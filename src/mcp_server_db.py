#!/usr/bin/env python3
"""
SQLite MCP Server for Retail Cash Logistics

A subprocess-based MCP server that provides SQLite database access.
This avoids issues with uvx/npx spawning and provides reliable database connectivity.
"""

import json
import sqlite3
import sys
import time
import os
import urllib.request
import urllib.error
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent.parent / "data" / "logistics.db"

# Validate database exists on startup
if not DB_PATH.exists():
    sys.stderr.write(f"ERROR: Database not found at {DB_PATH}\n")
    sys.stderr.flush()


def get_connection(retries=3, delay=0.5):
    """Get a database connection with retry logic."""
    last_error = None
    for attempt in range(retries):
        try:
            conn = sqlite3.connect(str(DB_PATH), timeout=10)
            conn.execute("SELECT 1")  # Test connection
            return conn
        except sqlite3.Error as e:
            last_error = e
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))  # Exponential backoff
    raise sqlite3.Error(f"Failed to connect after {retries} attempts: {last_error}")


def list_tables():
    """List all tables in the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tables


def describe_table(table_name: str):
    """Get schema for a specific table."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    conn.close()
    return [{"name": col[1], "type": col[2], "notnull": col[3], "pk": col[5]} for col in columns]


def read_query(query: str):
    """Execute a SELECT query and return results."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        columns = [description[0] for description in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        conn.close()
        return {"columns": columns, "rows": rows}
    except Exception as e:
        conn.close()
        raise e


def write_query(query: str):
    """Execute an INSERT/UPDATE/DELETE query."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return {"affected_rows": affected}
    except Exception as e:
        conn.rollback()
        conn.close()
        raise e


def read_thread(channel: str, thread_ts: str, limit: int = 10):
    """
    Read messages from a Slack thread to get conversation context.
    """
    # Log to file since stderr may not be visible
    with open("/tmp/mcp_debug.log", "a") as f:
        f.write(f"read_thread called: channel={channel}, thread_ts={thread_ts}\n")

    slack_token = os.environ.get("SLACK_BOT_TOKEN")
    if not slack_token:
        with open("/tmp/mcp_debug.log", "a") as f:
            f.write("ERROR: SLACK_BOT_TOKEN not configured\n")
        return {"success": False, "error": "SLACK_BOT_TOKEN not configured"}

    try:
        url = f"https://slack.com/api/conversations.replies?channel={channel}&ts={thread_ts}&limit={limit}"
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {slack_token}"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            with open("/tmp/mcp_debug.log", "a") as f:
                f.write(f"Slack API response ok={result.get('ok')}, error={result.get('error')}\n")
            if result.get("ok"):
                messages = []
                for msg in result.get("messages", []):
                    # Skip bot status messages like "Analyzing...", "Using tool..."
                    text = msg.get("text", "")
                    if text.startswith(("🔍", "🔧", "🧠", "🔄", "✅ Complete")):
                        continue
                    role = "assistant" if msg.get("bot_id") else "user"
                    messages.append({"role": role, "text": text})
                with open("/tmp/mcp_debug.log", "a") as f:
                    f.write(f"Returning {len(messages)} messages\n")
                return {"success": True, "messages": messages}
            else:
                return {"success": False, "error": result.get("error", "Unknown error")}
    except urllib.error.URLError as e:
        with open("/tmp/mcp_debug.log", "a") as f:
            f.write(f"URLError: {e}\n")
        return {"success": False, "error": str(e)}


def send_slack_message(channel: str, message: str):
    """
    Send a message to a Slack channel. Only use after user approves.
    """
    slack_token = os.environ.get("SLACK_BOT_TOKEN")
    if not slack_token:
        return {"success": False, "error": "SLACK_BOT_TOKEN not configured"}

    try:
        data = json.dumps({"channel": channel, "text": message}).encode("utf-8")
        req = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=data,
            headers={
                "Authorization": f"Bearer {slack_token}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            if result.get("ok"):
                return {"success": True, "channel": channel}
            else:
                return {"success": False, "error": result.get("error", "Unknown error")}
    except urllib.error.URLError as e:
        return {"success": False, "error": str(e)}


# MCP Protocol Implementation
def handle_request(request):
    """Handle a JSON-RPC request."""
    method = request.get("method")
    params = request.get("params", {})
    request_id = request.get("id")

    try:
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "sqlite-mcp", "version": "1.0.0"},
                },
            }
        elif method == "notifications/initialized":
            return None  # No response needed for notifications
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": "list_tables",
                            "description": "List all tables in the SQLite database",
                            "inputSchema": {"type": "object", "properties": {}},
                        },
                        {
                            "name": "describe_table",
                            "description": "Get the schema of a specific table",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "table_name": {"type": "string", "description": "Name of the table"}
                                },
                                "required": ["table_name"],
                            },
                        },
                        {
                            "name": "read_query",
                            "description": "Execute a SELECT query on the SQLite database",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string", "description": "SQL SELECT query to execute"}
                                },
                                "required": ["query"],
                            },
                        },
                        {
                            "name": "write_query",
                            "description": "Execute an INSERT, UPDATE, or DELETE query",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string", "description": "SQL query to execute"}
                                },
                                "required": ["query"],
                            },
                        },
                        {
                            "name": "read_thread",
                            "description": "Read messages from the current Slack thread to get conversation context. Use this when responding to short replies like 'yes', 'approved', 'no' to understand what was previously discussed.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "channel": {
                                        "type": "string",
                                        "description": "Channel ID (provided in context)"
                                    },
                                    "thread_ts": {
                                        "type": "string",
                                        "description": "Thread timestamp (provided in context)"
                                    },
                                    "limit": {
                                        "type": "integer",
                                        "description": "Max messages to fetch (default 10)",
                                        "default": 10
                                    }
                                },
                                "required": ["channel", "thread_ts"],
                            },
                        },
                        {
                            "name": "send_slack_message",
                            "description": "Send a message to a Slack channel. IMPORTANT: Only use this AFTER the user explicitly approves in the thread.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "channel": {
                                        "type": "string",
                                        "description": "Channel name (e.g., '#ops-alerts') or channel ID"
                                    },
                                    "message": {
                                        "type": "string",
                                        "description": "Message content to send"
                                    }
                                },
                                "required": ["channel", "message"],
                            },
                        },
                    ]
                },
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})

            if tool_name == "list_tables":
                result = list_tables()
                content = f"Tables in database:\n" + "\n".join(f"- {t}" for t in result)
            elif tool_name == "describe_table":
                result = describe_table(tool_args["table_name"])
                content = f"Schema for {tool_args['table_name']}:\n"
                content += "\n".join(f"- {col['name']} ({col['type']})" for col in result)
            elif tool_name == "read_query":
                result = read_query(tool_args["query"])
                if result["rows"]:
                    content = f"Columns: {', '.join(result['columns'])}\n\n"
                    content += f"Results ({len(result['rows'])} rows):\n"
                    for row in result["rows"][:100]:  # Limit to 100 rows
                        content += str(row) + "\n"
                    if len(result["rows"]) > 100:
                        content += f"\n... and {len(result['rows']) - 100} more rows"
                else:
                    content = "Query returned no results."
            elif tool_name == "write_query":
                result = write_query(tool_args["query"])
                content = f"Query executed. Affected rows: {result['affected_rows']}"
            elif tool_name == "read_thread":
                sys.stderr.write(f"[MCP] read_thread called with channel={tool_args.get('channel')}, thread_ts={tool_args.get('thread_ts')}\n")
                sys.stderr.flush()
                result = read_thread(
                    tool_args["channel"],
                    tool_args["thread_ts"],
                    tool_args.get("limit", 10)
                )
                sys.stderr.write(f"[MCP] read_thread result: {result}\n")
                sys.stderr.flush()
                if result.get("success"):
                    messages = result["messages"]
                    content = "Thread conversation:\n"
                    for msg in messages:
                        role = msg["role"].upper()
                        content += f"[{role}]: {msg['text']}\n"
                else:
                    content = f"Failed to read thread: {result.get('error')}"
            elif tool_name == "send_slack_message":
                result = send_slack_message(tool_args["channel"], tool_args["message"])
                if result.get("success"):
                    content = f"Message sent to {result['channel']}"
                else:
                    content = f"Failed to send message: {result.get('error')}"
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
                }

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"content": [{"type": "text", "text": content}]},
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32000, "message": str(e)},
        }


def main():
    """Main loop - read JSON-RPC requests from stdin, write responses to stdout."""
    # Use unbuffered I/O for reliable subprocess communication
    import io
    stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', newline='\n')
    stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', newline='\n', write_through=True)

    # Replace the global send_response to use unbuffered stdout
    def send(response):
        stdout.write(json.dumps(response) + "\n")
        stdout.flush()

    sys.stderr.write(f"[MCP] SQLite server starting, DB: {DB_PATH}\n")
    sys.stderr.flush()

    try:
        while True:
            line = stdin.readline()
            if not line:  # EOF
                break
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                response = handle_request(request)
                if response:  # Some methods (notifications) don't need a response
                    send(response)
            except json.JSONDecodeError as e:
                send({
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {e}"},
                })
            except Exception as e:
                sys.stderr.write(f"[MCP] Error handling request: {e}\n")
                sys.stderr.flush()
                send({
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32000, "message": f"Internal error: {e}"},
                })
    except Exception as e:
        sys.stderr.write(f"[MCP] Fatal error: {e}\n")
        sys.stderr.flush()
    finally:
        sys.stderr.write("[MCP] Server shutting down\n")
        sys.stderr.flush()


if __name__ == "__main__":
    main()
