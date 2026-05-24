"""
Finance AI Ecosystem MCP Server
================================
Connects Claude Desktop / Claude Code to the Finance AI Ecosystem FastAPI
backend (github.com/Chezhira/finance-ai-pack).

All tools call the FastAPI REST API over HTTP — the MCP server is a pure
wrapper. The ecosystem must be running (uvicorn api.main:app --port 8000)
for tools to work.

Tools — 18 across 3 tiers:

Tier 1 — Core workflow
  ingest_text           → POST /ingest/text
  ingest_email          → POST /ingest/email
  get_suggestions       → GET  /suggestions/{tenant_id}
  get_suggestion        → GET  /suggestions/{tenant_id}/{id}
  decide                → POST /suggestions/{tenant_id}/{id}/decide
  get_stats             → GET  /stats/{tenant_id}
  get_health            → GET  /health

Tier 2 — Department analysis
  analyze_tax           → POST /tax/analyze
  analyze_tax_supervised→ POST /tax/analyze/supervised
  analyze_fpa           → POST /fpa/analyze
  analyze_audit         → POST /audit/analyze
  analyze_treasury      → POST /treasury/analyze
  analyze_accounting    → POST /accounting/analyze
  analyze_universal     → POST /analyze

Tier 3 — Operations
  list_escalations      → GET  /escalations
  approve_escalation    → POST /escalations/{id}/approve
  get_market_rates      → GET  /market/rates
  get_fx_rate           → GET  /market/fx/{from}/{to}
  list_tenants          → GET  /tenants
  sync_postgres         → POST /sync
"""

import os
import json
from typing import Optional

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

load_dotenv()

BASE_URL   = os.getenv("FINOPS_URL", "http://localhost:8000")
TENANT_ID  = os.getenv("FINOPS_TENANT_ID", "default")
API_KEY    = os.getenv("FINOPS_API_KEY", "")        # optional — set if auth enabled
TIMEOUT    = float(os.getenv("FINOPS_TIMEOUT", "30"))

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _headers() -> dict:
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    if API_KEY:
        h["X-API-Key"] = API_KEY
    return h


def _get(path: str, params: dict = None) -> str:
    try:
        r = httpx.get(
            f"{BASE_URL}{path}",
            headers=_headers(),
            params=params,
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return _fmt_response(r.json())
    except httpx.ConnectError:
        return f"❌ Cannot connect to Finance AI Ecosystem at {BASE_URL}. Is the server running? (uvicorn api.main:app --port 8000)"
    except httpx.HTTPStatusError as e:
        return f"❌ HTTP {e.response.status_code}: {e.response.text[:400]}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


def _post(path: str, payload: dict) -> str:
    try:
        r = httpx.post(
            f"{BASE_URL}{path}",
            headers=_headers(),
            json=payload,
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return _fmt_response(r.json())
    except httpx.ConnectError:
        return f"❌ Cannot connect to Finance AI Ecosystem at {BASE_URL}. Is the server running? (uvicorn api.main:app --port 8000)"
    except httpx.HTTPStatusError as e:
        return f"❌ HTTP {e.response.status_code}: {e.response.text[:400]}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


def _fmt_response(data) -> str:
    """Pretty-print JSON response."""
    if isinstance(data, str):
        return data
    return json.dumps(data, indent=2, default=str)


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "finops",
    instructions=(
        "Tools for the Finance AI Ecosystem — a multi-agent accounting, tax, "
        "FP&A, audit, treasury, and corporate finance system. "
        "Agents suggest; humans decide. Nothing is committed without approval. "
        f"Default tenant: {TENANT_ID}. "
        "Start with get_health to confirm the system is online."
    ),
)


# ===========================================================================
# TIER 1 — Core workflow
# ===========================================================================

@mcp.tool()
def get_health() -> str:
    """
    Check whether the Finance AI Ecosystem backend is online.
    Returns system status, database mode (SQLite/Postgres), and version.
    Always call this first to confirm the server is running.
    """
    return _get("/health")


@mcp.tool()
def get_stats(tenant_id: Optional[str] = None) -> str:
    """
    Return dashboard statistics for a tenant — total suggestions, pending
    approvals, approved/rejected counts, escalations, and agent activity.

    Args:
        tenant_id: Tenant identifier. Defaults to the configured default tenant.
    """
    tid = tenant_id or TENANT_ID
    return _get(f"/stats/{tid}")


@mcp.tool()
def ingest_text(
    text: str,
    tenant_id: Optional[str] = None,
    source: Optional[str] = None,
) -> str:
    """
    Submit raw text to the Finance AI Ecosystem for processing.
    The system automatically routes it to the correct agent(s) based on content.
    Use this for invoices, journal entry descriptions, financial notes,
    transaction data, or any unstructured financial text.

    Args:
        text:       The raw text to process — invoice, data, notes, transactions.
        tenant_id:  Tenant identifier. Defaults to configured default.
        source:     Optional source label (e.g. "email", "manual", "quickbooks").

    Returns:
        Suggestion card(s) produced by the agent(s), pending human approval.
    """
    tid = tenant_id or TENANT_ID
    payload = {"text": text, "tenant_id": tid}
    if source:
        payload["source"] = source
    return _post("/ingest/text", payload)


@mcp.tool()
def ingest_email(
    subject: str,
    body: str,
    sender: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> str:
    """
    Submit a raw email to the Finance AI Ecosystem for processing.
    The system parses the email, classifies it, and routes to the correct agent.
    Useful for vendor invoices, payment confirmations, and tax notices received by email.

    Args:
        subject:    Email subject line.
        body:       Full email body text.
        sender:     Sender email address (optional).
        tenant_id:  Tenant identifier. Defaults to configured default.

    Returns:
        Suggestion card(s) produced by the routing agent.
    """
    tid = tenant_id or TENANT_ID
    payload = {
        "subject": subject,
        "body": body,
        "tenant_id": tid,
    }
    if sender:
        payload["sender"] = sender
    return _post("/ingest/email", payload)


@mcp.tool()
def get_suggestions(
    tenant_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
) -> str:
    """
    List suggestion cards produced by agents, pending human review.
    Each suggestion contains the agent's analysis and recommended action.
    No suggestion is committed until a human approves it.

    Args:
        tenant_id:  Tenant identifier. Defaults to configured default.
        status:     Filter by status: "pending", "approved", "rejected", "escalated".
                    Omit for all.
        limit:      Maximum number of suggestions to return (default 20).

    Returns:
        List of suggestion cards with id, agent, status, summary, and timestamp.
    """
    tid = tenant_id or TENANT_ID
    params = {"limit": limit}
    if status:
        params["status"] = status
    return _get(f"/suggestions/{tid}", params=params)


@mcp.tool()
def get_suggestion(
    suggestion_id: str,
    tenant_id: Optional[str] = None,
) -> str:
    """
    Get full detail for a single suggestion card by its ID.
    Shows the complete agent analysis, recommended journal entry or action,
    confidence level, supporting reasoning, and current status.

    Args:
        suggestion_id:  The suggestion ID (from get_suggestions).
        tenant_id:      Tenant identifier. Defaults to configured default.

    Returns:
        Full suggestion detail including agent output and reasoning.
    """
    tid = tenant_id or TENANT_ID
    return _get(f"/suggestions/{tid}/{suggestion_id}")


@mcp.tool()
def decide(
    suggestion_id: str,
    decision: str,
    reason: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> str:
    """
    Approve, reject, or escalate a suggestion card.
    This is the human approval gate — nothing is posted to the accounting
    system until a decision of "approved" is made here.

    Args:
        suggestion_id:  The suggestion ID to act on.
        decision:       One of: "approved", "rejected", "escalated".
        reason:         Optional reason or context for the decision.
                        Required when escalating; recommended when rejecting.
        tenant_id:      Tenant identifier. Defaults to configured default.

    Returns:
        Updated suggestion status and, if approved, confirmation of posting.
    """
    tid = tenant_id or TENANT_ID
    if decision not in ("approved", "rejected", "escalated"):
        return "❌ decision must be one of: approved, rejected, escalated"
    payload = {"decision": decision}
    if reason:
        payload["reason"] = reason
    return _post(f"/suggestions/{tid}/{suggestion_id}/decide", payload)


# ===========================================================================
# TIER 2 — Department analysis
# ===========================================================================

@mcp.tool()
def analyze_tax(
    content: str,
    jurisdiction: Optional[str] = None,
    tenant_id: Optional[str] = None,
    supervised: bool = False,
) -> str:
    """
    Submit content for tax analysis. Routes automatically to the Tanzania (TZ)
    or US tax specialist based on jurisdiction or content signals.
    Covers CIT, VAT, WHT, transfer pricing (TZ) and LLC pass-through,
    SE tax, QBI deduction, quarterly estimates (US).

    Args:
        content:      Tax scenario, transaction, or question to analyse.
        jurisdiction: "TZ" for Tanzania, "US" for United States.
                      Omit to let the system auto-detect.
        tenant_id:    Tenant identifier. Defaults to configured default.
        supervised:   If True, routes through Tax Supervisor for automatic
                      second-level review before surfacing to human.

    Returns:
        Tax analysis suggestion card with recommended treatment and reasoning.
        If supervised=True, includes supervisor review layer.
    """
    tid = tenant_id or TENANT_ID
    payload = {"content": content, "tenant_id": tid}
    if jurisdiction:
        payload["jurisdiction"] = jurisdiction
    endpoint = "/tax/analyze/supervised" if supervised else "/tax/analyze"
    return _post(endpoint, payload)


@mcp.tool()
def analyze_fpa(
    content: str,
    analysis_type: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> str:
    """
    Submit content for FP&A analysis. Routes to the appropriate FP&A agent —
    Analyst, Manager, Senior FP&A Manager, VP of Finance, or Data Analyst —
    based on complexity and content signals.
    Covers budgeting, forecasting, variance analysis, scenario planning,
    and management reporting.

    Args:
        content:        Financial data, question, or scenario for FP&A review.
        analysis_type:  Optional hint: "budget", "forecast", "variance",
                        "scenario", "reporting".
        tenant_id:      Tenant identifier. Defaults to configured default.

    Returns:
        FP&A suggestion card with analysis, recommendations, and reasoning.
    """
    tid = tenant_id or TENANT_ID
    payload = {"content": content, "tenant_id": tid}
    if analysis_type:
        payload["analysis_type"] = analysis_type
    return _post("/fpa/analyze", payload)


@mcp.tool()
def analyze_audit(
    content: str,
    analysis_type: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> str:
    """
    Submit content for audit analysis. Routes to Compliance Auditor,
    Audit Manager, QA Auditor, or Forensic Auditor based on content signals.
    Covers ISA compliance (TZ/NBAA), internal controls, fraud indicators,
    AML/FCPA flags, and audit findings.

    Args:
        content:        Transaction, process, or scenario to audit.
        analysis_type:  Optional hint: "compliance", "internal_control",
                        "forensic", "quality".
        tenant_id:      Tenant identifier. Defaults to configured default.

    Returns:
        Audit suggestion card with findings, risk flags, and recommended actions.
    """
    tid = tenant_id or TENANT_ID
    payload = {"content": content, "tenant_id": tid}
    if analysis_type:
        payload["analysis_type"] = analysis_type
    return _post("/audit/analyze", payload)


@mcp.tool()
def analyze_treasury(
    content: str,
    analysis_type: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> str:
    """
    Submit content for treasury analysis. Routes to Cash Flow Analyst,
    Liquidity Manager, Investment Strategist, Treasury Manager,
    Capital Markets Analyst, or Hedge Fund Manager based on content.
    Covers cash flow forecasting, liquidity, FX exposure, investments,
    and capital markets.

    Args:
        content:        Treasury scenario, position, or question.
        analysis_type:  Optional hint: "cashflow", "liquidity", "fx",
                        "investment", "capital_markets".
        tenant_id:      Tenant identifier. Defaults to configured default.

    Returns:
        Treasury suggestion card with analysis and recommended action.
    """
    tid = tenant_id or TENANT_ID
    payload = {"content": content, "tenant_id": tid}
    if analysis_type:
        payload["analysis_type"] = analysis_type
    return _post("/treasury/analyze", payload)


@mcp.tool()
def analyze_accounting(
    content: str,
    analysis_type: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> str:
    """
    Submit content for specialist accounting analysis. Routes to
    Cost Accountant, Revenue Accountant, or Accounting Manager.
    Covers cost allocation, COGS, revenue recognition (IFRS 15),
    accruals, provisions, and management accounting.
    CRITICAL flags (geographic/mathematical errors) auto-escalate.

    Args:
        content:        Transaction, scenario, or accounting question.
        analysis_type:  Optional hint: "cost", "revenue", "management".
        tenant_id:      Tenant identifier. Defaults to configured default.

    Returns:
        Accounting suggestion card with recommended treatment and journal entry.
    """
    tid = tenant_id or TENANT_ID
    payload = {"content": content, "tenant_id": tid}
    if analysis_type:
        payload["analysis_type"] = analysis_type
    return _post("/accounting/analyze", payload)


@mcp.tool()
def analyze_universal(
    content: str,
    tenant_id: Optional[str] = None,
) -> str:
    """
    Submit any financial content to the universal router (Phase4Orchestrator).
    Haiku L1 classifies the content and routes to the correct department
    and agent automatically. Use this when you are unsure which department
    should handle the content.

    Args:
        content:    Any financial text, transaction, question, or document.
        tenant_id:  Tenant identifier. Defaults to configured default.

    Returns:
        Suggestion card from whichever agent the orchestrator selected.
    """
    tid = tenant_id or TENANT_ID
    return _post("/analyze", {"content": content, "tenant_id": tid})


# ===========================================================================
# TIER 3 — Operations
# ===========================================================================

@mcp.tool()
def list_escalations(status: Optional[str] = None) -> str:
    """
    List escalations that have been raised by agents or operators.
    Escalations occur when an agent cannot resolve a suggestion within
    its authority level and requires human or senior agent intervention.

    Args:
        status:  Optional filter: "pending", "approved", "rejected".
                 Omit for all escalations.

    Returns:
        List of escalations with id, type, agent, reason, and status.
    """
    params = {}
    if status:
        params["status"] = status
    return _get("/escalations", params=params)


@mcp.tool()
def approve_escalation(
    escalation_id: str,
    decision: str,
    notes: Optional[str] = None,
) -> str:
    """
    Approve or reject an escalation raised by an agent.
    This is the senior human approval gate for complex or ambiguous cases
    that exceeded the agent's authority level.

    Args:
        escalation_id:  The escalation ID (from list_escalations).
        decision:       "approved" or "rejected".
        notes:          Optional notes or instructions for the agent.

    Returns:
        Updated escalation status.
    """
    if decision not in ("approved", "rejected"):
        return "❌ decision must be 'approved' or 'rejected'"
    payload = {"decision": decision}
    if notes:
        payload["notes"] = notes
    return _post(f"/escalations/{escalation_id}/approve", payload)


@mcp.tool()
def get_market_rates() -> str:
    """
    Return live FX rates and US market rates from the ecosystem's market
    data feed. Includes major currency pairs and benchmark rates.
    Used by treasury and FP&A agents for valuation and FX exposure analysis.

    Returns:
        Current FX rates and US market benchmark rates.
    """
    return _get("/market/rates")


@mcp.tool()
def get_fx_rate(
    from_currency: str,
    to_currency: str,
) -> str:
    """
    Return the current exchange rate for a specific currency pair.

    Args:
        from_currency:  Source currency code, e.g. "USD", "TZS", "EUR", "GBP".
        to_currency:    Target currency code, e.g. "TZS", "USD", "EUR".

    Returns:
        Current exchange rate for the pair.
    """
    return _get(f"/market/fx/{from_currency.upper()}/{to_currency.upper()}")


@mcp.tool()
def list_tenants() -> str:
    """
    List all tenants configured in the Finance AI Ecosystem.
    Each tenant is an isolated namespace — suggestions, stats, and agent
    history are scoped per tenant.

    Returns:
        List of tenant IDs and names.
    """
    return _get("/tenants")


@mcp.tool()
def sync_postgres() -> str:
    """
    Trigger a manual sync from SQLite (offline store) to Postgres.
    The system runs fully on SQLite when offline and auto-syncs on reconnection.
    Use this to force an immediate sync after coming back online.

    Returns:
        Sync result — number of records synced and any errors.
    """
    return _post("/sync", {})


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    mcp.run()
