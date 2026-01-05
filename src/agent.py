#!/usr/bin/env python3
"""
Cash Logistics Optimization Agent

A Claude-powered agent that analyzes cash logistics operations,
identifies cost-saving opportunities, and monitors compliance.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Claude Agent SDK imports
from claude_agent_sdk import Agent, AgentConfig
from claude_agent_sdk.mcp import MCPServerConfig, MCPManager


# Load environment variables
load_dotenv()

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "mcp_config.json"
DATA_PATH = PROJECT_ROOT / "data"
REPORTS_PATH = PROJECT_ROOT / "reports"

# Constants
INSURANCE_LIMIT = 25000  # Maximum cash-on-hand before insurance risk
SLA_CREDIT_PER_MISS = 150  # Credit amount for each missed pickup


SYSTEM_PROMPT = """You are a Cash Logistics Optimization Specialist - an expert AI assistant
that helps retail operations teams optimize their cash handling processes and reduce costs.

## Your Expertise

You have deep knowledge of:
- **CIT (Cash-in-Transit)** operations and carrier management
- **Smart safe technology** and integration with armored carriers
- **Float cost optimization** - minimizing idle cash that could be earning interest
- **Till skim procedures** and deposit timing strategies
- **Insurance compliance** - monitoring cash-on-hand limits

## Available Tools

You have access to:
1. **SQLite Database** - Query the cash_logistics.db database containing:
   - `stores`: Store info, pickup frequency, smart safe status
   - `deposits`: Daily deposit records with amounts and times
   - `scheduled_pickups`: Pickup schedule and completion status
   - `carrier_invoices`: Monthly CIT costs

2. **Slack** - Send alerts to the #cash-logistics-alerts channel for:
   - Urgent insurance limit warnings
   - Missed pickup notifications
   - Weekly summary reports

3. **Filesystem** - Generate and save markdown reports to ./reports/

## Key Analysis Capabilities

1. **Deposit Pattern Analysis**
   - Analyze deposits by store, day-of-week, and time
   - Identify weekend vs weekday volume differences
   - Flag unusual deposit patterns

2. **Schedule Optimization**
   - Find stores with mismatched pickup frequency vs deposit volume
   - Identify over-serviced stores (high frequency, low volume) = cost waste
   - Identify under-serviced stores (low frequency, high volume) = float cost + risk

3. **Missed Pickup Detection**
   - Track pickups with status='missed'
   - Calculate SLA credits owed ($150 per missed pickup)
   - Identify carriers with poor performance

4. **Insurance Risk Monitoring**
   - Calculate cumulative undeposited cash between pickups
   - Flag stores approaching $25,000 cash-on-hand limit
   - Recommend emergency pickups when needed

## Industry Terminology

- **CIT**: Cash-in-Transit - armored carrier services
- **Smart Safe**: Electronic safe that counts/validates cash and provisionally credits accounts
- **Float Cost**: Opportunity cost of cash sitting idle instead of being deposited
- **Till Skim**: Process of removing excess cash from registers
- **Provisional Credit**: Early credit for smart safe deposits before physical pickup
- **SLA**: Service Level Agreement - contractual pickup guarantees

## Response Guidelines

- Use specific numbers and percentages when analyzing data
- Recommend concrete actions with estimated savings
- Prioritize findings by financial impact
- Use tables for comparing multiple stores
- Always explain the "why" behind recommendations

When asked to analyze or investigate, query the database to get real data.
When issues are urgent (insurance limits, multiple missed pickups), send Slack alerts.
Generate reports in markdown format for sharing with stakeholders.
"""


def load_mcp_config() -> dict:
    """Load MCP server configuration from JSON file."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"MCP config not found: {CONFIG_PATH}")

    with open(CONFIG_PATH) as f:
        config = json.load(f)

    # Resolve relative paths to absolute
    # Update SQLite path
    if "sqlite" in config.get("mcpServers", {}):
        args = config["mcpServers"]["sqlite"]["args"]
        for i, arg in enumerate(args):
            if arg.startswith("./"):
                args[i] = str(PROJECT_ROOT / arg[2:])

    # Update filesystem paths
    if "filesystem" in config.get("mcpServers", {}):
        args = config["mcpServers"]["filesystem"]["args"]
        for i, arg in enumerate(args):
            if arg.startswith("./"):
                args[i] = str(PROJECT_ROOT / arg[2:])

    # Substitute environment variables in slack config
    if "slack" in config.get("mcpServers", {}):
        env = config["mcpServers"]["slack"].get("env", {})
        for key, value in env.items():
            if isinstance(value, str) and value.startswith("${"):
                # Extract env var name and default
                var_expr = value[2:-1]  # Remove ${ and }
                if ":-" in var_expr:
                    var_name, default = var_expr.split(":-", 1)
                else:
                    var_name, default = var_expr, ""
                env[key] = os.environ.get(var_name, default)

    return config


def build_mcp_servers(config: dict) -> list[MCPServerConfig]:
    """Build MCP server configurations from loaded config."""
    servers = []

    for name, server_config in config.get("mcpServers", {}).items():
        mcp_config = MCPServerConfig(
            name=name,
            command=server_config["command"],
            args=server_config.get("args", []),
            env=server_config.get("env", {}),
        )
        servers.append(mcp_config)

    return servers


class CashLogisticsAgent:
    """Cash Logistics Optimization Agent powered by Claude."""

    def __init__(self):
        self.agent: Optional[Agent] = None
        self.mcp_manager: Optional[MCPManager] = None
        self._config = None

    async def initialize(self):
        """Initialize the agent with MCP servers."""
        print("Initializing Cash Logistics Agent...")

        # Load configuration
        self._config = load_mcp_config()
        mcp_servers = build_mcp_servers(self._config)

        # Create MCP manager and start servers
        self.mcp_manager = MCPManager(servers=mcp_servers)
        await self.mcp_manager.start()
        print(f"  Started {len(mcp_servers)} MCP server(s)")

        # Create agent configuration
        agent_config = AgentConfig(
            model="claude-sonnet-4-20250514",
            system_prompt=SYSTEM_PROMPT,
            max_tokens=4096,
            mcp_manager=self.mcp_manager,
        )

        # Initialize the agent
        self.agent = Agent(config=agent_config)
        print("  Agent initialized")

        return self

    async def shutdown(self):
        """Clean up resources."""
        if self.mcp_manager:
            await self.mcp_manager.stop()
            print("MCP servers stopped")

    async def chat(self, message: str) -> str:
        """Send a message to the agent and get a response."""
        if not self.agent:
            raise RuntimeError("Agent not initialized. Call initialize() first.")

        response = await self.agent.chat(message)
        return response.content

    async def analyze_deposit_patterns(self) -> str:
        """Analyze deposit patterns across all stores."""
        query = """Analyze the deposit patterns in our database:
        1. Query deposits grouped by store and day of week
        2. Calculate average deposits for weekdays vs weekends
        3. Identify the top 5 highest-volume stores
        4. Note any unusual patterns or outliers

        Provide a summary with specific numbers."""
        return await self.chat(query)

    async def find_schedule_mismatches(self) -> str:
        """Find stores with mismatched pickup frequency vs deposit volume."""
        query = f"""Analyze pickup frequency vs deposit volume to find mismatches:

        1. Query all stores with their avg_daily_deposit and current_pickup_frequency
        2. Calculate what the OPTIMAL frequency should be based on:
           - Low volume (<$3,000/day): 1-2x per week
           - Medium volume ($3,000-$5,500/day): 3x per week
           - High volume (>$5,500/day): 4-5x per week

        3. Identify:
           - OVER-SERVICED stores: paying for more pickups than needed (cost waste)
           - UNDER-SERVICED stores: not enough pickups (float cost + insurance risk)

        4. Calculate potential monthly savings for over-serviced stores
           (assume $20 per pickup stop)

        Pay special attention to stores #342, #127, and #089.
        Format as a table and provide recommendations."""
        return await self.chat(query)

    async def detect_missed_pickups(self) -> str:
        """Detect missed pickups and calculate SLA credits."""
        query = f"""Find all missed pickups and calculate SLA credits:

        1. Query scheduled_pickups where status = 'missed'
        2. Join with store information
        3. Calculate total SLA credits owed at ${SLA_CREDIT_PER_MISS} per missed pickup
        4. Group by month to show trends
        5. Identify if any stores have multiple missed pickups (carrier reliability issue)

        If there are missed pickups, this is actionable - we should file for credits."""
        return await self.chat(query)

    async def check_insurance_risk(self) -> str:
        """Check for stores approaching insurance cash-on-hand limits."""
        query = f"""Check for insurance compliance risks:

        The maximum cash-on-hand limit is ${INSURANCE_LIMIT:,} per store.

        1. For each store, calculate the cumulative cash between pickups
        2. Find stores where deposits accumulate above ${INSURANCE_LIMIT:,} before pickup
        3. Consider the pickup frequency and daily deposit amounts
        4. Flag any stores currently at risk

        A store with $8,000/day deposits and only 2 pickups/week could accumulate
        $24,000+ between Friday and Tuesday pickups.

        If any stores are at risk, this is URGENT - recommend immediate action."""
        return await self.chat(query)

    async def generate_weekly_report(self) -> str:
        """Generate a comprehensive weekly report."""
        query = """Generate a weekly Cash Logistics Report with these sections:

        ## 1. Executive Summary
        - Total deposits this week vs last week
        - Total pickup stops and cost
        - Any critical issues

        ## 2. Missed Pickups
        - List any missed pickups with SLA credit amounts

        ## 3. Optimization Opportunities
        - Over-serviced stores (reduce frequency)
        - Under-serviced stores (increase frequency)
        - Estimated monthly savings

        ## 4. Insurance Compliance
        - Stores approaching $25,000 limit
        - Recommended actions

        ## 5. Recommendations
        - Prioritized action items

        Save this report to the filesystem as a markdown file with today's date."""
        return await self.chat(query)


async def interactive_cli():
    """Run an interactive CLI session with the agent."""
    print("\n" + "=" * 60)
    print("  Cash Logistics Optimization Agent")
    print("  Type 'help' for available commands, 'quit' to exit")
    print("=" * 60 + "\n")

    agent = CashLogisticsAgent()

    try:
        await agent.initialize()
        print("\nReady! Ask me anything about your cash logistics operations.\n")

        # Predefined commands
        commands = {
            "help": "Show available commands",
            "patterns": "Analyze deposit patterns across stores",
            "mismatches": "Find pickup frequency mismatches",
            "missed": "Detect missed pickups and SLA credits",
            "risk": "Check insurance compliance risks",
            "report": "Generate weekly summary report",
            "quit": "Exit the agent",
        }

        while True:
            try:
                user_input = input("\n> ").strip()

                if not user_input:
                    continue

                if user_input.lower() == "quit":
                    print("Goodbye!")
                    break

                if user_input.lower() == "help":
                    print("\nAvailable commands:")
                    for cmd, desc in commands.items():
                        print(f"  {cmd:12} - {desc}")
                    print("\nOr just type any question in natural language!")
                    continue

                # Handle predefined commands
                print("\nAnalyzing...\n")

                if user_input.lower() == "patterns":
                    response = await agent.analyze_deposit_patterns()
                elif user_input.lower() == "mismatches":
                    response = await agent.find_schedule_mismatches()
                elif user_input.lower() == "missed":
                    response = await agent.detect_missed_pickups()
                elif user_input.lower() == "risk":
                    response = await agent.check_insurance_risk()
                elif user_input.lower() == "report":
                    response = await agent.generate_weekly_report()
                else:
                    # Natural language query
                    response = await agent.chat(user_input)

                print(response)

            except KeyboardInterrupt:
                print("\n\nInterrupted. Type 'quit' to exit.")
                continue
            except Exception as e:
                print(f"\nError: {e}")
                continue

    finally:
        await agent.shutdown()


async def run_single_query(query: str):
    """Run a single query and exit."""
    agent = CashLogisticsAgent()

    try:
        await agent.initialize()
        response = await agent.chat(query)
        print(response)
    finally:
        await agent.shutdown()


def main():
    """Main entry point."""
    # Ensure reports directory exists
    REPORTS_PATH.mkdir(exist_ok=True)

    if len(sys.argv) > 1:
        # Run a single query from command line
        query = " ".join(sys.argv[1:])
        asyncio.run(run_single_query(query))
    else:
        # Interactive mode
        asyncio.run(interactive_cli())


if __name__ == "__main__":
    main()
