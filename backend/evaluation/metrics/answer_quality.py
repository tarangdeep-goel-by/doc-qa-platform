"""Answer quality metrics: LLM-as-judge, semantic similarity, ROUGE-L."""

from typing import List, Dict, Any, Optional
from collections import Counter


def _tokenize(text: str) -> List[str]:
    """Simple whitespace tokenizer for ROUGE computation."""
    return text.lower().split()


def rouge_l(hypothesis: str, reference: str) -> float:
    """ROUGE-L score based on Longest Common Subsequence.

    Returns:
        F1 score 0-1. Higher is better.
    """
    if not hypothesis or not reference:
        return 0.0

    hyp_tokens = _tokenize(hypothesis)
    ref_tokens = _tokenize(reference)

    if not hyp_tokens or not ref_tokens:
        return 0.0

    # LCS using dynamic programming
    m, n = len(hyp_tokens), len(ref_tokens)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if hyp_tokens[i - 1] == ref_tokens[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    lcs_length = dp[m][n]

    if lcs_length == 0:
        return 0.0

    precision = lcs_length / m
    recall = lcs_length / n
    f1 = (2 * precision * recall) / (precision + recall)
    return f1


def rouge_1(hypothesis: str, reference: str) -> float:
    """ROUGE-1 (unigram overlap) F1 score.

    Returns:
        F1 score 0-1. Higher is better.
    """
    if not hypothesis or not reference:
        return 0.0

    hyp_tokens = Counter(_tokenize(hypothesis))
    ref_tokens = Counter(_tokenize(reference))

    overlap = sum((hyp_tokens & ref_tokens).values())

    if overlap == 0:
        return 0.0

    precision = overlap / sum(hyp_tokens.values())
    recall = overlap / sum(ref_tokens.values())
    f1 = (2 * precision * recall) / (precision + recall)
    return f1


def semantic_similarity(
    embedding_a,
    embedding_b,
) -> float:
    """Cosine similarity between two embeddings.

    Args:
        embedding_a: numpy array or list of floats.
        embedding_b: numpy array or list of floats.

    Returns:
        Float -1 to 1. Higher is better.
    """
    import numpy as np

    a = np.array(embedding_a, dtype=np.float64)
    b = np.array(embedding_b, dtype=np.float64)

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(np.dot(a, b) / (norm_a * norm_b))


def llm_as_judge(
    question: str,
    our_answer: str,
    reference_answer: str,
    client,
    model_name: str = "gemini-2.5-flash",
) -> Dict[str, Any]:
    """Use LLM to rate answer quality on multiple dimensions.

    Args:
        question: The original question.
        our_answer: Answer from our RAG system.
        reference_answer: Gold standard answer (from Claude.ai).
        client: google.genai.Client instance.
        model_name: Gemini model to use for judging.

    Returns:
        Dict with scores (1-5) for relevance, completeness, accuracy, organization,
        plus an overall score and explanation.
    """
    prompt = f"""You are an expert evaluator comparing two answers to the same question.

QUESTION: {question}

REFERENCE ANSWER (gold standard):
{reference_answer}

SYSTEM ANSWER (to evaluate):
{our_answer}

Rate the SYSTEM ANSWER on these dimensions (1-5 scale):

1. **Relevance** (1-5): Does the answer address the question directly?
2. **Completeness** (1-5): Does it cover all information present in the reference?
3. **Accuracy** (1-5): Is the information factually correct compared to reference?
4. **Organization** (1-5): Is the answer well-structured and easy to read?

Respond in EXACTLY this format (one line per score, then explanation):
relevance: <score>
completeness: <score>
accuracy: <score>
organization: <score>
explanation: <one paragraph explaining your ratings>"""

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config={"temperature": 0.1},
        )
        text = (response.text or "").strip()
        if not text:
            raise ValueError("Empty response from LLM judge")
        return _parse_judge_response(text)
    except Exception as e:
        return {
            "relevance": 0,
            "completeness": 0,
            "accuracy": 0,
            "organization": 0,
            "overall": 0.0,
            "explanation": f"LLM judge failed: {e}",
            "error": True,
        }


def _parse_judge_response(text: str) -> Dict[str, Any]:
    """Parse the structured LLM judge response."""
    scores = {}
    explanation = ""

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        for dim in ["relevance", "completeness", "accuracy", "organization"]:
            if line.lower().startswith(f"{dim}:"):
                try:
                    val = line.split(":", 1)[1].strip()
                    # Handle "4/5" or "4" formats
                    scores[dim] = int(val.split("/")[0].strip())
                except (ValueError, IndexError):
                    scores[dim] = 0

        if line.lower().startswith("explanation:"):
            explanation = line.split(":", 1)[1].strip()

    # Default missing scores to 0
    for dim in ["relevance", "completeness", "accuracy", "organization"]:
        scores.setdefault(dim, 0)

    # Overall is average of all dimensions
    valid_scores = [v for v in scores.values() if v > 0]
    overall = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0

    return {
        **scores,
        "overall": round(overall, 2),
        "explanation": explanation,
        "error": False,
    }


def compute_answer_metrics(
    our_answer: str,
    reference_answer: str,
    embedder=None,
    client=None,
    question: str = "",
    model_name: str = "gemini-2.5-flash",
) -> Dict[str, Any]:
    """Compute all answer quality metrics.

    Args:
        our_answer: Answer from our RAG system.
        reference_answer: Gold standard answer.
        embedder: Optional Embedder instance for semantic similarity.
        client: Optional genai.Client for LLM-as-judge.
        question: Original question (needed for LLM judge).
        model_name: Model for LLM judge.

    Returns:
        Dict of metric_name → value.
    """
    metrics: Dict[str, Any] = {}

    # Text overlap metrics (always computed - no dependencies)
    metrics["rouge_l"] = round(rouge_l(our_answer, reference_answer), 4)
    metrics["rouge_1"] = round(rouge_1(our_answer, reference_answer), 4)

    # Semantic similarity (requires embedder)
    if embedder is not None and our_answer.strip() and reference_answer.strip():
        emb_a = embedder.embed_text(our_answer)
        emb_b = embedder.embed_text(reference_answer)
        metrics["semantic_similarity"] = round(
            semantic_similarity(emb_a, emb_b), 4
        )

    # LLM-as-judge (requires client)
    if client is not None and question:
        judge_result = llm_as_judge(
            question=question,
            our_answer=our_answer,
            reference_answer=reference_answer,
            client=client,
            model_name=model_name,
        )
        metrics["llm_judge"] = judge_result

    return metrics


def aggregate_answer_metrics(
    per_query_metrics: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Average answer quality metrics across multiple queries.

    Args:
        per_query_metrics: List of metric dicts from compute_answer_metrics.

    Returns:
        Dict of metric_name → average value.
    """
    if not per_query_metrics:
        return {}

    aggregated: Dict[str, Any] = {}

    # Average scalar metrics
    for key in ["rouge_l", "rouge_1", "semantic_similarity"]:
        values = [m[key] for m in per_query_metrics if key in m]
        if values:
            aggregated[f"avg_{key}"] = round(sum(values) / len(values), 4)

    # Average LLM judge scores
    judge_results = [m["llm_judge"] for m in per_query_metrics if "llm_judge" in m]
    if judge_results:
        for dim in ["relevance", "completeness", "accuracy", "organization", "overall"]:
            values = [j[dim] for j in judge_results if not j.get("error")]
            if values:
                aggregated[f"avg_judge_{dim}"] = round(
                    sum(values) / len(values), 2
                )

    return aggregated
