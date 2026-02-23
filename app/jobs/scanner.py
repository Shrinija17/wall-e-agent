import logging

from tavily import AsyncTavilyClient

from app.config import settings

logger = logging.getLogger(__name__)

# Shrinija's target roles and keywords
JOB_QUERIES = [
    "Data Analyst entry level AI startup hiring 2026",
    "Business Analyst fintech SaaS startup job posting 2026",
    "Product Analyst AI technology company hiring 2026",
    "Marketing Analyst AI data-driven startup job 2026",
    "Analytics Engineer entry level AI company remote hybrid 2026",
]

# Keywords that signal a good fit
POSITIVE_SIGNALS = [
    "data analyst", "business analyst", "product analyst",
    "marketing analyst", "analytics", "AI", "fintech",
    "SaaS", "startup", "entry level", "junior",
    "python", "sql", "machine learning",
]


async def scan_jobs() -> list[dict]:
    client = AsyncTavilyClient(api_key=settings.tavily_api_key)
    all_results = []
    seen_urls = set()

    for query in JOB_QUERIES:
        try:
            response = await client.search(
                query=query,
                max_results=5,
                search_depth="basic",
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

    # Score results by relevance
    scored = []
    for r in all_results:
        text = (r["title"] + " " + r["snippet"]).lower()
        score = sum(1 for kw in POSITIVE_SIGNALS if kw.lower() in text)
        scored.append((score, r))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:12]]  # Top 12 most relevant


def format_job_results(results: list[dict]) -> str:
    if not results:
        return "No relevant job postings found today. I'll keep looking!"

    lines = ["Here are today's job matches:\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"**{i}. {r['title']}**")
        lines.append(f"   {r['snippet'][:200]}...")
        lines.append(f"   🔗 {r['url']}")
        lines.append("")
    return "\n".join(lines)
