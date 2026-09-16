import frappe

def get_context(context):
    context.no_cache = 1
    user = frappe.session.user
    
    if user == "Guest":
        frappe.redirect_to_login()
        return

    user_roles = frappe.get_roles(user)
    context.is_admin = "System Manager" in user_roles or user == "Administrator"
    context.is_manager = "Stock Manager" in user_roles or context.is_admin
    context.is_agent = "Support Agent" in user_roles or context.is_admin
    context.user_fullname = frappe.utils.get_fullname(user)

    if context.is_manager:
        context.pending_orders = frappe.get_all(
            "Stock Order",
            filters={"docstatus": 0},
            fields=["name", "item", "quantity", "rate", "total_amount", "item_image", "owner"],
            order_by="creation desc"
        )

    if context.is_agent:
        # Fetch fresh list directly from Stock Item DocType
        context.stock_items = frappe.get_all(
            "Stock Item",
            fields=["name", "item_name", "image", "rate", "current_stock"]
        )
        context.my_orders = frappe.get_all(
            "Stock Order",
            filters={"owner": user} if not context.is_admin else {},
            fields=["name", "item", "quantity", "rate", "total_amount", "item_image", "docstatus", "status"],
            order_by="creation desc"
        )

    return context