# Benchmark Datasets

## Format

Each dataset is a JSON file with this structure:

```json
{
  "dataset_name": "Human-readable name",
  "document": "Name of the source document",
  "version": "1.0",
  "description": "What this benchmark tests",
  "questions": [
    {
      "id": "q1",
      "question": "The question to ask the RAG system",
      "claude_answer": "Gold standard answer from Claude.ai",
      "difficulty": "easy|medium|hard",
      "category": "product_info|classification|comparison|troubleshooting|general",
      "expected_sources": ["p.22", "p.29"],
      "requires_synthesis": false,
      "requires_organization": true
    }
  ]
}
```

## Fields

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique question identifier |
| `question` | Yes | Exact question to ask |
| `claude_answer` | Yes | Gold standard reference answer |
| `difficulty` | No | easy, medium, hard (default: medium) |
| `category` | No | Question type for grouping (default: general) |
| `expected_sources` | No | Page refs or text to match in retrieved sources |
| `requires_synthesis` | No | Does the answer need info from multiple sources? |
| `requires_organization` | No | Does the answer need structured formatting? |

## How to Create a Dataset

1. Upload your document to Claude.ai
2. Ask your questions and get comprehensive answers
3. Copy Q&A pairs into the JSON format above
4. Fill in `expected_sources` based on which pages/sections contain the answers
5. Set difficulty and category for each question

## Example Workflow

```bash
# Run eval with this dataset
python evaluation/run_evaluation.py \
  --dataset evaluation/datasets/fx5u_qa_benchmark.json \
  --output evaluation/results/baseline.json

# Or upload + eval in one command
python scripts/upload_and_eval.py path/to/manual.pdf \
  --benchmark evaluation/datasets/fx5u_qa_benchmark.json \
  --output evaluation/results/baseline.json
```
