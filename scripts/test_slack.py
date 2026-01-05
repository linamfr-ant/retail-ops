#!/usr/bin/env python3
"""
Slack Integration Test Script

Tests the Slack connection and sends a test message to verify
the Cash Logistics Bot is properly configured.

Usage:
    python scripts/test_slack.py
    python scripts/test_slack.py --channel "#other-channel"
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# ANSI color codes for terminal output
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    DIM = "\033[2m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def success(msg: str) -> None:
    print(f"{Colors.GREEN}✓{Colors.RESET} {msg}")


def error(msg: str) -> None:
    print(f"{Colors.RED}✗{Colors.RESET} {msg}")


def warning(msg: str) -> None:
    print(f"{Colors.YELLOW}!{Colors.RESET} {msg}")


def info(msg: str) -> None:
    print(f"{Colors.CYAN}→{Colors.RESET} {msg}")


def check_environment() -> tuple[str | None, str | None]:
    """Check that required environment variables are set."""
    print(f"\n{Colors.BOLD}Checking Environment{Colors.RESET}")
    print("=" * 40)

    token = os.environ.get("SLACK_BOT_TOKEN")
    channel = os.environ.get("SLACK_DEFAULT_CHANNEL", "#cash-logistics-alerts")

    if token:
        # Mask the token for display
        masked = token[:10] + "..." + token[-4:] if len(token) > 20 else "***"
        success(f"SLACK_BOT_TOKEN is set ({masked})")
    else:
        error("SLACK_BOT_TOKEN is not set")
        print(f"\n{Colors.DIM}To fix this:")
        print("  1. Copy .env.example to .env")
        print("  2. Add your Slack Bot Token")
        print(f"  See docs/SLACK_SETUP.md for details{Colors.RESET}")
        return None, None

    if channel:
        success(f"SLACK_DEFAULT_CHANNEL: {channel}")
    else:
        warning("SLACK_DEFAULT_CHANNEL not set, using #cash-logistics-alerts")
        channel = "#cash-logistics-alerts"

    return token, channel


def test_connection(token: str) -> dict | None:
    """Test the Slack API connection and get bot info."""
    print(f"\n{Colors.BOLD}Testing Connection{Colors.RESET}")
    print("=" * 40)

    try:
        # Test auth.test endpoint
        req = urllib.request.Request(
            "https://slack.com/api/auth.test",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())

        if data.get("ok"):
            success("Successfully connected to Slack API")
            success(f"Bot name: {data.get('user', 'Unknown')}")
            success(f"Workspace: {data.get('team', 'Unknown')}")
            return data
        else:
            error(f"API error: {data.get('error', 'Unknown error')}")
            _show_auth_error_help(data.get("error", ""))
            return None

    except urllib.error.URLError as e:
        error(f"Network error: {e}")
        print(f"\n{Colors.DIM}Check your internet connection{Colors.RESET}")
        return None
    except Exception as e:
        error(f"Connection failed: {e}")
        return None


def send_test_message(token: str, channel: str) -> bool:
    """Send a test message to the configured channel."""
    print(f"\n{Colors.BOLD}Sending Test Message{Colors.RESET}")
    print("=" * 40)

    info(f"Target channel: {channel}")

    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        message = {
            "channel": channel,
            "text": "🧪 *Cash Logistics Bot - Connection Test*",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🧪 Connection Test Successful",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            "The Cash Logistics Bot is properly configured "
                            "and can send messages to this channel.\n\n"
                            f"*Timestamp:* {timestamp}"
                        ),
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": (
                                "This is a test message from `scripts/test_slack.py`. "
                                "You can delete this message."
                            ),
                        }
                    ],
                },
            ],
        }

        req = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=json.dumps(message).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            },
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())

        if data.get("ok"):
            success("Message sent successfully!")
            print(f"\n{Colors.GREEN}Check your {channel} channel for the test message.{Colors.RESET}")
            return True
        else:
            error(f"Failed to send: {data.get('error', 'Unknown error')}")
            _show_send_error_help(data.get("error", ""), channel)
            return False

    except urllib.error.URLError as e:
        error(f"Network error: {e}")
        return False
    except Exception as e:
        error(f"Failed to send message: {e}")
        return False


def _show_auth_error_help(error_code: str) -> None:
    """Show helpful information for authentication errors."""
    help_messages = {
        "invalid_auth": (
            "Your token is invalid or expired.\n"
            "  → Go to api.slack.com/apps, select your app\n"
            "  → Navigate to OAuth & Permissions\n"
            "  → Copy the Bot User OAuth Token"
        ),
        "token_revoked": (
            "This token has been revoked.\n"
            "  → Reinstall the app to your workspace to get a new token"
        ),
        "account_inactive": (
            "The token's associated account is inactive.\n"
            "  → Check that the app is still installed in your workspace"
        ),
        "missing_scope": (
            "The token is missing required permissions.\n"
            "  → Add 'chat:write' scope in OAuth & Permissions\n"
            "  → Reinstall the app to apply new scopes"
        ),
    }

    if error_code in help_messages:
        print(f"\n{Colors.YELLOW}How to fix:{Colors.RESET}")
        print(f"{Colors.DIM}{help_messages[error_code]}{Colors.RESET}")
    else:
        print(f"\n{Colors.DIM}See docs/SLACK_SETUP.md for troubleshooting{Colors.RESET}")


def _show_send_error_help(error_code: str, channel: str) -> None:
    """Show helpful information for message sending errors."""
    help_messages = {
        "channel_not_found": (
            f"Channel '{channel}' was not found.\n"
            "  → Check the channel name is correct (include #)\n"
            "  → Verify the channel exists and isn't archived\n"
            "  → For private channels, invite the bot first"
        ),
        "not_in_channel": (
            f"The bot is not a member of {channel}.\n"
            "  → Go to the channel in Slack\n"
            "  → Type: /invite @YourBotName\n"
            "  → Or add the bot via channel settings → Integrations"
        ),
        "is_archived": (
            f"Channel '{channel}' is archived.\n"
            "  → Unarchive the channel, or\n"
            "  → Use a different channel"
        ),
        "msg_too_long": (
            "The message was too long.\n"
            "  → This shouldn't happen with test messages"
        ),
        "no_text": (
            "No message text was provided.\n"
            "  → This is a bug in the test script"
        ),
        "restricted_action": (
            "The bot doesn't have permission to post here.\n"
            "  → Check workspace settings for app restrictions\n"
            "  → Contact your Slack admin"
        ),
    }

    if error_code in help_messages:
        print(f"\n{Colors.YELLOW}How to fix:{Colors.RESET}")
        print(f"{Colors.DIM}{help_messages[error_code]}{Colors.RESET}")
    else:
        print(f"\n{Colors.DIM}Error code: {error_code}")
        print(f"See docs/SLACK_SETUP.md for troubleshooting{Colors.RESET}")


def main():
    parser = argparse.ArgumentParser(
        description="Test Slack integration for Cash Logistics Bot"
    )
    parser.add_argument(
        "--channel",
        help="Override the default channel (e.g., '#other-channel')",
    )
    parser.add_argument(
        "--no-send",
        action="store_true",
        help="Only test connection, don't send a message",
    )
    args = parser.parse_args()

    print(f"\n{Colors.BOLD}{Colors.CYAN}Slack Integration Test{Colors.RESET}")
    print("=" * 40)

    # Check environment
    token, channel = check_environment()
    if not token or not channel:
        sys.exit(1)

    # Override channel if specified
    if args.channel:
        channel = args.channel
        info(f"Using override channel: {channel}")

    # Test connection
    auth_info = test_connection(token)
    if not auth_info:
        sys.exit(1)

    # Send test message
    if not args.no_send:
        if not send_test_message(token, channel):
            sys.exit(1)
    else:
        info("Skipping message send (--no-send)")

    # Success summary
    print(f"\n{Colors.BOLD}{Colors.GREEN}All tests passed!{Colors.RESET}")
    print(f"\n{Colors.DIM}The Cash Logistics Bot is ready to send alerts.")
    print(f"Run the demo: python src/demo_runner.py --scripted{Colors.RESET}\n")


if __name__ == "__main__":
    main()
