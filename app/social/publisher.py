# Phase 2: X API + LinkedIn API auto-posting
#
# When implemented, this module will:
# 1. Post approved drafts directly to X via tweepy / X API v2
# 2. Post approved drafts to LinkedIn via LinkedIn API
# 3. Be triggered from approvals.py when a draft is approved
#
# For now, approved drafts are copy-pasted manually.


async def post_to_x(content: str) -> dict:
    raise NotImplementedError("X API posting coming in Phase 2")


async def post_to_linkedin(content: str) -> dict:
    raise NotImplementedError("LinkedIn API posting coming in Phase 2")
