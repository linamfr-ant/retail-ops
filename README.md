# Retail Cash Logistics Agent

A Slack bot powered by the **Claude Agent SDK** that analyzes armored carrier pickup logistics for retail cash management.

## How It Works

```
Slack @mention → Slack Bot (Bolt) → Claude Agent SDK → Custom MCP Server → SQLite DB
                                           ↓
                                    Agent Response → Slack Channel
```

1. User @mentions the bot in Slack with a query
2. `slack_bot.py` receives the message via Slack Bolt (Socket Mode)
3. Query is sent to Claude via the **Claude Agent SDK**
4. Claude uses MCP tools to query the SQLite database (`mcp_server_db.py`)
5. Response streams back to the Slack thread

## What It Analyzes

- **Missed Pickups (SLA Credits)** - Scheduled pickups that didn't occur
- **Deposit Patterns** - Peak days, trends, volume patterns
- **Cost Optimization** - Overtime costs, inefficient routes
- **Risk Assessment** - Cash sitting times, security exposure
- **Route Consolidation** - Nearby stores that could share pickup days

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Set Up Environment

```bash
cp .env.example .env
# Edit .env and add:
#   ANTHROPIC_API_KEY=your_api_key
#   SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
#   SLACK_APP_TOKEN=xapp-your-slack-app-token
```

### 3. Set Up Slack Bot

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app
2. Under **OAuth & Permissions**, add these Bot Token scopes:
   - `app_mentions:read` - Receive @mentions
   - `chat:write` - Send messages
   - `channels:history` - Read channel messages
   - `im:history` - Read DMs
3. Under **Socket Mode**, enable it and generate an App-Level Token with `connections:write` scope
4. Under **Event Subscriptions**, enable and subscribe to:
   - `app_mention`
   - `message.im`
5. Install the app to your workspace
6. Copy tokens to your `.env`:
   - **Bot User OAuth Token** (`xoxb-...`) → `SLACK_BOT_TOKEN`
   - **App-Level Token** (`xapp-...`) → `SLACK_APP_TOKEN`
7. Create channel `#cash-logistics-alerts` and invite the bot

### 4. Initialize Database

```bash
python scripts/init_db.py
```

This creates `data/logistics.db` with:
- 15 retail locations across 5 regions
- 3 carrier companies (Brinks, Loomis, Garda)
- 90 days of deposit history
- 90 days of pickup cost history
- **5 missed pickup scenarios** for demo alerts

### 5. Run the Slack Bot

```bash
python src/slack_bot.py
```

The bot will listen for:
- **@mentions** in channels: `@bot analyze deposit patterns`
- **Direct messages**: Just type your query

## Example Queries (via Slack)

### Analysis Queries
```
@bot Analyze deposit patterns against pickup schedules
@bot Which stores are over-serviced relative to their cash volume?
@bot Identify cost savings through schedule optimization
@bot Show me stores with high cash sitting risk
```

### Alerting Queries
```
@bot Alert on all missed deposits in the last 7 days
@bot Send alert for stores with cash sitting more than 48 hours
@bot Notify about high-risk accumulation situations
```

## Database Schema

| Table | Description |
|-------|-------------|
| `locations` | Retail stores with region, volume, risk tier |
| `carriers` | Armored carrier companies with pricing |
| `pickup_schedules` | Weekly pickup schedule per location |
| `deposits` | Daily cash deposit records |
| `pickup_costs` | Cost breakdown per pickup |

## Demo Scenarios

The seed data includes intentional inefficiencies for the agent to discover:

1. **Under-serviced high-volume stores** - Brooklyn Heights has $38K daily volume but only 1 pickup/week
2. **Over-serviced low-volume stores** - Cleveland and Detroit have 3 pickups/week for <$8K daily volume
3. **Schedule misalignment** - Peak deposits on weekends, pickups on weekdays
4. **Consolidation opportunities** - Hartford and Providence have same carrier, same days, different times

### Missed Pickups (for Slack Alerts)

The seed data creates **5 missed pickup scenarios** in the last 7 days:

| Store | Volume | Missed | Cash at Risk | Reason |
|-------|--------|--------|--------------|--------|
| LA Downtown (WE-001) | $55K/day | 3 days | ~$165,000 | Security incident |
| Manhattan Midtown (NE-002) | $62K/day | 2 days | ~$124,000 | Holiday staffing |
| Brooklyn Heights (NE-003) | $38K/day | 1 day | ~$38,000 | Vehicle breakdown |
| Miami Beach (SE-002) | $35K/day | 1 day | ~$35,000 | Route rescheduled |
| Orlando Tourist (SE-003) | $42K/day | 1 day | ~$42,000 | Weather delay |

**Total cash at risk: ~$404,000**

## Project Structure

```
retail-ops/
├── config/
│   └── mcp_config.json      # MCP server configuration (reference)
├── data/
│   └── logistics.db         # SQLite database (generated)
├── database/
│   ├── models.py            # SQLAlchemy models
│   ├── connection.py        # DB utilities
│   └── seed_data.py         # Mock data generator
├── scripts/
│   └── init_db.py           # Database initialization
├── src/
│   ├── mcp_server_db.py     # Custom SQLite MCP server (JSON-RPC over stdio)
│   └── slack_bot.py         # Slack bot + Claude Agent SDK integration
├── requirements.txt
└── README.md
```

## Architecture

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Slack User     │     │   slack_bot.py   │     │  Claude Agent    │
│   @mentions bot  │────▶│   (Bolt SDK)     │────▶│  SDK query()     │
└──────────────────┘     └──────────────────┘     └────────┬─────────┘
                                  ▲                        │
                                  │                        ▼
                                  │               ┌──────────────────┐
                         Response streamed        │ mcp_server_db.py │
                         back to thread           │ (SQLite MCP)     │
                                  │               └────────┬─────────┘
                                  │                        │
                                  │                        ▼
                                  │               ┌──────────────────┐
                                  └───────────────│  logistics.db    │
                                                  └──────────────────┘
```

## Key Components

### 1. Slack Bot (`src/slack_bot.py`)

Uses **Slack Bolt** (Socket Mode) to listen for @mentions and DMs. When a message arrives:

```python
from claude_agent_sdk import query, ClaudeAgentOptions

options = ClaudeAgentOptions(
    system_prompt=SYSTEM_PROMPT,
    mcp_servers={
        "sqlite": {
            "command": sys.executable,
            "args": ["src/mcp_server_db.py"],
        },
    },
    allowed_tools=["mcp__sqlite__list_tables", "mcp__sqlite__read_query", ...],
    max_turns=30,
)

async for message in query(prompt=user_query, options=options):
    # Stream responses back to Slack thread
    await say(text=message.text, thread_ts=thread_ts)
```

### 2. Custom MCP Server (`src/mcp_server_db.py`)

A lightweight JSON-RPC server that provides SQLite access via MCP protocol:

- `list_tables` - List all database tables
- `describe_table` - Get schema for a table
- `read_query` - Execute SELECT queries
- `write_query` - Execute INSERT/UPDATE/DELETE

The agent constructs SQL queries based on:
- Database schema (provided in system prompt)
- Business definitions (missed pickups, SLA credits, etc.)
- User's natural language question

### 3. Business Logic

**Missed Pickup (for SLA credits):**
A pickup was SCHEDULED (exists in `pickup_schedules`) but did NOT occur (no matching `pickup_costs` record).

**Cost Optimization:**
- High `overtime_cost` relative to `base_cost`
- Low `cash_collected` relative to `total_cost`
- Stores in same region with different pickup days
