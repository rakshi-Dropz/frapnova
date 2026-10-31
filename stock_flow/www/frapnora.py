import frappe
from frappe.utils import flt

def get_context(context):
    user = frappe.session.user
    if user == "Guest":
        frappe.local.flags.redirect_location = "/login"
        raise frappe.Redirect

    roles = frappe.get_roles(user)
    
    # Permission roles
    context.is_admin = (user == "Administrator") or ("System Manager" in roles)
    context.is_manager = ("Stock Manager" in roles) or ("Manager" in roles)
    context.user_fullname = frappe.db.get_value("User", user, "full_name") or user

    # Categories
    if frappe.db.exists("DocType", "Item Category"):
        context.categories = frappe.get_all("Item Category", pluck="name", order_by="name asc")
    else:
        context.categories = frappe.db.sql_list(
            "SELECT DISTINCT category FROM `tabStock Item` WHERE category IS NOT NULL AND category != '' ORDER BY category ASC"
        )

    # Stock Items catalog
    context.stock_items = frappe.get_all(
        "Stock Item",
        fields=["name", "item_name", "category", "rate", "current_stock", "image"],
        order_by="creation desc"
    )

    # Pending orders for manager/admin approval queue
    context.pending_orders = frappe.get_all(
        "Stock Order",
        filters={"docstatus": 0},
        fields=["name", "owner", "item", "quantity", "rate", "total_amount", "creation"],
        order_by="creation desc"
    )

    # User's own orders or all orders if admin/manager
    if context.is_admin or context.is_manager:
        context.my_orders = frappe.get_all(
            "Stock Order",
            fields=["name", "owner", "item", "quantity", "rate", "total_amount", "docstatus", "tracking_status", "creation"],
            order_by="creation desc",
            limit=50
        )
    else:
        context.my_orders = frappe.get_all(
            "Stock Order",
            filters={"owner": user},
            fields=["name", "owner", "item", "quantity", "rate", "total_amount", "docstatus", "tracking_status", "creation"],
            order_by="creation desc",
            limit=50
        )

    # Revenue calculation (Approved / Submitted orders)
    rev_result = frappe.db.sql("SELECT SUM(total_amount) FROM `tabStock Order` WHERE docstatus = 1")
    context.revenue = flt(rev_result[0][0]) if rev_result and rev_result[0][0] else 0.0

    return context