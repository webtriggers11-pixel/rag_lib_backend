import io
import logging
import warnings
from typing import List

import psycopg2
from langchain_core._api.deprecation import LangChainPendingDeprecationWarning

from app.db import get_pool

warnings.filterwarnings("ignore", category=LangChainPendingDeprecationWarning)
from langchain_community.vectorstores import PGVector
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from app.config import (
    EMBEDDING_DIMENSION,
    GEMINI_MAX_TOKENS,
    GEMINI_MODEL,
    GEMINI_TEMPERATURE,
    GOOGLE_API_KEY,
    get_connection_string,
)

COLLECTION_NAME = "rag_documents"
# Best-practice RAG chunking: paragraph/sentence-aware, ~200-300 tokens per chunk, 15-20% overlap
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
# Prefer paragraph, then line, then sentence, then space (keeps meaning intact)
CHUNK_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

NO_TEXT_ERROR_MSG = (
    "No text could be extracted from the PDF after trying direct extraction and OCR. "
    "For scanned PDFs, install Tesseract (e.g. brew install tesseract on Mac). "
    "The file may be empty, corrupted, or in an unsupported language."
)

RAG_PROMPT_KEY = "rag_system"

DEFAULT_RAG_PROMPT = """You are a helpful document Q&A assistant. The context below comes from uploaded documents (brochures, reports, product docs, etc.). Be accurate and friendly.

1. Answer ONLY from the provided context. Do not use outside knowledge or guess.
2. If the answer isn't in the context, say so in a natural way—e.g. "I couldn't find that in the documents," "That doesn't seem to be covered in what I have," or "I'm not sure from these materials." Keep it short and human.
3. For off-topic questions, inappropriate requests, or requests for PII: politely decline in a natural way—e.g. "I can only help with questions about these documents—try asking something about the content!" or "That's outside what I can answer from these materials." Do not sound robotic or use formal refusals.
4. For data questions (totals, rankings, numbers, tables): use EXACT values from the context. Quote figures and categories as they appear. If the context has a table or list, use it to answer (e.g. totals, top 5). Do not round or infer unless the document does.
5. Do not invent numbers, categories, or sources. If the data isn't there, say so in a friendly, natural way.
6. Keep answers clear and concise. For totals or rankings, give the answer first, then briefly mention where it came from if helpful.

Context:
{context}

Question: {question}

Answer:"""

logger = logging.getLogger("app")


def get_rag_prompt() -> str:
    """Sync: load RAG prompt from DB (used inside sync query_rag)."""
    try:
        conn = psycopg2.connect(get_connection_string())
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT content FROM prompts WHERE key = %s", (RAG_PROMPT_KEY,))
                row = cur.fetchone()
            if row and row[0] and "{context}" in row[0] and "{question}" in row[0]:
                return row[0]
        finally:
            conn.close()
    except Exception as e:
        logger.debug("get_rag_prompt fallback: %s", e)
    return DEFAULT_RAG_PROMPT


async def get_rag_prompt_async() -> str:
    """Async: load RAG prompt template from DB. Falls back to DEFAULT_RAG_PROMPT if missing or error."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT content FROM prompts WHERE key = $1", RAG_PROMPT_KEY)
            if row and row["content"] and "{context}" in row["content"] and "{question}" in row["content"]:
                return row["content"]
    except Exception as e:
        logger.debug("get_rag_prompt_async fallback: %s", e)
    return DEFAULT_RAG_PROMPT


def get_embeddings():
    return GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001",
        google_api_key=GOOGLE_API_KEY,
        output_dimensionality=EMBEDDING_DIMENSION,
    )


def get_vector_store():
    conn_str = get_connection_string()
    if conn_str.startswith("postgresql://"):
        conn_str = "postgresql+psycopg2://" + conn_str[len("postgresql://"):]
    return PGVector(
        collection_name=COLLECTION_NAME,
        connection_string=conn_str,
        embedding_function=get_embeddings(),
        use_jsonb=True,
    )


def _extract_with_pypdf(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    parts = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            parts.append(t)
    return "\n\n".join(parts)


def _extract_with_pymupdf(pdf_bytes: bytes) -> str:
    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    parts = []
    for page in doc:
        t = page.get_text()
        if t:
            parts.append(t)
    doc.close()
    return "\n\n".join(parts)


def _extract_with_ocr(pdf_bytes: bytes) -> str:
    """Extract text from image-based/scanned PDF using Tesseract OCR."""
    import fitz
    from PIL import Image
    import pytesseract

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    parts = []
    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        img_bytes = pix.tobytes(output="png")
        img = Image.open(io.BytesIO(img_bytes))
        t = pytesseract.image_to_string(img)
        if t and t.strip():
            parts.append(t.strip())
    doc.close()
    return "\n\n".join(parts)


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    text = _extract_with_pypdf(pdf_bytes)
    if not text or not text.strip():
        try:
            text = _extract_with_pymupdf(pdf_bytes)
        except Exception:
            pass
    if not text or not text.strip():
        try:
            text = _extract_with_ocr(pdf_bytes)
        except Exception:
            pass
    return text or ""


def ingest_pdf_into_store(
    pdf_bytes: bytes,
    metadata: dict | None = None,
    org_id: str | None = None,
) -> int:
    text = extract_text_from_pdf(pdf_bytes)
    if not text or not text.strip():
        raise ValueError(NO_TEXT_ERROR_MSG)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=CHUNK_SEPARATORS,
        length_function=len,
        is_separator_regex=False,
    )
    chunks = splitter.split_text(text)
    vector_store = get_vector_store()
    meta = dict(metadata or {})
    if org_id is not None:
        meta["org_id"] = str(org_id)
    vector_store.add_texts(chunks, metadatas=[meta] * len(chunks))
    return len(chunks)


def query_rag(
    question: str,
    k: int = 4,
    filter_metadata: dict | None = None,
) -> str:
    vector_store = get_vector_store()
    search_kwargs = {"k": k}
    if filter_metadata:
        search_kwargs["filter"] = filter_metadata
    retriever = vector_store.as_retriever(search_kwargs=search_kwargs)
    llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        temperature=GEMINI_TEMPERATURE,
        max_output_tokens=GEMINI_MAX_TOKENS,
        google_api_key=GOOGLE_API_KEY,
    )
    template = get_rag_prompt()
    prompt = ChatPromptTemplate.from_template(template)

    def format_docs(docs):
        return "\n\n".join(d.page_content for d in docs)

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain.invoke(question)
