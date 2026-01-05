#!/usr/bin/env python3
"""
Cash Logistics Optimizer Agent - Demo Runner

A demonstration script that showcases the agent's capabilities through
guided scenarios or interactive exploration.

Usage:
    python demo_runner.py              # Interactive mode
    python demo_runner.py --scripted   # Auto-run demo scenarios
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt
from rich.rule import Rule
from rich.table import Table
from rich.theme import Theme
from rich import box

# Custom theme
custom_theme = Theme({
    "info": "cyan",
    "success": "green",
    "warning": "yellow",
    "error": "red bold",
    "highlight": "magenta",
})

console = Console(theme=custom_theme)

# ASCII Art Banner
BANNER = r"""
[cyan]
   ██████╗ █████╗ ███████╗██╗  ██╗███████╗██╗      ██████╗ ██╗    ██╗
  ██╔════╝██╔══██╗██╔════╝██║  ██║██╔════╝██║     ██╔═══██╗██║    ██║
  ██║     ███████║███████╗███████║█████╗  ██║     ██║   ██║██║ █╗ ██║
  ██║     ██╔══██║╚════██║██╔══██║██╔══╝  ██║     ██║   ██║██║███╗██║
  ╚██████╗██║  ██║███████║██║  ██║██║     ███████╗╚██████╔╝╚███╔███╔╝
   ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝     ╚══════╝ ╚═════╝  ╚══╝╚══╝
[/cyan]
[white]              ██████╗ ██████╗ ████████╗██╗███╗   ███╗██╗███████╗███████╗██████╗
             ██╔═══██╗██╔══██╗╚══██╔══╝██║████╗ ████║██║╚══███╔╝██╔════╝██╔══██╗
             ██║   ██║██████╔╝   ██║   ██║██╔████╔██║██║  ███╔╝ █████╗  ██████╔╝
             ██║   ██║██╔═══╝    ██║   ██║██║╚██╔╝██║██║ ███╔╝  ██╔══╝  ██╔══██╗
             ╚██████╔╝██║        ██║   ██║██║ ╚═╝ ██║██║███████╗███████╗██║  ██║
              ╚═════╝ ╚═╝        ╚═╝   ╚═╝╚═╝     ╚═╝╚═╝╚══════╝╚══════╝╚═╝  ╚═╝[/white]
[dim]                        Powered by Claude Agent SDK + MCP[/dim]
"""

# Demo Scenarios
SCENARIOS = [
    {
        "id": 1,
        "title": "Deposit Pattern Analysis & Schedule Optimization",
        "description": "Analyze deposit patterns to find stores where pickup frequency doesn't match actual cash volume. This reveals cost-saving opportunities.",
        "prompt": "Analyze deposit patterns across all stores for Q4. Identify stores where pickup frequency doesn't match deposit volume. Show me the top 5 optimization opportunities.",
        "expected": [
            "Query deposits grouped by store",
            "Compare avg daily deposits to pickup frequency",
            "Identify over-serviced stores (high freq, low volume)",
            "Identify under-serviced stores (low freq, high volume)",
            "Calculate potential monthly savings",
        ],
    },
    {
        "id": 2,
        "title": "Missed Pickup Analysis & SLA Credit Recovery",
        "description": "Find missed pickups and calculate credits owed by the carrier per our Service Level Agreement.",
        "prompt": "Find all missed pickups in Q4 and calculate the credits we should recover from our carrier per our SLA.",
        "expected": [
            "Query scheduled_pickups where status='missed'",
            "Find 7 missed pickups in Q4",
            "Calculate SLA credits at $150 per missed pickup",
            "Total credit recovery: $1,050",
            "List affected stores and dates",
        ],
    },
    {
        "id": 3,
        "title": "Insurance Risk Alert",
        "description": "Send an urgent alert about a store approaching insurance limits for cash-on-hand.",
        "prompt": "Alert the #cash-logistics-alerts channel about Store #127's risk status—their cash-on-hand is approaching insurance limits.",
        "expected": [
            "Query Store #127's deposit data",
            "Calculate cumulative cash between pickups",
            "Identify risk: $8,200/day × 3-4 days between pickups",
            "Send Slack alert via MCP",
            "Recommend immediate action",
        ],
    },
]


class DemoRunner:
    """Runs the Cash Logistics Optimizer demo."""

    def __init__(self, scripted: bool = False):
        self.scripted = scripted
        self.agent = None

    async def initialize_agent(self):
        """Initialize the Cash Logistics Agent with MCP servers."""
        console.print()
        console.print(Rule("[bold cyan]Initializing Agent[/bold cyan]"))
        console.print()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Loading MCP configuration...", total=None)

            try:
                from agent import CashLogisticsAgent

                self.agent = CashLogisticsAgent()

                progress.update(task, description="Starting MCP servers...")
                await self.agent.initialize()

                progress.update(task, description="Agent ready!")
                await asyncio.sleep(0.5)

            except ImportError as e:
                progress.stop()
                console.print(f"[error]Import error: {e}[/error]")
                console.print("[dim]Make sure claude-agent-sdk is installed:[/dim]")
                console.print("  pip install -r requirements.txt")
                return False

            except FileNotFoundError as e:
                progress.stop()
                console.print(f"[error]Configuration error: {e}[/error]")
                console.print("[dim]Run setup.sh to create required files[/dim]")
                return False

            except Exception as e:
                progress.stop()
                console.print(f"[error]Failed to initialize agent: {e}[/error]")
                self._show_troubleshooting()
                return False

        console.print()
        self._show_mcp_status()
        return True

    def _show_mcp_status(self):
        """Display MCP server connection status."""
        table = Table(title="MCP Server Status", box=box.ROUNDED)
        table.add_column("Server", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Purpose")

        table.add_row("sqlite", "● Connected", "Query cash_logistics.db")
        table.add_row("slack", "● Connected", "Send alerts to #cash-logistics-alerts")
        table.add_row("filesystem", "● Connected", "Write reports to ./reports/")

        console.print(table)
        console.print()

    def _show_troubleshooting(self):
        """Show troubleshooting tips for common errors."""
        console.print()
        console.print(Panel(
            "[yellow]Troubleshooting Tips:[/yellow]\n\n"
            "1. [dim]Ensure Node.js and npx are installed[/dim]\n"
            "   Run: ./setup.sh\n\n"
            "2. [dim]Check that the database exists[/dim]\n"
            "   Run: python src/setup_database.py\n\n"
            "3. [dim]For Slack integration, set environment variables[/dim]\n"
            "   Copy .env.example to .env and configure\n\n"
            "4. [dim]Install Python dependencies[/dim]\n"
            "   Run: pip install -r requirements.txt",
            title="[red]Connection Failed[/red]",
            border_style="red",
        ))

    async def run_prompt(self, prompt: str) -> tuple[str, float]:
        """Run a prompt through the agent and return response with timing."""
        start_time = time.time()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            _ = progress.add_task("Agent is analyzing...", total=None)

            try:
                response = await self.agent.chat(prompt)  # type: ignore[union-attr]
                elapsed = time.time() - start_time
                return response, elapsed

            except Exception as e:
                elapsed = time.time() - start_time
                return f"[Error: {e}]", elapsed

    def show_banner(self):
        """Display the ASCII art banner."""
        console.print(BANNER)
        console.print()

    def show_scenario_header(self, scenario: dict):
        """Display a scenario header with description."""
        console.print()
        console.print(Rule(f"[bold magenta]SCENARIO {scenario['id']}[/bold magenta]"))
        console.print()

        console.print(Panel(
            f"[bold]{scenario['title']}[/bold]\n\n"
            f"[dim]{scenario['description']}[/dim]",
            border_style="magenta",
        ))
        console.print()

        # Show expected actions
        console.print("[dim]Expected agent actions:[/dim]")
        for item in scenario["expected"]:
            console.print(f"  [dim]→ {item}[/dim]")
        console.print()

    def show_prompt(self, prompt: str):
        """Display the prompt being sent to the agent."""
        console.print(Panel(
            f"[white]{prompt}[/white]",
            title="[cyan]User Prompt[/cyan]",
            border_style="cyan",
        ))
        console.print()

    def show_response(self, response: str, elapsed: float):
        """Display the agent's response with timing."""
        # Render as markdown for better formatting
        md = Markdown(response)

        console.print(Panel(
            md,
            title=f"[green]Agent Response[/green] [dim]({elapsed:.1f}s)[/dim]",
            border_style="green",
            padding=(1, 2),
        ))

    def wait_for_continue(self):
        """Pause and wait for user to press Enter."""
        console.print()
        Prompt.ask("[dim]Press Enter to continue[/dim]", default="")

    async def run_scripted_demo(self):
        """Run the pre-defined demo scenarios automatically."""
        console.print()
        console.print(Panel(
            "[bold]Scripted Demo Mode[/bold]\n\n"
            "This demo will run through 3 scenarios showcasing the\n"
            "Cash Logistics Optimizer's key capabilities.\n\n"
            "[dim]Press Enter between scenarios to continue.[/dim]",
            border_style="blue",
        ))

        self.wait_for_continue()

        for scenario in SCENARIOS:
            self.show_scenario_header(scenario)
            self.show_prompt(scenario["prompt"])

            response, elapsed = await self.run_prompt(scenario["prompt"])
            self.show_response(response, elapsed)

            if scenario["id"] < len(SCENARIOS):
                self.wait_for_continue()

        # Final summary
        console.print()
        console.print(Rule("[bold green]Demo Complete[/bold green]"))
        console.print()

        summary_table = Table(title="Demo Summary", box=box.ROUNDED)
        summary_table.add_column("Scenario", style="cyan")
        summary_table.add_column("Capability Demonstrated")

        summary_table.add_row("1", "Deposit analysis & schedule optimization")
        summary_table.add_row("2", "SLA compliance & credit recovery")
        summary_table.add_row("3", "Risk alerting via Slack")

        console.print(summary_table)
        console.print()
        console.print("[dim]The agent used MCP servers to query SQLite, send Slack alerts, and could write reports to the filesystem.[/dim]")
        console.print()

    async def run_interactive_mode(self):
        """Run in interactive mode for manual exploration."""
        console.print()
        console.print(Panel(
            "[bold]Interactive Mode[/bold]\n\n"
            "Ask the Cash Logistics Optimizer anything about your cash operations.\n\n"
            "[dim]Commands:[/dim]\n"
            "  [cyan]scenario 1|2|3[/cyan] - Run a specific demo scenario\n"
            "  [cyan]help[/cyan]          - Show example prompts\n"
            "  [cyan]quit[/cyan]          - Exit the demo\n\n"
            "[dim]Or just type a natural language question![/dim]",
            border_style="blue",
        ))
        console.print()

        example_prompts = [
            "Which stores are over-serviced and costing us unnecessary pickup fees?",
            "Show me the deposit trends for Store #127 over the past 30 days.",
            "Generate a weekly cash logistics report.",
            "What's our total CIT cost for Q4?",
            "Find stores without smart safes that have high deposit volumes.",
        ]

        while True:
            try:
                user_input = Prompt.ask("\n[bold cyan]>[/bold cyan]")

                if not user_input.strip():
                    continue

                lower_input = user_input.lower().strip()

                if lower_input == "quit":
                    console.print("[dim]Goodbye![/dim]")
                    break

                if lower_input == "help":
                    console.print("\n[bold]Example prompts you can try:[/bold]")
                    for i, prompt in enumerate(example_prompts, 1):
                        console.print(f"  [dim]{i}.[/dim] {prompt}")
                    continue

                if lower_input.startswith("scenario "):
                    try:
                        scenario_num = int(lower_input.split()[1])
                        if 1 <= scenario_num <= len(SCENARIOS):
                            scenario = SCENARIOS[scenario_num - 1]
                            self.show_scenario_header(scenario)
                            self.show_prompt(scenario["prompt"])
                            response, elapsed = await self.run_prompt(scenario["prompt"])
                            self.show_response(response, elapsed)
                        else:
                            console.print(f"[warning]Invalid scenario. Choose 1-{len(SCENARIOS)}[/warning]")
                        continue
                    except (ValueError, IndexError):
                        console.print("[warning]Usage: scenario 1|2|3[/warning]")
                        continue

                # Regular prompt
                console.print()
                response, elapsed = await self.run_prompt(user_input)
                self.show_response(response, elapsed)

            except KeyboardInterrupt:
                console.print("\n[dim]Use 'quit' to exit[/dim]")
                continue

    async def run(self):
        """Main entry point for the demo."""
        self.show_banner()

        # Show mode info
        mode = "Scripted" if self.scripted else "Interactive"
        console.print(f"[dim]Mode: {mode}[/dim]")
        console.print()

        # Initialize agent
        if not await self.initialize_agent():
            return 1

        try:
            if self.scripted:
                await self.run_scripted_demo()
            else:
                await self.run_interactive_mode()
        finally:
            if self.agent:
                console.print("[dim]Shutting down MCP servers...[/dim]")
                await self.agent.shutdown()

        return 0

    async def cleanup(self):
        """Clean up resources."""
        if self.agent:
            await self.agent.shutdown()


def main():
    """Parse arguments and run the demo."""
    parser = argparse.ArgumentParser(
        description="Cash Logistics Optimizer Agent Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python demo_runner.py              # Interactive mode
  python demo_runner.py --scripted   # Run pre-defined scenarios

Demo Scenarios:
  1. Deposit Pattern Analysis - Find schedule optimization opportunities
  2. Missed Pickup Analysis - Calculate SLA credit recovery
  3. Risk Alert - Send Slack notification for insurance limit warning
        """,
    )

    parser.add_argument(
        "--scripted",
        action="store_true",
        help="Run pre-defined demo scenarios automatically",
    )

    parser.add_argument(
        "--scenario",
        type=int,
        choices=[1, 2, 3],
        help="Run a specific scenario only (implies --scripted)",
    )

    args = parser.parse_args()

    # If specific scenario requested, filter to just that one
    if args.scenario:
        global SCENARIOS
        SCENARIOS = [s for s in SCENARIOS if s["id"] == args.scenario]
        args.scripted = True

    runner = DemoRunner(scripted=args.scripted)

    try:
        exit_code = asyncio.run(runner.run())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        console.print("\n[dim]Demo interrupted[/dim]")
        sys.exit(0)


if __name__ == "__main__":
    main()
