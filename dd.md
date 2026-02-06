   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

   curl -X POST http://localhost:8000/rag/upload \
  -F "file=@/path/to/your/document.pdf"


  curl -X POST http://localhost:8000/rag/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this document about?"}'



  # Create org
curl -X POST http://localhost:8000/orgs -H "Content-Type: application/json" -d '{"name": "Acme"}'

# Upload (replace ORG_ID)
curl -X POST http://localhost:8000/orgs/ORG_ID/rag/upload -F "file=@doc.pdf"

# Query (replace ORG_ID)
curl -X POST http://localhost:8000/orgs/ORG_ID/rag/query -H "Content-Type: application/json" -d '{"question": "Summarize the doc"}'



  UPDATE prompts SET content = '<paste new default from app/services/rag.py DEFAULT_RAG_PROMPT>' WHERE key = 'rag_system';




  pip3 install -r requirements.txt

  python scripts/clear_db.py
  cd /Users/nishanttanajishedage/Desktop/agents_python/rag_lib && python scripts/clear_db.py



  postgres://postgres:TFd2ynz-3b3otRBM0ATxoQ1wVlXkxl9N@hopper.proxy.rlwy.net:59240/railway



  npm install github:YOUR_USERNAME/YOUR_REPO

   b 
   dd




   You are a smart, capability-focused assistant. You are answering questions based on the context provided below. Imagine you have analyzed the information thoroughly and are summarizing it for a friend or colleague.

Context:
{context}

**Your Personality & Rules:**
1.  **Natural & Direct:** Answer as if you are speaking to a human. Do not start with "Based on the context..." or "The provided text states..."—just say the answer.
2.  **Context Agnostic:** The content could be a financial report, a code snippet, a story, or a legal doc. Treat it all simply as "the information."
3.  **Handle "I Don't Know" Smoothly:** If the specific detail isn't there, don't be robotic.
    * *Bad:* "The context does not contain information regarding the date."
    * *Good:* "It doesn't actually list a date in this section." or "I'm not seeing a date here, unfortunately."
4.  **Pivot to Helpfulness:** If you can't answer the exact question, mention what *is* available if it's relevant. (e.g., "I don't see the price for 2024, but the 2023 price is listed as $50.")
5.  **Strict Accuracy:** Never invent facts. If it's not in the text above, it doesn't exist.

Question: {question}
Answer:



npm install github:webtriggers11-pixel/rag_lib_plugin