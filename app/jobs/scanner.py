import logging

from tavily import AsyncTavilyClient

from app.config import settings

logger = logging.getLogger(__name__)

# Shrinija's target roles — Marketing Analyst + entry-level Analyst roles
JOB_QUERIES = [
    "Marketing Analyst entry level job posting 2026",
    "Marketing Analyst remote hybrid startup hiring",
    "Data Analyst entry level job posting 2026",
    "Business Analyst entry level job posting 2026",
    "Product Analyst entry level startup hiring 2026",
    "Analytics Analyst junior entry level job 2026",
    "Marketing Data Analyst fintech SaaS job posting",
    "Entry level Analyst AI technology company hiring",
]


async def scan_jobs() -> list[dict]:
    client = AsyncTavilyClient(api_key=settings.tavily_api_key)
    all_results = []
    seen_urls = set()

    for query in JOB_QUERIES:
        try:
            response = await client.search(
                query=query,
                max_results=8,
                search_depth="advanced",
                days=1,  # Only results from last 24 hours
            )
            for r in response.get("results", []):
                if r["url"] not in seen_urls:
                    seen_urls.add(r["url"])
                    all_results.append({
                        "title": r["title"],
                        "url": r["url"],
                        "snippet": r.get("content", "")[:400],
                    })
        except Exception as e:
            logger.warning("Job scan failed for query '%s': %s", query, e)

    # Score results by relevance to analyst roles
    scored = []
    for r in all_results:
        text = (r["title"] + " " + r["snippet"]).lower()
        score = 0
        # Strong signals
        if "marketing analyst" in text:
            score += 5
        if "data analyst" in text:
            score += 4
        if "business analyst" in text:
            score += 4
        if "product analyst" in text:
            score += 4
        if "analytics" in text:
            score += 3
        # Good signals
        if "entry level" in text or "entry-level" in text or "junior" in text:
            score += 3
        if "apply" in text or "application" in text:
            score += 2
        if any(kw in text for kw in ["fintech", "saas", "startup", "ai", "tech"]):
            score += 2
        if any(kw in text for kw in ["python", "sql", "tableau", "excel"]):
            score += 1
        # Negative signals (skip irrelevant)
        if "senior" in text or "principal" in text or "director" in text:
            score -= 3
        if "10+ years" in text or "8+ years" in text or "7+ years" in text:
            score -= 3

        scored.append((score, r))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:20]]  # Top 20 most relevant


def format_job_results(results: list[dict]) -> str:
    if not results:
        return "No relevant job postings found in the last 24 hours."

    lines = [f"Found {len(results)} jobs posted in the last 24 hours:\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"**{i}. {r['title']}**")
        lines.append(f"   {r['snippet'][:250]}")
        lines.append(f"   🔗 Apply: {r['url']}")
        lines.append("")
    return "\n".join(lines)
