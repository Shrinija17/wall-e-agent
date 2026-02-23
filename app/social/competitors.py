import logging

from tavily import AsyncTavilyClient

from app.config import settings

logger = logging.getLogger(__name__)

COMPETITORS = [
    {"name": "Ramp", "domain": "ramp.com", "focus": "corporate cards & expense management"},
    {"name": "Brex", "domain": "brex.com", "focus": "financial stack for startups"},
    {"name": "Zeni", "domain": "zeni.ai", "focus": "AI bookkeeping"},
    {"name": "Truewind", "domain": "truewind.ai", "focus": "AI-powered accounting"},
    {"name": "Chargebee", "domain": "chargebee.com", "focus": "subscription billing"},
    {"name": "HighRadius", "domain": "highradius.com", "focus": "AR automation"},
    {"name": "Tesorio", "domain": "tesorio.com", "focus": "cash flow management"},
]


async def scan_competitor(client: AsyncTavilyClient, competitor: dict) -> dict:
    query = f"{competitor['name']} {competitor['focus']} news announcements 2026"
    try:
        response = await client.search(
            query=query,
            max_results=3,
            search_depth="basic",
        )
        results = response.get("results", [])
        snippets = [
            {"title": r["title"], "url": r["url"], "snippet": r.get("content", "")[:300]}
            for r in results
        ]
        return {
            "name": competitor["name"],
            "focus": competitor["focus"],
            "results": snippets,
        }
    except Exception as e:
        logger.warning("Failed to scan %s: %s", competitor["name"], e)
        return {
            "name": competitor["name"],
            "focus": competitor["focus"],
            "results": [],
            "error": str(e),
        }


async def scan_all_competitors() -> list[dict]:
    client = AsyncTavilyClient(api_key=settings.tavily_api_key)
    results = []
    for competitor in COMPETITORS:
        result = await scan_competitor(client, competitor)
        results.append(result)
    return results


def format_competitor_data(data: list[dict]) -> str:
    lines = []
    for comp in data:
        lines.append(f"\n### {comp['name']} ({comp['focus']})")
        if comp.get("error"):
            lines.append(f"  ⚠ Scan failed: {comp['error']}")
            continue
        if not comp["results"]:
            lines.append("  No recent news found.")
            continue
        for r in comp["results"]:
            lines.append(f"  - **{r['title']}**")
            lines.append(f"    {r['snippet'][:200]}...")
            lines.append(f"    {r['url']}")
    return "\n".join(lines)
