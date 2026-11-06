import os
import sys
import httpx
from mcp.server.fastmcp import FastMCP

# Initialize the FastMCP Server instance
mcp = FastMCP("FRAPNORA Stock & Revenue Intelligence")

# Configuration loaded via environment variables
FRAPPE_URL = os.environ.get("FRAPPE_URL", "http://127.0.0.1:8000")
FRAPPE_API_KEY = os.environ.get("FRAPPE_API_KEY", "")
FRAPPE_API_SECRET = os.environ.get("FRAPPE_API_SECRET", "")


def get_headers():
    """Generates Frappe token authentication headers."""
    if not FRAPPE_API_KEY or not FRAPPE_API_SECRET:
        raise ValueError("Missing FRAPPE_API_KEY or FRAPPE_API_SECRET environment variables.")
    return {
        "Authorization": f"token {FRAPPE_API_KEY}:{FRAPPE_API_SECRET}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }


# -------------------------------------------------------------
# Tool 1: Catalog & Stock Status
# -------------------------------------------------------------
@mcp.tool()
def fetch_inventory_status() -> str:
    """Fetch current stock levels, unit pricing, categories, and stockout warnings across all catalog SKUs."""
    url = f"{FRAPPE_URL}/api/method/stock_flow.mcp_api.get_inventory_summary"
    with httpx.Client(timeout=15.0) as client:
        res = client.get(url, headers=get_headers())
        if res.status_code != 200:
            return f"Error ({res.status_code}): {res.text}"
        return res.text


# -------------------------------------------------------------
# Tool 2: Order Tracking & History
# -------------------------------------------------------------
@mcp.tool()
def fetch_order_history(limit: int = 50) -> str:
    """Fetch recent orders, quantities, line amounts, and fulfillment/tracking statuses."""
    url = f"{FRAPPE_URL}/api/method/stock_flow.mcp_api.get_order_analytics"
    with httpx.Client(timeout=15.0) as client:
        res = client.get(url, headers=get_headers(), params={"limit": limit})
        if res.status_code != 200:
            return f"Error ({res.status_code}): {res.text}"
        return res.text


# -------------------------------------------------------------
# Tool 3: Executive Business KPIs
# -------------------------------------------------------------
@mcp.tool()
def fetch_executive_kpis() -> str:
    """Fetch total sales revenue, pending order queue size, stockout counts, and agent sales breakdown."""
    url = f"{FRAPPE_URL}/api/method/stock_flow.mcp_api.get_sales_and_revenue_kpis"
    with httpx.Client(timeout=15.0) as client:
        res = client.get(url, headers=get_headers())
        if res.status_code != 200:
            return f"Error ({res.status_code}): {res.text}"
        return res.text


if __name__ == "__main__":
    # Runs the server over stdio for Claude Desktop
    mcp.run(transport="stdio")