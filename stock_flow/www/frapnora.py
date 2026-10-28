import frappe

def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login"
        raise frappe.Redirect

    roles = frappe.get_roles(frappe.session.user)
    context.is_admin = "System Manager" in roles or frappe.session.user == "Administrator"
    context.is_manager = "Stock Manager" in roles or context.is_admin
    # Give all users (including Administrator/Manager) access to Cart, Orders & Wishlist for testing
    context.is_agent = True 

    context.user_fullname = frappe.utils.get_fullname(frappe.session.user)

    # Fetch Catalog Items
    context.stock_items = frappe.get_all(
        "Stock Item",
        fields=["name", "item_name", "rate", "current_stock", "category", "image"],
        order_by="creation desc"
    )

    # Categories list
    raw_cats = frappe.db.sql_list("SELECT DISTINCT category FROM `tabStock Item` WHERE category IS NOT NULL AND category != ''")
    context.categories = sorted(raw_cats) if raw_cats else ["Books", "Electronics", "Accessories"]

    # Revenue
    if context.is_manager:
        rev = frappe.db.sql("SELECT SUM(total_amount) FROM `tabStock Order` WHERE docstatus = 1")[0][0]
    else:
        rev = frappe.db.sql("SELECT SUM(total_amount) FROM `tabStock Order` WHERE docstatus = 1 AND owner = %s", frappe.session.user)[0][0]
    context.revenue = rev or 0.0

    # Orders with tracking metadata
    context.my_orders = frappe.get_all(
        "Stock Order",
        filters={"owner": frappe.session.user},
        fields=[
            "name", "item", "quantity", "rate", "total_amount",
            "docstatus", "creation", "tracking_status", "courier_name", "tracking_number"
        ],
        order_by="creation desc"
    )

    if context.is_manager:
        context.pending_orders = frappe.get_all(
            "Stock Order",
            filters={"docstatus": 0},
            fields=["name", "owner", "item", "quantity", "total_amount", "tracking_status"],
            order_by="creation desc"
        )
    else:
        context.pending_orders = []

    return context