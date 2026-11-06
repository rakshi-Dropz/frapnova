import frappe
from frappe import _
from frappe.utils import flt

# -------------------------------------------------------------
# Function 1: Catalog & Stock Levels
# -------------------------------------------------------------
@frappe.whitelist()
def get_inventory_summary():
    """
    Returns inventory levels, unit prices, categories, and stock status.
    Claude will call this when you ask questions like:
    - 'What items are low on stock?'
    - 'What is our current catalog value?'
    """
    items = frappe.db.sql("""
        SELECT 
            name AS item_code,
            item_name,
            category,
            rate,
            current_stock,
            CASE 
                WHEN current_stock <= 0 THEN 'Out of Stock'
                WHEN current_stock <= 5 THEN 'Low Stock'
                ELSE 'Healthy'
            END AS stock_status
        FROM `tabStock Item`
        ORDER BY current_stock ASC
    """, as_dict=True)
    
    return items


# -------------------------------------------------------------
# Function 2: Order Activity & Tracking
# -------------------------------------------------------------
@frappe.whitelist()
def get_order_analytics(limit=50):
    """
    Returns recent order records, quantities, and delivery milestones.
    Claude will call this when you ask questions like:
    - 'How many orders were placed today?'
    - 'Are there any orders waiting for dispatch?'
    """
    orders = frappe.db.sql("""
        SELECT 
            name AS order_id,
            owner AS agent,
            item,
            quantity,
            rate,
            total_amount,
            docstatus,
            tracking_status,
            creation
        FROM `tabStock Order`
        ORDER BY creation DESC
        LIMIT %s
    """, (int(limit),), as_dict=True)
    
    return orders


# -------------------------------------------------------------
# Function 3: High-Level Revenue & Performance
# -------------------------------------------------------------
@frappe.whitelist()
def get_sales_and_revenue_kpis():
    """
    Aggregates total cleared sales, order counts, and agent sales breakdown.
    Claude will call this when you ask questions like:
    - 'Who is our top performing agent?'
    - 'What is our total cleared revenue?'
    """
    # 1. Calculate total revenue from approved/submitted orders (docstatus = 1)
    revenue_result = frappe.db.sql("""
        SELECT COALESCE(SUM(total_amount), 0)
        FROM `tabStock Order`
        WHERE docstatus = 1
    """)
    total_revenue = flt(revenue_result[0][0]) if revenue_result else 0.0

    # 2. Count key operational indicators
    total_orders = frappe.db.count("Stock Order", filters={"docstatus": 1})
    pending_orders = frappe.db.count("Stock Order", filters={"docstatus": 0})
    out_of_stock_count = frappe.db.count("Stock Item", filters={"current_stock": ["<=", 0]})

    # 3. Agent breakdown with full names (joining tabUser)
    agent_breakdown = frappe.db.sql("""
        SELECT 
            COALESCE(u.full_name, o.owner) AS agent_name,
            COUNT(o.name) AS completed_orders,
            SUM(o.total_amount) AS revenue_generated
        FROM `tabStock Order` o
        LEFT JOIN `tabUser` u ON o.owner = u.name COLLATE utf8mb4_unicode_ci
        WHERE o.docstatus = 1
        GROUP BY o.owner
        ORDER BY revenue_generated DESC
    """, as_dict=True)

    return {
        "total_revenue": total_revenue,
        "cleared_orders_count": total_orders,
        "pending_approval_count": pending_orders,
        "out_of_stock_skus": out_of_stock_count,
        "agent_performance": agent_breakdown
    }