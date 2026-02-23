import logging

from tavily import AsyncTavilyClient

from app.config import settings

logger = logging.getLogger(__name__)

TRENDING_QUERIES = [
    "trending AI topics on X Twitter today 2026",
    "viral AI tech tweets this week 2026",
    "breaking AI news technology startups 2026",
    "trending machine learning LLM agents 2026",
]


async def scan_trending_ai() -> list[dict]:
    client = AsyncTavilyClient(api_key=settings.tavily_api_key)
    all_results = []
    seen_urls = set()

    for query in TRENDING_QUERIES:
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
            logger.warning("Trending scan failed for query '%s': %s", query, e)

    return all_results[:15]  # Cap at 15 unique results


def format_trending_data(results: list[dict]) -> str:
    if not results:
        return "No trending AI/tech topics found today."

    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"**{i}. {r['title']}**")
        lines.append(f"   {r['snippet'][:200]}...")
        lines.append(f"   {r['url']}")
        lines.append("")
    return "\n".join(lines)
