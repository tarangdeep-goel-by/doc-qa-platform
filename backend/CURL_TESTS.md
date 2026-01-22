# Backend API Testing with cURL

## Prerequisites

```bash
# Start backend
cd backend
python run_api.py

# Ensure Qdrant is running
docker-compose up -d
```

---

## 1. Health Check

```bash
# Check API health
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "qdrant_connected": true,
  "gemini_configured": true
}
```

---

## 2. Document Management

### Upload Document

```bash
# Upload a PDF (replace with your file path)
curl -X POST http://localhost:8000/api/admin/upload \
  -F "file=@/path/to/your/document.pdf"
```

**Expected Response:**
```json
{
  "doc_id": "abc123...",
  "title": "document.pdf",
  "status": "success",
  "chunk_count": 45,
  "processing_time": 12.34
}
```

**Save the doc_id for next steps!**

### List Documents

```bash
curl http://localhost:8000/api/admin/documents
```

**Expected Response:**
```json
{
  "documents": [
    {
      "doc_id": "abc123...",
      "title": "document.pdf",
      "upload_date": "2026-01-21T...",
      "file_size_mb": 1.5,
      "chunk_count": 45,
      "format": "pdf"
    }
  ]
}
```

### Get Document Details

```bash
# Replace {doc_id} with actual ID
curl http://localhost:8000/api/admin/documents/{doc_id}
```

**Expected Response:**
```json
{
  "doc_id": "abc123...",
  "title": "document.pdf",
  "filename": "document.pdf",
  "format": "pdf",
  "upload_date": "2026-01-21T...",
  "file_size_mb": 1.5,
  "chunk_count": 45,
  "total_pages": 10,
  "metadata": {
    "total_pages": 10,
    "author": "",
    "title": "",
    "subject": "",
    "creator": ""
  }
}
```

### Serve PDF File

```bash
# Download PDF (opens in browser)
curl http://localhost:8000/api/admin/documents/{doc_id}/file \
  --output downloaded.pdf

# Or open in browser:
# http://localhost:8000/api/admin/documents/{doc_id}/file#page=5
```

### Delete Document

```bash
curl -X DELETE http://localhost:8000/api/admin/documents/{doc_id}
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Document 'document.pdf' deleted successfully"
}
```

---

## 3. Chat Management

### Create Chat

```bash
# Create chat with all documents
curl -X POST http://localhost:8000/api/chats \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Research Q&A",
    "doc_ids": []
  }'

# Or create chat with specific documents
curl -X POST http://localhost:8000/api/chats \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Machine Learning Papers",
    "doc_ids": ["doc_id_1", "doc_id_2"]
  }'
```

**Expected Response:**
```json
{
  "id": "chat_xyz...",
  "name": "Research Q&A",
  "doc_ids": [],
  "created_at": "2026-01-21T...",
  "updated_at": "2026-01-21T...",
  "message_count": 0
}
```

**Save the chat id for next steps!**

### List Chats

```bash
curl http://localhost:8000/api/chats
```

**Expected Response:**
```json
{
  "chats": [
    {
      "id": "chat_xyz...",
      "name": "Research Q&A",
      "doc_ids": [],
      "created_at": "2026-01-21T...",
      "updated_at": "2026-01-21T...",
      "message_count": 0
    }
  ]
}
```

### Get Chat with Messages

```bash
curl http://localhost:8000/api/chats/{chat_id}
```

**Expected Response:**
```json
{
  "chat": {
    "id": "chat_xyz...",
    "name": "Research Q&A",
    "doc_ids": [],
    "created_at": "2026-01-21T...",
    "updated_at": "2026-01-21T...",
    "message_count": 2
  },
  "messages": [
    {
      "id": "msg_1",
      "chat_id": "chat_xyz...",
      "role": "user",
      "content": "What is the main topic?",
      "timestamp": "2026-01-21T...",
      "sources": null,
      "filtered_docs": []
    },
    {
      "id": "msg_2",
      "chat_id": "chat_xyz...",
      "role": "assistant",
      "content": "The main topic is...",
      "timestamp": "2026-01-21T...",
      "sources": [
        {
          "doc_id": "abc123...",
          "doc_title": "document.pdf",
          "chunk_text": "...",
          "score": 0.89,
          "page_num": 3
        }
      ],
      "filtered_docs": []
    }
  ]
}
```

### Ask Question in Chat

```bash
curl -X POST http://localhost:8000/api/chats/{chat_id}/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the key findings?",
    "top_k": 10
  }'
```

**Expected Response:**
```json
{
  "message": {
    "id": "msg_xyz...",
    "chat_id": "chat_xyz...",
    "role": "assistant",
    "content": "Based on the documents, the key findings are...",
    "timestamp": "2026-01-21T...",
    "sources": [
      {
        "doc_id": "abc123...",
        "doc_title": "document.pdf",
        "chunk_text": "The research shows that...",
        "score": 0.92,
        "page_num": 5
      }
    ],
    "filtered_docs": []
  }
}
```

### Rename Chat

```bash
curl -X PATCH http://localhost:8000/api/chats/{chat_id} \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Chat Name"
  }'
```

**Expected Response:**
```json
{
  "id": "chat_xyz...",
  "name": "Updated Chat Name",
  "doc_ids": [],
  "created_at": "2026-01-21T...",
  "updated_at": "2026-01-21T...",
  "message_count": 2
}
```

### Delete Chat

```bash
curl -X DELETE http://localhost:8000/api/chats/{chat_id}
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Chat deleted successfully"
}
```

---

## 4. Legacy Query Endpoint (Still Works)

### Ask Question (Without Chat)

```bash
curl -X POST http://localhost:8000/api/query/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the document about?",
    "top_k": 5,
    "doc_ids": []
  }'
```

**Expected Response:**
```json
{
  "question": "What is the document about?",
  "answer": "The document discusses...",
  "sources": [
    {
      "doc_id": "abc123...",
      "doc_title": "document.pdf",
      "chunk_text": "...",
      "score": 0.85,
      "page_num": 2
    }
  ],
  "retrieved_count": 5
}
```

---

## Complete Test Flow

### Test Script

```bash
#!/bin/bash

BASE_URL="http://localhost:8000"
DOC_FILE="/path/to/test.pdf"

echo "=== 1. Health Check ==="
curl -s $BASE_URL/health | jq

echo -e "\n=== 2. Upload Document ==="
UPLOAD_RESPONSE=$(curl -s -X POST $BASE_URL/api/admin/upload -F "file=@$DOC_FILE")
echo $UPLOAD_RESPONSE | jq
DOC_ID=$(echo $UPLOAD_RESPONSE | jq -r '.doc_id')
echo "Document ID: $DOC_ID"

echo -e "\n=== 3. List Documents ==="
curl -s $BASE_URL/api/admin/documents | jq

echo -e "\n=== 4. Create Chat ==="
CHAT_RESPONSE=$(curl -s -X POST $BASE_URL/api/chats \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"Test Chat\", \"doc_ids\": [\"$DOC_ID\"]}")
echo $CHAT_RESPONSE | jq
CHAT_ID=$(echo $CHAT_RESPONSE | jq -r '.id')
echo "Chat ID: $CHAT_ID"

echo -e "\n=== 5. Ask Question in Chat ==="
curl -s -X POST $BASE_URL/api/chats/$CHAT_ID/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this document about?", "top_k": 5}' | jq

echo -e "\n=== 6. Get Chat with Messages ==="
curl -s $BASE_URL/api/chats/$CHAT_ID | jq

echo -e "\n=== 7. List All Chats ==="
curl -s $BASE_URL/api/chats | jq

echo -e "\n=== 8. Cleanup ==="
echo "Delete chat..."
curl -s -X DELETE $BASE_URL/api/chats/$CHAT_ID | jq
echo "Delete document..."
curl -s -X DELETE $BASE_URL/api/admin/documents/$DOC_ID | jq

echo -e "\n=== Done! ==="
```

Save as `test_api.sh` and run:
```bash
chmod +x test_api.sh
./test_api.sh
```

---

## Troubleshooting

### Error: Connection refused
**Solution**: Start backend with `python run_api.py`

### Error: Qdrant connection failed
**Solution**: Start Qdrant with `docker-compose up -d`

### Error: Gemini not configured
**Solution**: Set `GEMINI_API_KEY` in `.env` file

### Error: 404 Not Found
**Solution**: Check endpoint URL - ensure correct path and ID

### Error: 422 Validation error
**Solution**: Check request body format - ensure JSON is valid
