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

    # Fetch active catalog items
    stock_items = frappe.db.get_all(
        "Stock Item",
        fields=["name", "item_name", "image", "rate", "current_stock"]
    )
    for item in stock_items:
        if item.get("image") and item["image"].startswith("/private/files/"):
            item["image"] = item["image"].replace("/private/files/", "/files/")
    context.stock_items = stock_items

    # Fetch pending orders for Manager view
    if context.is_manager:
        pending_orders = frappe.db.get_all(
            "Stock Order",
            filters={"docstatus": 0},
            fields=["name", "item", "quantity", "rate", "total_amount", "item_image", "owner"],
            order_by="creation desc"
        )
        for order in pending_orders:
            if order.get("item_image") and order["item_image"].startswith("/private/files/"):
                order["item_image"] = order["item_image"].replace("/private/files/", "/files/")
        context.pending_orders = pending_orders

    # Fetch user orders for Agent view
    if context.is_agent:
        my_orders = frappe.db.get_all(
            "Stock Order",
            filters={"owner": user} if not context.is_admin else {},
            fields=["name", "item", "quantity", "rate", "total_amount", "item_image", "docstatus"],
            order_by="creation desc"
        )
        for order in my_orders:
            if order.get("item_image") and order["item_image"].startswith("/private/files/"):
                order["item_image"] = order["item_image"].replace("/private/files/", "/files/")
        context.my_orders = my_orders

    return context