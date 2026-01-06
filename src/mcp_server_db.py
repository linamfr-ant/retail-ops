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


# MCP Protocol Implementation
def send_response(response):
    """Send a JSON-RPC response."""
    output = json.dumps(response) + "\n"
    sys.stdout.write(output)
    sys.stdout.flush()


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
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
            if response:  # Some methods (notifications) don't need a response
                send_response(response)
        except json.JSONDecodeError as e:
            send_response({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {e}"},
            })


if __name__ == "__main__":
    main()
