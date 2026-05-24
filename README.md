# finops-mcp-server

A Model Context Protocol (MCP) server that connects Claude Desktop and Claude Code to the [Finance AI Ecosystem](https://github.com/Chezhira/finance-accounting-ecosystem) — a multi-agent accounting, tax, FP&A, audit, treasury, and corporate finance system.

Ask Claude to ingest financial data, trigger agent analysis, review suggestion cards, and approve or reject agent recommendations — all from natural language in Claude Desktop.

> **Agents suggest. Humans decide. Nothing posts without approval.**

---

## What it does

Instead of calling the FastAPI endpoints manually, you can ask Claude:

> *"Check if the Finance AI system is online"*
> *"Ingest this invoice text and route it to the right agent"*
> *"Show me all pending suggestions for the default tenant"*
> *"Approve suggestion abc-123"*
> *"Analyse this transaction for Tanzania tax treatment"*
> *"Run this P&L data through the FP&A agents"*
> *"What is the current USD to TZS exchange rate?"*
> *"List all open escalations"*

Claude calls the MCP tools, the tools call the Finance AI Ecosystem FastAPI backend, and results are returned directly in chat.

---

## Tools — 19 across 3 tiers

### Tier 1 — Core workflow

| Tool | Description |
|------|-------------|
| `get_health` | Check system status, DB mode, and version. Start here. |
| `get_stats` | Dashboard statistics — pending, approved, rejected, escalated counts. |
| `ingest_text` | Submit raw text for agent processing — invoices, notes, transactions. |
| `ingest_email` | Submit a raw email for agent routing and processing. |
| `get_suggestions` | List agent suggestion cards pending human review. |
| `get_suggestion` | Full detail for a single suggestion card. |
| `decide` | Approve, reject, or escalate a suggestion. The human approval gate. |

### Tier 2 — Department analysis

| Tool | Description |
|------|-------------|
| `analyze_tax` | Tanzania (TZ) or US tax analysis — CIT, VAT, WHT, LLC pass-through. Optional supervised mode adds Tax Supervisor review layer. |
| `analyze_fpa` | FP&A analysis — budgeting, forecasting, variance, scenario planning. |
| `analyze_audit` | Audit analysis — ISA compliance, internal controls, forensic, AML/FCPA flags. |
| `analyze_treasury` | Treasury analysis — cash flow, liquidity, FX exposure, investments. |
| `analyze_accounting` | Specialist accounting — cost allocation, revenue recognition, provisions. CRITICAL flags auto-escalate. |
| `analyze_universal` | Universal router — auto-classifies and routes to the correct department and agent. |

### Tier 3 — Operations

| Tool | Description |
|------|-------------|
| `list_escalations` | List escalations raised by agents requiring senior human review. |
| `approve_escalation` | Approve or reject an escalation. |
| `get_market_rates` | Live FX rates and US market benchmark rates. |
| `get_fx_rate` | Single currency pair rate (e.g. USD → TZS). |
| `list_tenants` | List all configured tenants. |
| `sync_postgres` | Trigger manual SQLite → Postgres sync after coming back online. |

---

## Prerequisites

- Finance AI Ecosystem running locally: `uvicorn api.main:app --port 8000`
- Python 3.10+
- Claude Desktop or Claude Code

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Chezhira/finops-mcp-server.git
cd finops-mcp-server
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
```

Edit `.env`:

```env
FINOPS_URL=http://localhost:8000
FINOPS_TENANT_ID=default
FINOPS_API_KEY=
FINOPS_TIMEOUT=30
```

### 4. Start the Finance AI Ecosystem first

```bash
# In the finance-accounting-ecosystem directory
uvicorn api.main:app --reload --port 8000
```

### 5. Test with MCP Inspector

```bash
npx @modelcontextprotocol/inspector python server.py
```

Opens at `http://localhost:5173`. Connect → Tools → `get_health` → Run.

---

## Connect to Claude Desktop

Edit `claude_desktop_config.json` (Settings → Developer → Edit Config):

```json
{
  "mcpServers": {
    "finops": {
      "command": "python",
      "args": ["C:\\full\\path\\to\\finops-mcp-server\\server.py"],
      "env": {
        "FINOPS_URL": "http://localhost:8000",
        "FINOPS_TENANT_ID": "default",
        "FINOPS_API_KEY": "",
        "FINOPS_TIMEOUT": "30"
      }
    }
  }
}
```

Restart Claude Desktop. The `finops` server appears under Settings → Developer → Local MCP servers.

---

## Connect to Claude Code

```bash
claude mcp add finops python /full/path/to/finops-mcp-server/server.py \
  -e FINOPS_URL=http://localhost:8000 \
  -e FINOPS_TENANT_ID=default
```

---

## Architecture

```
Claude Desktop / Claude Code
        │
        │  MCP protocol (stdio / JSON-RPC 2.0)
        ▼
  server.py  (FastMCP)
        │
        │  HTTP / REST
        ▼
  Finance AI Ecosystem  (FastAPI, port 8000)
        │
        ├── Phase4Orchestrator (Haiku L1 → Sonnet L2)
        ├── 30+ specialist agents (Accounting, Tax, FP&A, Audit, Treasury, Corp Finance)
        ├── SQLite (offline) / Postgres (online)
        └── Accounting adapters (QuickBooks, Fishbowl, BILL.com, Xero, Odoo)
```

The MCP server is a pure HTTP wrapper — it holds no state and no business logic. All intelligence lives in the Finance AI Ecosystem backend.

---

## Example prompts once connected

```
Is the Finance AI system online?

Show me all pending suggestions for the default tenant.

Ingest this text: "Received invoice from Office Supplies Ltd for TZS 450,000 dated 15 Jan 2025 for stationery."

Analyse this for Tanzania tax treatment: "We paid a non-resident consultant USD 5,000 for advisory services."

Run supervised tax analysis on: "Interest income of TZS 2,500,000 received from NMB bank savings account."

What is the current USD to TZS exchange rate?

Approve suggestion abc-123 with reason "Reviewed and confirmed correct treatment."

List all open escalations.

Trigger a Postgres sync.
```

---

## Troubleshooting

**`Cannot connect to Finance AI Ecosystem`**
- Start the backend first: `uvicorn api.main:app --port 8000`
- Confirm it's running: `curl http://localhost:8000/health`

**`HTTP 422`**
- The payload shape doesn't match the API. Check the FastAPI docs at `http://localhost:8000/docs`.

**Tools not appearing in Claude Desktop**
- Windows Store Claude uses a non-standard config path — use Settings → Developer → Edit Config to locate it.
- Fully quit and restart Claude Desktop after editing the config.

---

## Related

- [finance-accounting-ecosystem](https://github.com/Chezhira/finance-accounting-ecosystem) — the Finance AI Ecosystem backend this server wraps
- [odoo19-mcp-server](https://github.com/Chezhira/odoo19-mcp-server) — MCP server for Odoo 19 GL queries

---

## License

MIT
