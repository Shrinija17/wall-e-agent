import re

# Discord message limit
MAX_MESSAGE_LENGTH = 2000


def chunk_message(text: str) -> list[str]:
    """Split a long message into Discord-safe chunks, breaking at paragraph boundaries."""
    if len(text) <= MAX_MESSAGE_LENGTH:
        return [text]

    chunks = []
    while text:
        if len(text) <= MAX_MESSAGE_LENGTH:
            chunks.append(text)
            break

        # Try to break at a double newline (paragraph)
        split_at = text.rfind("\n\n", 0, MAX_MESSAGE_LENGTH)
        if split_at == -1:
            split_at = text.rfind("\n", 0, MAX_MESSAGE_LENGTH)
        if split_at == -1:
            split_at = text.rfind(" ", 0, MAX_MESSAGE_LENGTH)
        if split_at == -1:
            split_at = MAX_MESSAGE_LENGTH

        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")

    return chunks
