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
| `expected_sources` | No | Page refs (`"p.22"`), title substrings or snippet text to match in retrieved sources. Retrieval metrics (precision/recall/NDCG/MRR) are 0 without it. **Every bundled dataset has it empty (`[]`)**, so retrieval is not currently scored |
| `requires_synthesis` | No | Does the answer need info from multiple sources? |
| `requires_organization` | No | Does the answer need structured formatting? |

## Bundled Datasets

| File | Questions | Reference answers from |
|------|-----------|------------------------|
| `fx5u_qa_benchmark.json` | 24 | Claude.ai with the FX5U hardware manual |
| `atomic habits.json` | 28 | Claude.ai with the book |
| `separation-letter.json` | 28 | Claude.ai with the separation agreement |
| `real_world_multi_doc.json` | 77 | the three above combined (adds `source_document`) |
| `conversational_multi_doc.json` | 6 conversations, 18 turns | `claude_answer` per turn; uses `conversations[].turns[]` with `doc_ids_hint` and `depends_on_context` instead of `questions`, auto-detected by `run_evaluation.py` |
| `nvc.json` | 30 | Gemini with the full PDF, via `generate_dataset.py` |

## How to Create a Dataset

Alternatively, generate one from an uploaded PDF with Gemini: `python evaluation/generate_dataset.py --pdf data/uploads/<doc_id>.pdf --output evaluation/datasets/out.json --num-questions 30`.


1. Upload your document to Claude.ai
2. Ask your questions and get comprehensive answers
3. Copy Q&A pairs into the JSON format above
4. Fill in `expected_sources` based on which pages/sections contain the answers (needed for any non-zero retrieval metric; none of the bundled datasets do this yet)
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
