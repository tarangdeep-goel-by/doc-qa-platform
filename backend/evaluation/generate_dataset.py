#!/usr/bin/env python3
"""
Generate eval datasets automatically from any PDF document.

Uses Gemini File API to upload the PDF once, then references it in all API calls.
Gemini reads the PDF natively (layout, tables, images) — no text extraction needed.

Usage:
    # Inside Docker container:
    python evaluation/generate_dataset.py \
        --pdf data/uploads/<doc_id>.pdf \
        --output evaluation/datasets/my_dataset.json \
        --num-questions 30 \
        --doc-name "My Document Title"

    # Or from host via docker exec:
    docker exec -t doc-qa-backend python evaluation/generate_dataset.py \
        --pdf data/uploads/<doc_id>.pdf \
        --output evaluation/datasets/my_dataset.json \
        --num-questions 30 \
        --doc-name "My Document Title"
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

from google import genai


# ---------------------------------------------------------------------------
# Gemini File API upload
# ---------------------------------------------------------------------------

def upload_pdf(client, pdf_path: str, doc_name: str) -> genai.types.File:
    """Upload PDF to Gemini File API. Returns File reference for generate_content calls."""
    uploaded = client.files.upload(
        file=pdf_path,
        config=genai.types.UploadFileConfig(
            mime_type="application/pdf",
            display_name=doc_name,
        ),
    )
    # Wait for ACTIVE state (processing is usually instant for PDFs)
    while uploaded.state.name == "PROCESSING":
        time.sleep(2)
        uploaded = client.files.get(name=uploaded.name)
    if uploaded.state.name != "ACTIVE":
        raise RuntimeError(f"File upload failed: state={uploaded.state.name}")
    return uploaded


# ---------------------------------------------------------------------------
# Question generation
# ---------------------------------------------------------------------------

QUESTION_GEN_PROMPT = """\
You are an expert at creating evaluation questions for document Q&A systems.

The document has been provided as an attached PDF file. Generate exactly {num_questions} diverse questions that test a RAG system's ability to find and synthesize information from this document.

QUESTION DIVERSITY REQUIREMENTS — include a mix of:
1. **Factual/lookup** (easy): Questions with a direct answer in one place in the document
2. **Multi-part** (medium): Questions requiring info from 2-3 different sections
3. **Synthesis** (hard): Questions requiring reasoning across multiple parts of the document
4. **Table/data** (if applicable): Questions about specific numbers, comparisons, or data points
5. **Overview/summary**: What is this document about? What are the main topics?
6. **Specific detail**: Questions about edge cases, exceptions, or caveats mentioned in the doc
7. **Comparison**: Questions comparing two things discussed in the document
8. **Procedural**: How-to questions if the document describes processes or steps

IMPORTANT RULES:
- Questions must be answerable ONLY from this document
- Do NOT ask about information not in the document
- Vary question phrasing (don't start every question with "What")
- Include both short-answer and long-answer questions
- Questions should feel natural, like a real user would ask them

Output ONLY a JSON array of objects, each with:
- "question": the question text
- "difficulty": "easy" | "medium" | "hard"
- "category": one of "factual", "multi_part", "synthesis", "table_data", "overview", "specific_detail", "comparison", "procedural"
- "requires_synthesis": true/false (does it need info from multiple sections?)

Generate exactly {num_questions} questions as a JSON array. Output ONLY the JSON array, no other text."""


def generate_questions(client, model: str, uploaded_file: genai.types.File, num_questions: int) -> list[dict]:
    """Generate diverse questions from the document using Gemini."""
    print(f"  Generating {num_questions} questions...")

    prompt = QUESTION_GEN_PROMPT.format(num_questions=num_questions)

    response = _call_with_retry(
        client, model, contents=[uploaded_file, prompt],
        temperature=0.7, response_mime_type="application/json",
    )

    questions = json.loads(response.text)
    print(f"  Got {len(questions)} questions")

    # Validate and assign IDs
    for i, q in enumerate(questions, 1):
        q["id"] = f"q{i}"
        q.setdefault("difficulty", "medium")
        q.setdefault("category", "factual")
        q.setdefault("requires_synthesis", False)

    return questions


# ---------------------------------------------------------------------------
# Oracle answer generation
# ---------------------------------------------------------------------------

ORACLE_ANSWER_PROMPT = """\
You are an expert at answering questions about documents. The document has been provided as an attached PDF file. Answer the question thoroughly and accurately using ONLY information from this document.

RULES:
- Be comprehensive but concise
- Cite specific details, numbers, and facts from the document
- If the document contains relevant tables or lists, include that data
- If the question asks about something not covered in the document, say so clearly
- Structure longer answers with clear organization (lists, sections as appropriate)

QUESTION: {question}

Provide a thorough, accurate answer based on the document."""


def _call_with_retry(client, model: str, contents, temperature: float = 0.2,
                     response_mime_type: str | None = None, max_retries: int = 5):
    """Call Gemini with exponential backoff on rate limit errors."""
    config = genai.types.GenerateContentConfig(temperature=temperature)
    if response_mime_type:
        config = genai.types.GenerateContentConfig(
            temperature=temperature, response_mime_type=response_mime_type,
        )

    for attempt in range(max_retries):
        try:
            return client.models.generate_content(
                model=model, contents=contents, config=config,
            )
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait = min(30 * (2 ** attempt), 120)  # 30s, 60s, 120s, 120s, 120s
                print(f"    Rate limited, waiting {wait}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Failed after {max_retries} retries due to rate limiting")


def generate_oracle_answers(
    client, model: str, uploaded_file: genai.types.File, questions: list[dict], delay: float = 1.0,
    save_path: str | None = None, doc_name: str = "", description: str = "",
) -> list[dict]:
    """Generate oracle answers for each question using full document context.

    Skips questions that already have a claude_answer (for resume support).
    Saves progress to save_path after each answer if provided.
    """
    print(f"  Generating oracle answers for {len(questions)} questions...")
    total = len(questions)
    skipped = 0

    for i, q in enumerate(questions, 1):
        if q.get("claude_answer"):
            skipped += 1
            continue

        if skipped and i == skipped + 1:
            print(f"    Skipped {skipped} already-answered questions")

        prompt = ORACLE_ANSWER_PROMPT.format(question=q["question"])

        response = _call_with_retry(client, model, contents=[uploaded_file, prompt], temperature=0.2)

        q["claude_answer"] = response.text
        print(f"    [{i}/{total}] {q['question'][:60]}...")

        # Save progress after each answer so we can resume
        if save_path:
            _save_progress(save_path, doc_name, questions, description)

        # Rate limit courtesy
        if i < total:
            time.sleep(delay)

    return questions


def _save_progress(path: str, doc_name: str, questions: list[dict], description: str = ""):
    """Save current state to disk for resume support."""
    dataset = build_dataset(doc_name, questions, description)
    with open(path, "w") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Dataset assembly
# ---------------------------------------------------------------------------

def build_dataset(
    doc_name: str, questions: list[dict], description: str = ""
) -> dict:
    """Assemble questions into the standard eval dataset format."""
    for q in questions:
        q.setdefault("expected_sources", [])
        q.setdefault("requires_organization", q.get("requires_synthesis", False))

    return {
        "dataset_name": f"{doc_name} Q&A",
        "document": doc_name,
        "version": "1.0",
        "description": description or f"Auto-generated eval dataset for {doc_name}. "
        f"Oracle answers generated by Gemini with full document context.",
        "questions": questions,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate eval dataset from a PDF using Gemini oracle"
    )
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--output", required=True, help="Output dataset JSON path")
    parser.add_argument(
        "--num-questions", type=int, default=30, help="Number of questions to generate (default: 30)"
    )
    parser.add_argument("--doc-name", help="Document name (default: PDF filename)")
    parser.add_argument("--description", help="Dataset description")
    parser.add_argument(
        "--model",
        default=None,
        help="Gemini model to use (default: GEMINI_MODEL env var)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=5.0,
        help="Delay between oracle answer API calls in seconds (default: 5.0)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from partial output file (skips questions that already have answers)",
    )
    args = parser.parse_args()

    # Validate
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}")
        sys.exit(1)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc_name = args.doc_name or pdf_path.stem.replace("_", " ").replace("-", " ").title()
    model = args.model or os.environ["GEMINI_MODEL"]
    api_key = os.environ["GEMINI_API_KEY"]

    client = genai.Client(api_key=api_key)

    print(f"=== Dataset Generator ===")
    print(f"  PDF: {pdf_path}")
    print(f"  Model: {model}")
    print(f"  Questions: {args.num_questions}")
    print()

    # Step 1: Upload PDF to Gemini File API
    print("Step 1: Uploading PDF to Gemini File API...")
    uploaded_file = upload_pdf(client, str(pdf_path), doc_name)
    print(f"  Uploaded: {uploaded_file.name} ({uploaded_file.state.name})")
    print()

    try:
        # Step 2: Generate questions (or load from partial output)
        questions = None
        if args.resume and output_path.exists():
            print("Step 2: Resuming from partial output...")
            with open(output_path) as f:
                partial = json.load(f)
            questions = partial.get("questions", [])
            answered = sum(1 for q in questions if q.get("claude_answer"))
            print(f"  Loaded {len(questions)} questions, {answered} already answered")
        else:
            print("Step 2: Generating questions...")
            questions = generate_questions(client, model, uploaded_file, args.num_questions)
        print()

        # Step 3: Generate oracle answers (skips already-answered questions)
        print("Step 3: Generating oracle answers...")
        questions = generate_oracle_answers(
            client, model, uploaded_file, questions, delay=args.delay,
            save_path=str(output_path), doc_name=doc_name,
            description=args.description or "",
        )
        print()
    finally:
        # Step 4: Cleanup — delete uploaded file
        print("Step 4: Cleaning up uploaded file...")
        try:
            client.files.delete(name=uploaded_file.name)
            print(f"  Deleted: {uploaded_file.name}")
        except Exception as e:
            print(f"  Warning: Could not delete file: {e}")

    # Step 5: Assemble dataset
    print("Step 5: Assembling dataset...")
    dataset = build_dataset(doc_name, questions, args.description or "")

    with open(output_path, "w") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Dataset written to {output_path}")
    print(f"  {len(questions)} questions generated")
    print(f"  Difficulty breakdown:")
    for diff in ["easy", "medium", "hard"]:
        count = sum(1 for q in questions if q.get("difficulty") == diff)
        if count:
            print(f"    {diff}: {count}")
    print(f"  Category breakdown:")
    cats = {}
    for q in questions:
        cat = q.get("category", "unknown")
        cats[cat] = cats.get(cat, 0) + 1
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"    {cat}: {count}")


if __name__ == "__main__":
    main()
