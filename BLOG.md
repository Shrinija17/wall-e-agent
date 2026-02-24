# How I Built Wall-E: My Personal AI Agent That Runs 24/7 on Discord

## The Problem

I'm a Marketing Analyst Intern at JustPaid, a YC-backed AI fintech startup. Every day I need to:

- Track what 7 competitors are doing (Ramp, Brex, Zeni, Truewind, Chargebee, HighRadius, Tesorio)
- Stay on top of trending AI/tech topics for social content
- Draft X and LinkedIn posts that position JustPaid as the AI-native solution
- Hunt for job postings that match my profile (I'm on OPT with a June 2026 STEM OPT deadline)

Doing all of this manually was eating hours every day. So I built Wall-E — a personal AI agent that lives in Discord and does it all for me, automatically, 24/7.

## What Wall-E Does

Wall-E is a Discord bot powered by Groq's Llama 3.3 70B model. It runs on Railway and operates across 5 dedicated channels:

### Channels

| Channel | Purpose |
|---------|---------|
| `#wall-e` | Chat with the agent about anything |
| `#briefings` | Automated competitor intelligence briefings |
| `#trending` | Trending AI/tech topics + tweet drafts |
| `#drafts` | Social post drafts with approve/edit/skip buttons |
| `#jobs` | Curated job postings matching my resume |

### Automated Daily Schedule

- **8:00 AM** — Job scan #1 (fresh postings from last 24h)
- **8:30 AM** — Trending AI/tech scan + 3 auto-drafted tweets
- **9:00 AM** — Competitor intelligence briefing with suggested posts
- **8:00 PM** — Job scan #2 (evening batch)

### Commands

- `!briefing` — Manual competitor scan
- `!trending` — Manual trending AI/tech scan with tweet drafts
- `!jobs` — Manual job postings scan
- `!draft x <topic>` — Draft a tweet about any topic
- `!draft linkedin <topic>` — Draft a LinkedIn post
- `!pending` — View posts awaiting approval
- `!new` — Reset conversation history

### Agent Tools

Wall-E has 4 tools it can autonomously decide to use:

1. **web_search** — Real-time web search via Tavily API for competitor news, trends, research
2. **draft_social_post** — Creates a post draft, saves to database, sends approval buttons to Discord
3. **save_memory** — Stores information across conversations
4. **recall_memory** — Retrieves stored context

### Approval Workflow

When Wall-E drafts a social post, it shows up with interactive buttons:
- **Post it** — Marks as approved (copy-paste to post)
- **Edit** — Sends back for revision
- **Skip** — Rejects the draft

### Job Scanner

The job scanner is tuned for my specific profile:
- Searches 8 targeted queries focused on Marketing Analyst + entry-level Analyst roles
- Only shows jobs posted in the last 24 hours
- Scores and ranks by relevance (boosts fintech, AI, startup; penalizes senior roles)
- Returns top 20 with direct apply links
- Runs every 12 hours so I never miss a fresh posting
- Includes application tips tailored to each top pick

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **LLM** | Groq (Llama 3.3 70B Versatile) |
| **Messaging** | Discord.py |
| **Web Search** | Tavily API |
| **Database** | SQLAlchemy + aiosqlite (local) / asyncpg (production) |
| **Scheduler** | APScheduler (AsyncIOScheduler) |
| **Config** | Pydantic Settings |
| **Deployment** | Railway (Dockerfile) |
| **Repo** | GitHub (private) |

## Architecture

```
Discord User
    |
    v
discord.py Bot (handlers.py)
    |
    ├── Commands (!briefing, !trending, !jobs, !draft)
    |       |
    |       v
    |   Scheduled Jobs (APScheduler)
    |       |
    |       ├── Competitor Scanner (Tavily) → Agent → #briefings
    |       ├── Trending Scanner (Tavily) → Agent → #trending
    |       └── Job Scanner (Tavily) → Agent → #jobs
    |
    └── Free Chat (on_message)
            |
            v
        GeminiAgent (Groq Llama 3.3 70B)
            |
            ├── Tool Loop (max 10 iterations)
            |   ├── web_search → Tavily
            |   ├── draft_social_post → DB + #drafts
            |   ├── save_memory → MemoryStore
            |   └── recall_memory → MemoryStore
            |
            └── Response → Discord Channel
```

## Project Structure

```
wall-e-agent/
├── app/
│   ├── agent/
│   │   ├── claude.py          # LLM agent with agentic tool loop
│   │   ├── prompts.py         # System prompts for briefings, trending, jobs
│   │   └── tools.py           # Tool definitions + execution
│   ├── bot/
│   │   ├── handlers.py        # Discord commands + message routing
│   │   ├── approvals.py       # Interactive approve/edit/skip buttons
│   │   └── formatting.py      # Message chunking for Discord limits
│   ├── db/
│   │   ├── database.py        # SQLAlchemy async engine
│   │   └── models.py          # PostDraft, BriefingLog models
│   ├── jobs/
│   │   └── scanner.py         # Job postings scanner with relevance scoring
│   ├── memory/
│   │   └── store.py           # Persistent key-value memory
│   ├── scheduler/
│   │   ├── runner.py          # APScheduler cron job setup
│   │   └── jobs.py            # Briefing, trending, job scan functions
│   ├── social/
│   │   ├── competitors.py     # 7-competitor Tavily scanner
│   │   └── trending.py        # Trending AI/tech topic scanner
│   ├── config.py              # Pydantic Settings with lazy proxy
│   └── main.py                # Entry point
├── Dockerfile
├── railway.toml
├── pyproject.toml
└── .env.example
```

## The Journey

### Evolution of the Stack

The project went through several iterations:

1. **LLM**: Started with Anthropic Claude API → switched to Google Gemini → landed on **Groq (Llama 3.3 70B)** for the free tier and fast inference
2. **Messaging**: Started with Telegram → switched to **Discord** for richer UI (buttons, channels, embeds)
3. **Deployment**: Local development → **Railway** for 24/7 cloud uptime

### Key Challenges

- **Groq/Llama tool calling quirks**: Llama 3.3 sometimes generates malformed tool calls in a text format (`<function=name>`) instead of using the proper API. Fixed by limiting which tools are available per task and adding error handling.
- **Discord on_ready conflicts**: Had two `@bot.event async def on_ready()` handlers (one in handlers.py, one in main.py) — only the last one fires. Merged them.
- **Railway env vars**: The Railway dashboard UI was uncooperative for setting environment variables. Solved by creating an API token and using the Railway GraphQL API directly via curl.

## What's Next

- Auto-posting to X and LinkedIn on approval (Phase 2)
- Weekly content calendar generation
- Real-time competitor alerts
- Resume-tailored cover letter drafts per job posting

## About Me

I'm Shrinija, an M.S. Business Analytics graduate from Baruch College (CUNY). I'm building at the intersection of AI, marketing, and analytics. Currently looking for entry-level Analyst roles — if you're hiring, Wall-E probably already found your posting.

**GitHub**: [github.com/Shrinija17/wall-e-agent](https://github.com/Shrinija17/wall-e-agent)
