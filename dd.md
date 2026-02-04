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