import datetime as dt

from sqlalchemy import delete, select

from app.db.database import async_session
from app.db.models import ConversationMessage, MemoryEntry


class MemoryStore:
    async def get(self, key: str) -> str | None:
        async with async_session() as session:
            result = await session.execute(
                select(MemoryEntry.value).where(MemoryEntry.key == key)
            )
            row = result.scalar_one_or_none()
            return row

    async def set(self, key: str, value: str) -> None:
        async with async_session() as session:
            result = await session.execute(
                select(MemoryEntry).where(MemoryEntry.key == key)
            )
            entry = result.scalar_one_or_none()
            if entry:
                entry.value = value
            else:
                session.add(MemoryEntry(key=key, value=value))
            await session.commit()

    async def get_all(self) -> dict[str, str]:
        async with async_session() as session:
            result = await session.execute(select(MemoryEntry))
            entries = result.scalars().all()
            return {e.key: e.value for e in entries}

    async def get_context_summary(self) -> str:
        memories = await self.get_all()
        if not memories:
            return "No stored memories yet."
        lines = [f"- **{k}**: {v}" for k, v in memories.items()]
        return "## Stored Memories\n" + "\n".join(lines)

    async def save_message(self, role: str, content: str) -> None:
        async with async_session() as session:
            session.add(ConversationMessage(role=role, content=content))
            await session.commit()

    async def get_recent_messages(self, limit: int = 20) -> list[dict[str, str]]:
        async with async_session() as session:
            result = await session.execute(
                select(ConversationMessage)
                .order_by(ConversationMessage.id.desc())
                .limit(limit)
            )
            messages = result.scalars().all()
            return [
                {"role": m.role, "content": m.content} for m in reversed(messages)
            ]

    async def clear_conversation(self) -> None:
        async with async_session() as session:
            await session.execute(delete(ConversationMessage))
            await session.commit()
