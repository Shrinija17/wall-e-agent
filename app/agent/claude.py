import json
import logging

from groq import AsyncGroq

from app.agent.prompts import build_system_prompt
from app.agent.tools import TOOL_DEFINITIONS, execute_tool
from app.config import settings
from app.memory.store import MemoryStore

logger = logging.getLogger(__name__)


def _clean_message(message) -> dict:
    """Convert an assistant message to dict with only Groq-supported fields."""
    d = {"role": "assistant"}
    if message.content:
        d["content"] = message.content
    if message.tool_calls:
        d["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in message.tool_calls
        ]
    return d


class GeminiAgent:
    """LLM agent powered by Groq (Llama 3.3 70B). Class name kept for import compatibility."""

    def __init__(self, memory_store: MemoryStore, send_approval_fn=None):
        self.client = AsyncGroq(api_key=settings.groq_api_key)
        self.memory = memory_store
        self.send_approval_fn = send_approval_fn

    async def chat(self, user_message: str) -> str:
        await self.memory.save_message("user", user_message)

        memory_context = await self.memory.get_context_summary()
        system_prompt = build_system_prompt(memory_context)
        history = await self.memory.get_recent_messages(settings.max_conversation_history)

        # Build messages in OpenAI format
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        if not history or history[-1]["content"] != user_message:
            messages.append({"role": "user", "content": user_message})

        # Agentic tool loop
        response_text = ""
        for _ in range(settings.max_tool_iterations):
            response = await self.client.chat.completions.create(
                model=settings.groq_model,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                max_tokens=4096,
            )

            choice = response.choices[0]
            message = choice.message

            if message.content:
                response_text = message.content

            # If no tool calls, we're done
            if not message.tool_calls:
                break

            # Add assistant message with tool calls
            messages.append(_clean_message(message))

            # Execute each tool and add results
            for tool_call in message.tool_calls:
                fn = tool_call.function
                logger.info("Executing tool: %s", fn.name)
                args = json.loads(fn.arguments)
                result = await execute_tool(
                    fn.name,
                    args,
                    self.memory,
                    self.send_approval_fn,
                )
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

        if response_text:
            await self.memory.save_message("assistant", response_text)

        return response_text or "I processed your request but didn't generate a text response."

    async def run_briefing(self, briefing_prompt: str, tools: list | None = None) -> str:
        """Run a briefing prompt without saving to conversation history.

        Args:
            tools: Optional list of tool definitions to use. Defaults to
                   only draft_social_post. Pass empty list for no tools.
        """
        memory_context = await self.memory.get_context_summary()
        system_prompt = build_system_prompt(memory_context)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": briefing_prompt},
        ]

        # Only include draft_social_post by default — avoids Llama
        # generating malformed save_memory/recall_memory calls
        if tools is None:
            tools = [t for t in TOOL_DEFINITIONS if t["function"]["name"] == "draft_social_post"]

        api_kwargs = {
            "model": settings.groq_model,
            "messages": messages,
            "max_tokens": 4096,
        }
        if tools:
            api_kwargs["tools"] = tools
            api_kwargs["tool_choice"] = "auto"

        response_text = ""
        for _ in range(settings.max_tool_iterations):
            try:
                response = await self.client.chat.completions.create(**api_kwargs)
            except Exception as e:
                logger.warning("Briefing API error: %s", e)
                break

            choice = response.choices[0]
            message = choice.message

            if message.content:
                response_text = message.content

            if not message.tool_calls:
                break

            messages.append(_clean_message(message))

            for tool_call in message.tool_calls:
                fn = tool_call.function
                logger.info("Briefing tool: %s", fn.name)
                try:
                    args = json.loads(fn.arguments)
                    result = await execute_tool(
                        fn.name,
                        args,
                        self.memory,
                        self.send_approval_fn,
                    )
                except Exception as e:
                    logger.warning("Briefing tool error: %s — %s", fn.name, e)
                    result = f"Tool error: {e}"
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

        return response_text or "Briefing completed but no text was generated."
