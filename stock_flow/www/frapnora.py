import frappe

def get_context(context):
    context.no_cache = 1
    user = frappe.session.user
    
    if user == "Guest":
        frappe.redirect_to_login()
        return

    user_roles = frappe.get_roles(user)
    
    # 1. User Role Flags (System Manager / Administrator gets full access across all views)
    context.is_admin = "System Manager" in user_roles or user == "Administrator"
    context.is_manager = "Stock Manager" in user_roles or context.is_admin
    context.is_agent = "Support Agent" in user_roles or "Stock Agent" in user_roles or context.is_admin
    context.user_fullname = frappe.utils.get_fullname(user)

    # 2. Fetch Active Catalog Items
    stock_items = frappe.db.get_all(
        "Stock Item",
        fields=["name", "item_name", "image", "rate", "current_stock"],
        order_by="creation desc"
    )
    for item in stock_items:
        if item.get("image") and item["image"].startswith("/private/files/"):
            item["image"] = item["image"].replace("/private/files/", "/files/")
    context.stock_items = stock_items

    # 3. Pending Orders for Managers/Admins (Draft status = 0)
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

    # 4. Agent Order List (Shows Drafts, Submitted, and Rejected/Cancelled)
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