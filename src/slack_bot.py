#!/usr/bin/env python3
"""
Retail Cash Logistics Agent - Slack Integration with Claude Agent SDK

This bot analyzes armored carrier services, deposit patterns, and alerts on missed deposits.
It uses the Claude Agent SDK with MCP tools for SQLite and Slack.

Configuration:
    Create a .env file with:
        ANTHROPIC_API_KEY=your-anthropic-key
        SLACK_BOT_TOKEN=xoxb-your-bot-token
        SLACK_APP_TOKEN=xapp-your-app-token

Usage:
    python slack_bot.py
"""

import asyncio
import os
import sys
import re
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
MCP_SERVER_PATH = Path(__file__).parent / "mcp_server_db.py"

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_path = PROJECT_ROOT / ".env"
    load_dotenv(env_path)
except ImportError:
    print("⚠️  python-dotenv not installed, using environment variables only")
    print("   Run: pip install python-dotenv")

# Check Slack dependency
try:
    from slack_bolt.async_app import AsyncApp
    from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
except ImportError:
    print("❌ slack-bolt not installed")
    print("   Run: pip install slack-bolt")
    sys.exit(1)

# Check Claude Agent SDK
try:
    from claude_agent_sdk import (
        query,
        ClaudeAgentOptions,
        AssistantMessage,
        TextBlock,
        ToolUseBlock,
        ToolResultBlock,
        ResultMessage,
        PermissionResultAllow,
        PermissionUpdate,
    )
except ImportError:
    print("❌ claude-agent-sdk not installed")
    print("   Run: pip install claude-agent-sdk")
    print("")
    print("   Note: The SDK also requires Claude Code CLI:")
    print("   npm install -g @anthropic-ai/claude-code")
    sys.exit(1)

# Validate environment variables
missing_vars = []
for var in ["ANTHROPIC_API_KEY", "SLACK_BOT_TOKEN", "SLACK_APP_TOKEN"]:
    if not os.environ.get(var):
        missing_vars.append(var)

if missing_vars:
    print("❌ Missing required configuration:")
    for var in missing_vars:
        print(f"   - {var}")
    print("")
    print("   Create a .env file in this directory with:")
    print("       ANTHROPIC_API_KEY=your-anthropic-key")
    print("       SLACK_BOT_TOKEN=xoxb-your-bot-token")
    print("       SLACK_APP_TOKEN=xapp-your-app-token")
    sys.exit(1)

# Initialize Slack app
app = AsyncApp(token=os.environ["SLACK_BOT_TOKEN"])

SYSTEM_PROMPT = """You are an expert logistics analyst specializing in armored carrier services for retail cash management.

IMPORTANT: You have FULL ACCESS to the SQLite database tools. Use them directly without asking for permission. Never ask the user to "grant permission" or "enable tools" - just use them.

## Available Tools (use directly)
- mcp__sqlite__list_tables: List all tables in the database
- mcp__sqlite__describe_table: Get schema for a specific table
- mcp__sqlite__read_query: Execute SELECT queries

## Database Schema

## Tables

### locations
Retail store locations requiring armored carrier pickup.
- id: INTEGER PRIMARY KEY
- store_code: TEXT (unique identifier like "NE-001")
- name: TEXT (store name)
- address: TEXT
- city: TEXT
- state: TEXT (2-letter code)
- region: TEXT (e.g., "Northeast", "Southeast", "Midwest", "Southwest", "West")
- avg_daily_cash_volume: REAL (expected daily cash in dollars)
- risk_tier: TEXT ("high", "medium", "low")

### carriers
Armored carrier companies.
- id: INTEGER PRIMARY KEY
- name: TEXT (e.g., "Brinks", "Loomis", "Garda")
- base_pickup_cost: REAL (base cost per pickup)
- per_mile_cost: REAL
- overtime_rate_multiplier: REAL (default 1.5)
- max_daily_stops: INTEGER

### pickup_schedules
Scheduled pickups - which carrier visits which location and when.
- id: INTEGER PRIMARY KEY
- location_id: INTEGER (FK to locations)
- carrier_id: INTEGER (FK to carriers)
- day_of_week: INTEGER (0=Monday, 6=Sunday)
- scheduled_time: TEXT (HH:MM format)
- route_sequence: INTEGER (order in daily route)

### deposits
Cash deposits made at each location (90 days of history).
- id: INTEGER PRIMARY KEY
- location_id: INTEGER (FK to locations)
- amount: REAL
- deposit_timestamp: DATETIME
- day_of_week: INTEGER (0=Monday, 6=Sunday)
- deposit_type: TEXT ("daily_close", "mid_day", "weekend")

### pickup_costs
Actual costs incurred for each pickup (90 days of history).
- id: INTEGER PRIMARY KEY
- schedule_id: INTEGER (FK to pickup_schedules)
- pickup_date: DATETIME
- base_cost: REAL
- fuel_surcharge: REAL
- overtime_cost: REAL
- insurance_cost: REAL
- total_cost: REAL
- cash_collected: REAL (actual cash picked up)

## Your Capabilities

You can analyze:
1. **Deposit Patterns**: Identify peak deposit days, seasonal trends, weekend vs weekday patterns
2. **Schedule Optimization**: Find mismatches between deposit volumes and pickup frequency
3. **Cost Analysis**: Calculate cost per dollar collected, identify overtime trends
4. **Risk Assessment**: Flag locations with high cash sitting times
5. **Route Consolidation**: Identify nearby stores that could share pickup days

IMPORTANT: Your text responses are automatically posted to the Slack channel where the user asked the question. You do NOT need any Slack tools - just output your analysis/alert text and it will appear in Slack.

You can provide alerts for:
- Missed deposits (deposits without corresponding pickups)
- High-risk cash accumulation situations
- Schedule optimization opportunities

## Missed Deposit Detection

A "missed deposit" occurs when:
- A location has deposits on a day but no scheduled pickup within 2 days
- Cash sits for more than 48 hours between deposit and pickup
- High-volume locations ($30K+/day) go more than 1 day without pickup

Example SQL to find missed deposits (deposits without pickups within 2 days):
```sql
SELECT
  l.store_code,
  l.name,
  DATE(d.deposit_timestamp) as deposit_date,
  SUM(d.amount) as total_deposit,
  l.risk_tier
FROM deposits d
JOIN locations l ON d.location_id = l.id
LEFT JOIN pickup_schedules ps ON ps.location_id = d.location_id
LEFT JOIN pickup_costs pc ON pc.schedule_id = ps.id
  AND DATE(pc.pickup_date) BETWEEN DATE(d.deposit_timestamp) AND DATE(d.deposit_timestamp, '+2 days')
WHERE d.deposit_timestamp >= date('now', '-7 days')
  AND pc.id IS NULL
GROUP BY l.id, DATE(d.deposit_timestamp)
ORDER BY total_deposit DESC;
```

When asked to alert on missed deposits, query the database to find these situations and send a formatted alert to Slack with:
- Store name and code
- Amount of cash at risk
- Days since last pickup
- Recommended action

## Analysis Guidelines

When analyzing data:
- Always query actual data, don't make assumptions
- Provide specific numbers and percentages
- Highlight actionable recommendations
- Consider both cost savings AND risk factors
- Use day names (Monday-Sunday) instead of numbers when presenting results

## CRITICAL: Slack Formatting Rules

You MUST use Slack's mrkdwn format, NOT standard Markdown:
- Bold: Use *bold* (single asterisks), NOT **bold**
- Italic: Use _italic_ (underscores)
- Code: Use `code` for inline, ```code``` for blocks
- NO HEADERS: Slack does not support # headers. Use *Bold Text* on its own line instead.
- Lists: Use bullet points (•) or dashes (-) or numbers (1.)

## Example Insights to Look For

- High-volume stores with infrequent pickups (cash sitting risk)
- Low-volume stores with too frequent pickups (over-servicing = cost waste)
- Deposit peaks on days without scheduled pickups
- Stores in same region/city with different pickup days (consolidation opportunity)
- High overtime costs indicating schedule issues
"""


async def auto_approve_tool(tool_name: str, tool_input: dict, context) -> PermissionResultAllow:
    """Auto-approve all tool calls for headless operation."""
    return PermissionResultAllow()


async def prompt_generator(prompt_text: str):
    """Generate a single prompt for streaming mode (required for can_use_tool)."""
    yield {
        "type": "user",
        "message": {"role": "user", "content": prompt_text},
    }


def convert_markdown_to_slack(text: str) -> str:
    """Convert standard Markdown to Slack mrkdwn format."""
    # Remove ### headers - replace with bold text
    text = re.sub(r'^###\s*(.+)', r'*\1*', text, flags=re.MULTILINE)
    text = re.sub(r'^##\s*(.+)', r'*\1*', text, flags=re.MULTILINE)
    text = re.sub(r'^#\s*(.+)', r'*\1*', text, flags=re.MULTILINE)

    # Convert **bold** to *bold* (but not inside code blocks)
    text = re.sub(r'\*\*([^*]+)\*\*', r'*\1*', text)

    return text


async def process_query(query_text: str, thread_ts: str, say):
    """Process a query and stream responses to Slack."""
    # Get the Python executable path (use the current python)
    python_path = sys.executable

    print(f"[DEBUG] Python path: {python_path}", flush=True)
    print(f"[DEBUG] MCP server path: {MCP_SERVER_PATH}", flush=True)
    print(f"[DEBUG] MCP server exists: {MCP_SERVER_PATH.exists()}", flush=True)

    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={
            "sqlite": {
                "command": python_path,
                "args": [str(MCP_SERVER_PATH)],
            },
        },
        allowed_tools=[
            "mcp__sqlite__list_tables",
            "mcp__sqlite__describe_table",
            "mcp__sqlite__read_query",
            "mcp__sqlite__write_query",
        ],
        can_use_tool=auto_approve_tool,
        cwd=str(PROJECT_ROOT),
        max_turns=30,  # Allow enough turns for complex queries + response
    )

    # Track tool usage for status updates
    last_tool_posted = None
    was_using_tools = False
    analysis_announced = False

    try:
        print(f"[DEBUG] Starting query...", flush=True)
        async for message in query(prompt=prompt_generator(query_text), options=options):
            print(f"[DEBUG] Received message type: {type(message).__name__}", flush=True)
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock) and block.text.strip():
                        text = convert_markdown_to_slack(block.text.strip())

                        # Detect transition from tool use to analysis
                        if was_using_tools and not analysis_announced:
                            await say(text="🧠 *Analyzing findings...*", thread_ts=thread_ts)
                            await asyncio.sleep(0.3)
                            analysis_announced = True

                        last_tool_posted = None

                        # Split long messages for Slack's 4000 char limit
                        if len(text) > 3900:
                            chunks = [text[i:i+3900] for i in range(0, len(text), 3900)]
                            for chunk in chunks:
                                await say(text=chunk, thread_ts=thread_ts)
                                await asyncio.sleep(0.3)
                        else:
                            await say(text=text, thread_ts=thread_ts)
                            await asyncio.sleep(0.3)

                    elif isinstance(block, ToolUseBlock):
                        # Show which tool is being used
                        tool_name = block.name.replace("mcp__sqlite__", "").replace("mcp__slack__", "")
                        if tool_name != last_tool_posted:
                            await say(text=f"🔧 *Using {tool_name}...*", thread_ts=thread_ts)
                            await asyncio.sleep(0.2)
                            last_tool_posted = tool_name
                        was_using_tools = True

            elif isinstance(message, PermissionUpdate):
                print(f"[DEBUG] Permission update: {message}", flush=True)
                # Log any permission-related messages
            elif isinstance(message, ResultMessage):
                if message.is_error:
                    await say(text=f"❌ Error: {message.result}", thread_ts=thread_ts)
                else:
                    duration_sec = message.duration_ms / 1000 if message.duration_ms else 0
                    await say(text=f"✅ Complete ({duration_sec:.1f}s)", thread_ts=thread_ts)

    except Exception as e:
        error_msg = str(e)
        await say(text=f"❌ Failed: {error_msg}", thread_ts=thread_ts)
        print(f"[ERROR] Exception type: {type(e).__name__}", flush=True)
        print(f"[ERROR] Exception message: {error_msg}", flush=True)
        import traceback
        traceback.print_exc()
        # Print more context
        print(f"[ERROR] Query was: {query_text}", flush=True)


@app.event("app_mention")
async def handle_mention(event, say, client):
    """Handle @mentions in Slack channels."""
    print(f"[DEBUG] Received app_mention event", flush=True)

    thread_ts = event.get("thread_ts", event["ts"])
    text = event.get("text", "")

    # Remove the bot mention from the text
    query_text = re.sub(r"<@[A-Z0-9]+>\s*", "", text).strip()
    print(f"[DEBUG] Query: {query_text}", flush=True)

    if not query_text:
        await say(
            text="👋 I'm the Retail Cash Logistics bot! Mention me with a query.\n\nExamples:\n• `@Retail Cash alert on all missed deposits`\n• `@Retail Cash analyze deposit patterns`",
            thread_ts=thread_ts
        )
        return

    # Acknowledge the request
    await say(text="🔍 *Analyzing...*", thread_ts=thread_ts)

    # Run query as background task so handler returns quickly
    asyncio.create_task(process_query(query_text, thread_ts, say))


@app.event("message")
async def handle_message(event, say):
    """Handle direct messages to the bot."""
    # Only respond to DMs
    if not event.get("channel", "").startswith("D"):
        return

    # Ignore bot messages
    if event.get("bot_id"):
        return

    text = event.get("text", "").strip()
    if text:
        await handle_mention(
            {"channel": event["channel"], "ts": event["ts"], "text": text, "user": event.get("user")},
            say,
            None
        )


async def main():
    """Start the Slack bot."""
    print("=" * 50)
    print("🚛 Retail Cash Logistics Agent - Slack Bot")
    print("=" * 50)
    print("Bot is starting...")
    print("Mention @Retail Cash in #cash-logistics-alerts")
    print("Press Ctrl+C to stop")
    print("=" * 50)

    handler = AsyncSocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    await handler.start_async()


if __name__ == "__main__":
    asyncio.run(main())
