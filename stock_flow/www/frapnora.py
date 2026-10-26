import frappe

def get_context(context):
    roles = frappe.get_roles(frappe.session.user)
    context.is_admin = "System Manager" in roles or frappe.session.user == "Administrator"
    context.is_manager = "Stock Manager" in roles or context.is_admin
    context.is_agent = "Agent" in roles or context.is_admin

    context.user_fullname = frappe.utils.get_fullname(frappe.session.user)

    has_category = frappe.db.has_column("Stock Item", "category")

    fields = ["name", "item_name", "rate", "current_stock", "image"]
    if has_category:
        fields.append("category")

    context.stock_items = frappe.get_all("Stock Item", fields=fields)

    # Categories
    if has_category:
        context.categories = frappe.db.sql(
            "SELECT DISTINCT category FROM `tabStock Item` WHERE category IS NOT NULL AND TRIM(category) != '' ORDER BY category ASC",
            pluck=True
        ) or []
    else:
        context.categories = []

    # Calculate Revenue for Sidebar
    if context.is_admin or context.is_manager:
        # Total revenue across all approved orders
        rev = frappe.db.sql(
            "SELECT COALESCE(SUM(total_amount), 0) FROM `tabStock Order` WHERE docstatus = 1",
            pluck=True
        )
        context.revenue = float(rev[0]) if rev else 0.0
    else:
        # Agent personal revenue/spend
        rev = frappe.db.sql(
            "SELECT COALESCE(SUM(total_amount), 0) FROM `tabStock Order` WHERE owner = %s AND docstatus = 1",
            (frappe.session.user,),
            pluck=True
        )
        context.revenue = float(rev[0]) if rev else 0.0

    if context.is_agent:
        context.my_orders = frappe.get_all(
            "Stock Order",
            filters={"owner": frappe.session.user},
            fields=["name", "item", "quantity", "rate", "total_amount", "docstatus", "creation"],
            order_by="creation desc"
        )
    else:
        context.my_orders = []

    if context.is_manager:
        context.pending_orders = frappe.get_all(
            "Stock Order",
            filters={"docstatus": 0},
            fields=["name", "owner", "item", "quantity", "total_amount"]
        )
    else:
        context.pending_orders = []

    return context