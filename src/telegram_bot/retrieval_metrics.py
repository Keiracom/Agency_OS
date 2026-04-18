"""
Retrieval quality measurement for the memory listener.

Computes per-retrieval cited/not-cited flags by matching surfaced memory
content against bot response text. Aggregates into Hit Rate@5 and MRR@5.
No LLM calls — pure string matching with proper tokenization.
"""

# Stopword list: English common + callsigns + AU business terms
STOPWORDS = {
    # English common (top 50)
    "about", "after", "again", "also", "back", "been", "before", "being",
    "between", "both", "came", "come", "could", "does", "done", "each",
    "even", "every", "from", "going", "have", "here", "into", "just",
    "know", "like", "made", "make", "many", "more", "most", "much",
    "must", "need", "only", "other", "over", "right", "same", "some",
    "still", "such", "take", "than", "that", "them", "then", "there",
    "these", "they", "this", "those", "through", "very", "want", "well",
    "were", "what", "when", "where", "which", "while", "will", "with",
    "would", "your",
    # Callsigns
    "dave", "elliot", "aiden", "scout", "claude", "elliottbot",
    # AU business / Agency OS domain
    "agency", "client", "domain", "pipeline", "directive", "memory",
    "save", "recall", "supabase", "stage", "manual",
}


def tokenize(text: str) -> list[str]:
    """Extract meaningful tokens: lowercase, strip punctuation, remove stopwords, 4+ chars only."""
    import re
    words = re.findall(r'[a-zA-Z0-9]+', text.lower())
    return [w for w in words if len(w) >= 4 and w not in STOPWORDS]


def compute_cited_flags(
    surfaced_rows: list[dict],
    response_text: str,
) -> list[dict]:
    """For each surfaced memory row, compute whether it was 'cited' in the response.

    A row is cited if 2+ of its content tokens appear in the response tokens.

    Returns list of {row_id, cited: bool, shared_tokens: int, total_tokens: int}
    """
    response_tokens = set(tokenize(response_text))

    results = []
    for row in surfaced_rows:
        content = row.get("content", "")
        row_tokens = set(tokenize(content))
        shared = row_tokens & response_tokens
        results.append({
            "row_id": row.get("id", "unknown"),
            "source_type": row.get("source_type", "unknown"),
            "cited": len(shared) >= 2,
            "shared_tokens": len(shared),
            "total_row_tokens": len(row_tokens),
        })

    return results


def compute_hit_rate(cited_flags_list: list[list[dict]]) -> float:
    """Hit Rate@5: % of retrievals where at least 1 result was cited.

    cited_flags_list: list of per-retrieval cited_flags (from compute_cited_flags)
    """
    if not cited_flags_list:
        return 0.0
    hits = sum(1 for flags in cited_flags_list if any(f["cited"] for f in flags))
    return hits / len(cited_flags_list)


def compute_mrr(cited_flags_list: list[list[dict]]) -> float:
    """MRR@5: Mean Reciprocal Rank of first cited result.

    For each retrieval, find rank of first cited result (1-indexed).
    MRR = average of 1/rank across all retrievals.
    If no cited result: that retrieval contributes 0.
    """
    if not cited_flags_list:
        return 0.0
    reciprocals = []
    for flags in cited_flags_list:
        for i, f in enumerate(flags):
            if f["cited"]:
                reciprocals.append(1.0 / (i + 1))
                break
        else:
            reciprocals.append(0.0)
    return sum(reciprocals) / len(reciprocals)


def compute_source_type_breakdown(cited_flags_list: list[list[dict]]) -> dict:
    """Per source_type: how often each type gets cited vs not."""
    counts = {}  # {source_type: {cited: int, total: int}}
    for flags in cited_flags_list:
        for f in flags:
            st = f["source_type"]
            if st not in counts:
                counts[st] = {"cited": 0, "total": 0}
            counts[st]["total"] += 1
            if f["cited"]:
                counts[st]["cited"] += 1
    return counts


def generate_summary(cited_flags_list: list[list[dict]]) -> str:
    """Generate a text summary of retrieval quality metrics."""
    hr = compute_hit_rate(cited_flags_list)
    mrr = compute_mrr(cited_flags_list)
    breakdown = compute_source_type_breakdown(cited_flags_list)
    total_retrievals = len(cited_flags_list)

    lines = [
        f"Retrieval Quality Summary ({total_retrievals} retrievals)",
        f"  Hit Rate@5: {hr:.1%}",
        f"  MRR@5: {mrr:.3f}",
        f"  Source-type breakdown:",
    ]
    for st, counts in sorted(breakdown.items()):
        rate = counts["cited"] / counts["total"] if counts["total"] else 0
        lines.append(f"    {st}: {counts['cited']}/{counts['total']} cited ({rate:.0%})")

    return "\n".join(lines)
