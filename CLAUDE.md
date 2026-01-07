# Retail Cash Logistics Agent

Slack bot using Claude Agent SDK to analyze armored carrier pickups for retail cash management.

## Architecture

```
Slack @mention → slack_bot.py (Bolt) → Claude Agent SDK → mcp_server_db.py → SQLite
```

## Key Files

| File | Purpose |
|------|---------|
| `src/slack_bot.py` | Main bot - Slack Bolt + Claude Agent SDK |
| `src/mcp_server_db.py` | Custom MCP server for SQLite (JSON-RPC over stdio) |
| `data/logistics.db` | SQLite database |
| `scripts/init_db.py` | Seeds database with demo data |

## MCP Tools

Custom server at `src/mcp_server_db.py` exposes:
- `mcp__sqlite__list_tables`
- `mcp__sqlite__describe_table`
- `mcp__sqlite__read_query`
- `mcp__sqlite__write_query`

## Slack Integration

Uses `slack-bolt` directly (not MCP):
```python
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
```

## Database Tables

- `locations` - Retail stores (region, volume, risk tier)
- `carriers` - Armored companies (Brinks, Loomis, Garda)
- `pickup_schedules` - Weekly schedule per location
- `deposits` - Daily cash deposits (90 days)
- `pickup_costs` - Cost breakdown per pickup (90 days)

## Running

```bash
# Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add ANTHROPIC_API_KEY, SLACK_BOT_TOKEN, SLACK_APP_TOKEN

# Init DB
python scripts/init_db.py

# Run bot
python src/slack_bot.py
```

## Business Definitions

**Missed Pickup**: Scheduled in `pickup_schedules` but no matching `pickup_costs` record (SLA violation).

**High-Risk Cash**: High-volume locations ($30K+/day) without pickup >1 day, or any location with cash sitting >48 hours.
