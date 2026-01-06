"""
Slack bot that listens to messages and runs the logistics agent.

The bot listens in #cash-logistics-alerts channel and responds to queries.
"""

import asyncio
import os
import re
import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from agent import run_query

load_dotenv()

# Slack configuration
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")  # For Socket Mode

# Initialize Slack app
app = AsyncApp(token=SLACK_BOT_TOKEN)


@app.event("app_mention")
async def handle_mention(event, say):
    """Handle when the bot is @mentioned."""
    print(f"[DEBUG] Received app_mention event: {event}", flush=True)
    text = event.get("text", "")
    user = event.get("user")

    # Remove the bot mention from the text
    query = re.sub(r"<@[A-Z0-9]+>", "", text).strip()
    print(f"[DEBUG] Extracted query: {query}", flush=True)

    if not query:
        await say(f"<@{user}> Please provide a query. For example: `@bot analyze deposit patterns`")
        return

    # Acknowledge the request
    await say(f"Analyzing: _{query}_...")
    print(f"[DEBUG] Sent acknowledgment, running agent...", flush=True)

    # Run the agent
    try:
        result = await run_query(query)
        print(f"[DEBUG] Agent result: {result[:200] if result else 'None'}...", flush=True)
        await say(result or "No response generated.")
    except Exception as e:
        print(f"[DEBUG] Error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        await say(f"Error running analysis: {str(e)}")


@app.event("message")
async def handle_message(event, say):
    """Handle direct messages to the bot."""
    # Ignore messages from bots (including self)
    if event.get("bot_id"):
        return

    # Only respond to DMs (channel type 'im')
    if event.get("channel_type") != "im":
        return

    text = event.get("text", "")

    if not text:
        return

    # Run the agent
    try:
        result = await run_query(text)
        await say(result or "No response generated.")
    except Exception as e:
        await say(f"Error: {str(e)}")


async def main():
    """Start the Slack bot."""
    print("\n" + "=" * 60, flush=True)
    print("Armored Carrier Logistics Agent - Slack Bot", flush=True)
    print("=" * 60, flush=True)
    print(f"\nSLACK_BOT_TOKEN: {'set' if SLACK_BOT_TOKEN else 'NOT SET'}", flush=True)
    print(f"SLACK_APP_TOKEN: {'set' if SLACK_APP_TOKEN else 'NOT SET'}", flush=True)
    print("\nBot is running! Mention @bot in #cash-logistics-alerts", flush=True)
    print("or send a direct message to interact.", flush=True)
    print("\nExample queries:", flush=True)
    print("  @bot analyze deposit patterns against pickup schedules", flush=True)
    print("  @bot alert on all missed deposits", flush=True)
    print("  @bot which stores have high cash sitting risk?", flush=True)
    print("\nPress Ctrl+C to stop.\n", flush=True)

    handler = AsyncSocketModeHandler(app, SLACK_APP_TOKEN)
    await handler.start_async()


if __name__ == "__main__":
    asyncio.run(main())
