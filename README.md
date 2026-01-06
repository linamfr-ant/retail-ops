# Armored Carrier Logistics Agent

A demo showcasing the **Claude Agent SDK** (`anthropic-agentsdk`) with SQLite MCP integration for analyzing armored carrier pickup logistics.

## Overview

This agent analyzes retail cash management operations, including:
- **Deposit pattern analysis** - Peak days, trends, volume patterns
- **Schedule optimization** - Mismatches between deposits and pickups
- **Cost analysis** - Per-pickup costs, overtime trends
- **Risk assessment** - Cash sitting times, security exposure
- **Route consolidation** - Efficiency opportunities
- **Slack alerting** - Automatic alerts for missed deposits to `#cash-logistics-alerts`

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install Claude Agent SDK and dependencies
pip install -r requirements.txt

# The SQLite MCP server is invoked via uvx (auto-installs on first run)
# Or pre-install: pip install mcp-server-sqlite
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
│   └── mcp_config.json      # MCP server configuration
├── data/
│   └── logistics.db         # SQLite database (generated)
├── database/
│   ├── models.py            # SQLAlchemy models
│   ├── connection.py        # DB utilities
│   └── seed_data.py         # Mock data generator
├── scripts/
│   └── init_db.py           # Database initialization
├── src/
│   ├── agent.py             # Agent definition (Agent SDK + MCP)
│   └── slack_bot.py         # Slack bot listener
├── requirements.txt
└── README.md
```

## Architecture

```
┌─────────────────┐                              ┌─────────────────┐
│  Slack Channel  │                         ┌───▶│   SQLite MCP    │
│ #cash-logistics │                         │    │    Server       │
│    -alerts      │                         │    └────────┬────────┘
└────────┬────────┘     ┌─────────────────┐ │             │
         │              │  Claude Agent   │─┤             ▼
         │   @mention   │  (Agent SDK)    │ │    ┌─────────────────┐
         └─────────────▶│                 │ │    │  logistics.db   │
                        └────────┬────────┘ │    └─────────────────┘
                                 │          │
                                 │          │    ┌─────────────────┐
                                 │          └───▶│   Slack MCP     │
                                 │               │    Server       │
                                 │               └────────┬────────┘
                                 │                        │
                                 └────────────────────────┘
                                      Response + Alerts
```

### Claude Agent SDK Components

```python
from agents import Agent, Runner
from agents.mcp import MCPServerStdio

# SQLite MCP for database queries
sqlite_mcp = MCPServerStdio(
    name="sqlite",
    command="uvx",
    args=["mcp-server-sqlite", "--db-path", "data/logistics.db"],
)

# Slack MCP for alerting
slack_mcp = MCPServerStdio(
    name="slack",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-slack"],
    env={"SLACK_BOT_TOKEN": os.getenv("SLACK_BOT_TOKEN")},
)

# Create agent with both MCP servers
agent = Agent(
    name="Logistics Analyst",
    model="claude-sonnet-4-20250514",
    instructions=SYSTEM_PROMPT,
    mcp_servers=[sqlite_mcp, slack_mcp],
)

# Run queries (analysis + alerting)
result = await Runner.run(agent, "Alert on missed deposits")
```

The agent uses MCP (Model Context Protocol) to:
1. Query the SQLite database for logistics analysis
2. Send alerts to Slack when issues are detected
