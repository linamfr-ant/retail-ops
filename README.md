# Cash Logistics Optimizer Agent

An AI-powered agent that optimizes cash logistics operations for retail businesses. Built with the Claude Agent SDK and MCP (Model Context Protocol) for seamless integration with databases, Slack, and file systems.

## What It Does

The Cash Logistics Optimizer helps retail operations teams:

- **Analyze deposit patterns** - Identify volume trends by store, day-of-week, and season
- **Optimize pickup schedules** - Find over-serviced stores (wasting money) and under-serviced stores (creating risk)
- **Recover SLA credits** - Track missed pickups and calculate credits owed by carriers
- **Monitor insurance compliance** - Alert when stores approach $25,000 cash-on-hand limits
- **Generate reports** - Create weekly summaries for stakeholders

## Quick Start

### 1. Clone and Setup

```bash
cd retail-ops
./setup.sh
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Initialize the Database

```bash
python src/setup_database.py
```

### 4. Configure Slack (Optional)

For Slack alerts, follow the [Slack Setup Guide](docs/SLACK_SETUP.md), then:

```bash
cp .env.example .env
# Edit .env with your Slack token
python scripts/test_slack.py
```

### 5. Run the Demo

```bash
# Interactive mode
python src/demo_runner.py

# Scripted demo with 3 scenarios
python src/demo_runner.py --scripted
```

## Project Structure

```
retail-ops/
├── config/
│   └── mcp_config.json      # MCP server configuration
├── data/
│   └── cash_logistics.db    # SQLite database (generated)
├── docs/
│   └── SLACK_SETUP.md       # Slack integration guide
├── reports/                 # Generated reports
├── scripts/
│   └── test_slack.py        # Slack connection tester
├── src/
│   ├── agent.py             # Main agent implementation
│   ├── demo_runner.py       # Demo/presentation runner
│   └── setup_database.py    # Database initialization
├── .env.example             # Environment template
├── .gitignore
├── README.md
├── requirements.txt
└── setup.sh                 # Setup validation script
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Cash Logistics Agent                      │
│                   (Claude Agent SDK)                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
          ┌───────────┼───────────┐
          │           │           │
          ▼           ▼           ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │  SQLite  │ │  Slack   │ │Filesystem│
    │   MCP    │ │   MCP    │ │   MCP    │
    └────┬─────┘ └────┬─────┘ └────┬─────┘
         │            │            │
         ▼            ▼            ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │ Database │ │ #alerts  │ │ /reports │
    │   .db    │ │ channel  │ │   /*.md  │
    └──────────┘ └──────────┘ └──────────┘
```

## MCP Servers

| Server | Purpose | Package |
|--------|---------|---------|
| SQLite | Query cash_logistics.db | `mcp-server-sqlite-npx` |
| Slack | Send alerts | `@mkusaka/mcp-server-slack-notify` |
| Filesystem | Write reports | `@modelcontextprotocol/server-filesystem` |

## Database Schema

### stores
| Column | Type | Description |
|--------|------|-------------|
| store_id | TEXT | Primary key (e.g., "342") |
| name | TEXT | Store name |
| region | TEXT | North/South/East/West |
| current_pickup_frequency | INT | Pickups per week (1-5) |
| avg_daily_deposit | REAL | Average daily cash deposit |
| smart_safe_enabled | BOOL | Has smart safe technology |

### deposits
| Column | Type | Description |
|--------|------|-------------|
| store_id | TEXT | Foreign key to stores |
| deposit_date | DATE | Date of deposit |
| amount | REAL | Deposit amount |
| deposit_time | TIME | Time of deposit |

### scheduled_pickups
| Column | Type | Description |
|--------|------|-------------|
| store_id | TEXT | Foreign key to stores |
| scheduled_date | DATE | Scheduled pickup date |
| scheduled_time | TIME | Scheduled time |
| actual_time | TIME | Actual pickup time (null if missed) |
| status | TEXT | 'completed', 'missed', or 'late' |

### carrier_invoices
| Column | Type | Description |
|--------|------|-------------|
| month | TEXT | Month (YYYY-MM) |
| total_stops | INT | Number of pickup stops |
| cost_per_stop | REAL | Cost per stop |
| total_amount | REAL | Monthly invoice total |

## Sample Data Scenarios

The demo database includes specific scenarios for testing:

| Store | Scenario | Details |
|-------|----------|---------|
| #342 | Over-serviced | $1,800/day but 5x weekly pickup (waste) |
| #127 | Under-serviced | $8,200/day but only 2x weekly (risk) |
| #089 | Optimal | $4,500/day with 3x weekly (balanced) |

Plus:
- 50 stores across 4 regions
- 90 days of deposit history
- 7 missed pickups in Q4
- Weekend deposits 40% higher than weekday

## CLI Commands

### Interactive Mode

```bash
python src/agent.py
```

Commands:
- `patterns` - Analyze deposit patterns
- `mismatches` - Find schedule optimization opportunities
- `missed` - Detect missed pickups and SLA credits
- `risk` - Check insurance compliance
- `report` - Generate weekly report
- `help` - Show commands
- `quit` - Exit

### Demo Runner

```bash
# Interactive with rich UI
python src/demo_runner.py

# Auto-run all scenarios
python src/demo_runner.py --scripted

# Run specific scenario
python src/demo_runner.py --scenario 2
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SLACK_BOT_TOKEN` | For Slack | Bot OAuth token (xoxb-...) |
| `SLACK_DEFAULT_CHANNEL` | No | Default alert channel |

## Industry Terminology

- **CIT** - Cash-in-Transit (armored carrier services)
- **Smart Safe** - Electronic safe with counting/validation and provisional credit
- **Float Cost** - Opportunity cost of idle cash
- **Till Skim** - Removing excess cash from registers
- **SLA** - Service Level Agreement (pickup guarantees)

## Troubleshooting

### MCP servers won't start

```bash
# Verify Node.js is installed
node --version
npx --version

# Run setup validation
./setup.sh
```

### Database not found

```bash
python src/setup_database.py
```

### Slack not working

```bash
python scripts/test_slack.py
```

See [docs/SLACK_SETUP.md](docs/SLACK_SETUP.md) for detailed Slack configuration.

## Requirements

- Python 3.11+
- Node.js 18+ (for MCP servers)
- Claude Agent SDK
- Slack workspace (optional, for alerts)

## License

Internal demo - not for distribution.
