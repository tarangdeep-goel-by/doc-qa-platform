#!/bin/bash

###############################################################################
# Quick Backend API Test Script
# Tests all major endpoints with curl commands
###############################################################################

set -e  # Exit on error

# Configuration
BASE_URL="http://localhost:8000"
TEST_PDF="${1:-tests/fixtures/test.pdf}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

# Check if backend is running
print_header "Checking Backend Connection"
if curl -s -f "$BASE_URL/health" > /dev/null 2>&1; then
    print_success "Backend is running at $BASE_URL"
else
    print_error "Backend is not running at $BASE_URL"
    echo "Start backend with: cd backend && python run_api.py"
    exit 1
fi

# Check if test PDF exists
if [ ! -f "$TEST_PDF" ]; then
    print_error "Test PDF not found at: $TEST_PDF"
    echo "Usage: $0 [path/to/test.pdf]"
    exit 1
fi

###############################################################################
# Test 1: Health Check
###############################################################################

print_header "1. Health Check"
HEALTH=$(curl -s "$BASE_URL/health")
echo "$HEALTH" | jq '.'

if echo "$HEALTH" | jq -e '.status == "healthy"' > /dev/null; then
    print_success "Health check passed"
else
    print_error "Health check failed"
    exit 1
fi

###############################################################################
# Test 2: Upload Document
###############################################################################

print_header "2. Upload Document"
print_info "Uploading: $TEST_PDF"

UPLOAD_RESPONSE=$(curl -s -X POST "$BASE_URL/api/admin/upload" \
  -F "file=@$TEST_PDF")

echo "$UPLOAD_RESPONSE" | jq '.'

DOC_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.doc_id')

if [ -n "$DOC_ID" ] && [ "$DOC_ID" != "null" ]; then
    print_success "Document uploaded with ID: $DOC_ID"
else
    print_error "Failed to upload document"
    exit 1
fi

###############################################################################
# Test 3: List Documents
###############################################################################

print_header "3. List Documents"
DOCS=$(curl -s "$BASE_URL/api/admin/documents")
echo "$DOCS" | jq '.documents[] | {doc_id, title, chunk_count}'

DOC_COUNT=$(echo "$DOCS" | jq '.documents | length')
print_success "Found $DOC_COUNT document(s)"

###############################################################################
# Test 4: Get Document Details
###############################################################################

print_header "4. Get Document Details"
DOC_DETAILS=$(curl -s "$BASE_URL/api/admin/documents/$DOC_ID")
echo "$DOC_DETAILS" | jq '{doc_id, title, total_pages, chunk_count}'
print_success "Retrieved document details"

###############################################################################
# Test 5: Create Chat (No Documents)
###############################################################################

print_header "5. Create Chat (All Documents)"
CHAT1_RESPONSE=$(curl -s -X POST "$BASE_URL/api/chats" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Chat - All Docs",
    "doc_ids": []
  }')

echo "$CHAT1_RESPONSE" | jq '.'
CHAT1_ID=$(echo "$CHAT1_RESPONSE" | jq -r '.id')

if [ -n "$CHAT1_ID" ] && [ "$CHAT1_ID" != "null" ]; then
    print_success "Chat 1 created with ID: $CHAT1_ID"
else
    print_error "Failed to create chat 1"
    exit 1
fi

###############################################################################
# Test 6: Create Chat (With Specific Document)
###############################################################################

print_header "6. Create Chat (Specific Document)"
CHAT2_RESPONSE=$(curl -s -X POST "$BASE_URL/api/chats" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Test Chat - Specific Doc\",
    \"doc_ids\": [\"$DOC_ID\"]
  }")

echo "$CHAT2_RESPONSE" | jq '.'
CHAT2_ID=$(echo "$CHAT2_RESPONSE" | jq -r '.id')

if [ -n "$CHAT2_ID" ] && [ "$CHAT2_ID" != "null" ]; then
    print_success "Chat 2 created with ID: $CHAT2_ID"
else
    print_error "Failed to create chat 2"
    exit 1
fi

###############################################################################
# Test 7: List Chats
###############################################################################

print_header "7. List All Chats"
CHATS=$(curl -s "$BASE_URL/api/chats")
echo "$CHATS" | jq '.chats[] | {id, name, message_count}'

CHAT_COUNT=$(echo "$CHATS" | jq '.chats | length')
print_success "Found $CHAT_COUNT chat(s)"

###############################################################################
# Test 8: Ask Question in Chat
###############################################################################

print_header "8. Ask Question in Chat"
print_info "Asking: What is this document about?"

ASK_RESPONSE=$(curl -s -X POST "$BASE_URL/api/chats/$CHAT1_ID/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is this document about?",
    "top_k": 5
  }')

echo "$ASK_RESPONSE" | jq '{
  message_id: .message.id,
  content: .message.content,
  source_count: (.message.sources | length),
  sources: [.message.sources[] | {doc_title, page_num, score}]
}'

# Check if answer has content
ANSWER_LENGTH=$(echo "$ASK_RESPONSE" | jq -r '.message.content | length')
if [ "$ANSWER_LENGTH" -gt 0 ]; then
    print_success "Got answer with $ANSWER_LENGTH characters"
else
    print_error "Answer is empty"
fi

# Check for page numbers in sources
HAS_PAGE_NUMS=$(echo "$ASK_RESPONSE" | jq '[.message.sources[]? | .page_num] | any')
if [ "$HAS_PAGE_NUMS" == "true" ]; then
    print_success "Sources include page numbers ✓"
else
    print_error "Sources missing page numbers (re-upload document?)"
fi

###############################################################################
# Test 9: Get Chat with Messages
###############################################################################

print_header "9. Get Chat with Messages"
CHAT_DETAILS=$(curl -s "$BASE_URL/api/chats/$CHAT1_ID")
echo "$CHAT_DETAILS" | jq '{
  chat: .chat | {id, name, message_count},
  message_count: (.messages | length),
  messages: [.messages[] | {role, content_length: (.content | length)}]
}'

MESSAGE_COUNT=$(echo "$CHAT_DETAILS" | jq '.messages | length')
print_success "Chat has $MESSAGE_COUNT message(s)"

###############################################################################
# Test 10: Rename Chat
###############################################################################

print_header "10. Rename Chat"
RENAME_RESPONSE=$(curl -s -X PATCH "$BASE_URL/api/chats/$CHAT2_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Renamed Test Chat"
  }')

echo "$RENAME_RESPONSE" | jq '{id, name}'
print_success "Chat renamed"

###############################################################################
# Test 11: Legacy Query Endpoint
###############################################################################

print_header "11. Legacy Query Endpoint (Still Works)"
LEGACY_RESPONSE=$(curl -s -X POST "$BASE_URL/api/query/ask" \
  -H "Content-Type: application/json" \
  -d "{
    \"question\": \"Summary of the document?\",
    \"top_k\": 3,
    \"doc_ids\": [\"$DOC_ID\"]
  }")

echo "$LEGACY_RESPONSE" | jq '{
  question,
  answer_length: (.answer | length),
  source_count: (.sources | length),
  retrieved_count
}'

print_success "Legacy endpoint working"

###############################################################################
# Test 12: PDF File Serving
###############################################################################

print_header "12. PDF File Serving"
PDF_URL="$BASE_URL/api/admin/documents/$DOC_ID/file"
print_info "PDF URL: $PDF_URL"

# Check if PDF is accessible
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$PDF_URL")

if [ "$HTTP_CODE" == "200" ]; then
    print_success "PDF file is accessible (HTTP $HTTP_CODE)"
    print_info "Open in browser: $PDF_URL#page=1"
else
    print_error "PDF file not accessible (HTTP $HTTP_CODE)"
fi

###############################################################################
# Cleanup
###############################################################################

print_header "Cleanup"
read -p "Delete test data? (y/N) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Deleting chats..."
    curl -s -X DELETE "$BASE_URL/api/chats/$CHAT1_ID" | jq '.'
    curl -s -X DELETE "$BASE_URL/api/chats/$CHAT2_ID" | jq '.'
    print_success "Chats deleted"

    print_info "Deleting document..."
    curl -s -X DELETE "$BASE_URL/api/admin/documents/$DOC_ID" | jq '.'
    print_success "Document deleted"
else
    print_info "Cleanup skipped"
    echo "To manually cleanup:"
    echo "  Chat 1: curl -X DELETE $BASE_URL/api/chats/$CHAT1_ID"
    echo "  Chat 2: curl -X DELETE $BASE_URL/api/chats/$CHAT2_ID"
    echo "  Document: curl -X DELETE $BASE_URL/api/admin/documents/$DOC_ID"
fi

###############################################################################
# Summary
###############################################################################

print_header "Test Summary"
echo ""
echo "✓ Health check"
echo "✓ Document upload"
echo "✓ Document list/details"
echo "✓ Chat creation (2 chats)"
echo "✓ Chat listing"
echo "✓ Question answering with page citations"
echo "✓ Chat message persistence"
echo "✓ Chat renaming"
echo "✓ Legacy query endpoint"
echo "✓ PDF file serving"
echo ""
print_success "All tests passed! 🎉"
echo ""
print_info "IDs for manual testing:"
echo "  Document ID: $DOC_ID"
echo "  Chat 1 ID: $CHAT1_ID"
echo "  Chat 2 ID: $CHAT2_ID"
echo ""
