import datetime as dt
import logging

import discord
from sqlalchemy import select

from app.db.database import async_session
from app.db.models import PostDraft

logger = logging.getLogger(__name__)


class ApprovalView(discord.ui.View):
    def __init__(self, draft_id: int):
        super().__init__(timeout=None)
        self.draft_id = draft_id

    @discord.ui.button(label="Post it", style=discord.ButtonStyle.success, emoji="✅")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        session_factory = async_session()
        async with session_factory() as session:
            result = await session.execute(
                select(PostDraft).where(PostDraft.id == self.draft_id)
            )
            draft = result.scalar_one_or_none()
            if not draft:
                await interaction.response.edit_message(content="Draft not found.", view=None)
                return

            draft.status = "approved"
            draft.resolved_at = dt.datetime.now(dt.timezone.utc)
            await session.commit()

            await interaction.response.edit_message(
                content=(
                    f"✅ **Draft #{self.draft_id} approved!**\n\n{draft.content}\n\n"
                    f"*Copy and post to {draft.platform}. Auto-posting coming in Phase 2!*"
                ),
                view=None,
            )

    @discord.ui.button(label="Edit", style=discord.ButtonStyle.primary, emoji="✏️")
    async def edit(self, interaction: discord.Interaction, button: discord.ui.Button):
        session_factory = async_session()
        async with session_factory() as session:
            result = await session.execute(
                select(PostDraft).where(PostDraft.id == self.draft_id)
            )
            draft = result.scalar_one_or_none()
            if not draft:
                await interaction.response.edit_message(content="Draft not found.", view=None)
                return

            await interaction.response.edit_message(
                content=(
                    f"✏️ **Draft #{self.draft_id}** — Send me your edits.\n\n"
                    f"Current draft:\n{draft.content}"
                ),
                view=None,
            )

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary, emoji="⏭")
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        session_factory = async_session()
        async with session_factory() as session:
            result = await session.execute(
                select(PostDraft).where(PostDraft.id == self.draft_id)
            )
            draft = result.scalar_one_or_none()
            if not draft:
                await interaction.response.edit_message(content="Draft not found.", view=None)
                return

            draft.status = "rejected"
            draft.resolved_at = dt.datetime.now(dt.timezone.utc)
            await session.commit()

            await interaction.response.edit_message(
                content=f"⏭ Draft #{self.draft_id} skipped.",
                view=None,
            )


async def send_approval_message(
    draft_id: int, platform: str, content: str, channel: discord.TextChannel
) -> None:
    platform_label = "𝕏 Twitter" if platform == "x" else "LinkedIn"
    text = f"📝 **Draft #{draft_id}** — {platform_label}\n\n{content}"
    view = ApprovalView(draft_id)
    await channel.send(text, view=view)


async def get_pending_drafts() -> list[PostDraft]:
    session_factory = async_session()
    async with session_factory() as session:
        result = await session.execute(
            select(PostDraft)
            .where(PostDraft.status == "pending")
            .order_by(PostDraft.created_at.desc())
        )
        return list(result.scalars().all())
