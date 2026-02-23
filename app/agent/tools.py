import json
import logging

from tavily import AsyncTavilyClient

from app.config import settings
from app.db.database import async_session
from app.db.models import PostDraft

logger = logging.getLogger(__name__)

# Tool definitions in OpenAI-compatible format (used by Groq)
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for information — competitor news, industry trends, research, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "draft_social_post",
            "description": "Create a draft social media post and send it for Shrinija's approval via Telegram. Always use this when creating content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "enum": ["x", "linkedin"],
                        "description": "Target platform",
                    },
                    "content": {"type": "string", "description": "The post content"},
                },
                "required": ["platform", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "Save a piece of information for future reference. Use for things worth remembering across conversations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Short descriptive key (e.g., 'justpaid_funding_round')",
                    },
                    "value": {"type": "string", "description": "The information to store"},
                },
                "required": ["key", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall_memory",
            "description": "Retrieve a stored memory by key, or get all memories if no key specified.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "The key to look up. Omit to get all memories.",
                    },
                },
            },
        },
    },
]


async def execute_tool(name: str, input_data: dict, memory_store, send_approval_fn=None) -> str:
    try:
        if name == "web_search":
            return await _web_search(input_data["query"])
        elif name == "draft_social_post":
            return await _draft_social_post(
                input_data["platform"], input_data["content"], send_approval_fn
            )
        elif name == "save_memory":
            return await _save_memory(input_data["key"], input_data["value"], memory_store)
        elif name == "recall_memory":
            return await _recall_memory(input_data.get("key"), memory_store)
        else:
            return f"Unknown tool: {name}"
    except Exception as e:
        logger.exception("Tool execution error: %s", name)
        return f"Error executing {name}: {e}"


async def _web_search(query: str) -> str:
    client = AsyncTavilyClient(api_key=settings.tavily_api_key)
    response = await client.search(query=query, max_results=5, search_depth="basic")
    results = response.get("results", [])
    if not results:
        return "No results found."
    lines = []
    for r in results:
        lines.append(f"**{r['title']}**")
        lines.append(r.get("content", "")[:300])
        lines.append(r["url"])
        lines.append("")
    return "\n".join(lines)


async def _draft_social_post(platform: str, content: str, send_approval_fn) -> str:
    session_factory = async_session()
    async with session_factory() as session:
        draft = PostDraft(platform=platform, content=content, status="pending")
        session.add(draft)
        await session.commit()
        await session.refresh(draft)
        draft_id = draft.id

    if send_approval_fn:
        await send_approval_fn(draft_id, platform, content)

    return f"Draft #{draft_id} created for {platform} and sent for approval."


async def _save_memory(key: str, value: str, memory_store) -> str:
    await memory_store.set(key, value)
    return f"Saved memory: {key}"


async def _recall_memory(key: str | None, memory_store) -> str:
    if key:
        value = await memory_store.get(key)
        return value if value else f"No memory found for key: {key}"
    else:
        memories = await memory_store.get_all()
        if not memories:
            return "No memories stored yet."
        return json.dumps(memories, indent=2)
