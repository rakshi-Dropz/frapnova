import frappe

def check_low_stock_and_notify():
    """Background task to inspect inventory, broadcast SocketIO, and queue emails."""
    low_stock_items = frappe.db.get_all(
        "Stock Item",
        filters={"current_stock": ["<=", 5]},
        fields=["name", "item_name", "current_stock"]
    )

    if not low_stock_items:
        return

    # 1. SocketIO broadcast to online users
    try:
        frappe.publish_realtime(
            event="low_stock_alert",
            message={
                "title": "Low Stock Alert",
                "count": len(low_stock_items),
                "items": [item.item_name for item in low_stock_items]
            },
            user=None
        )
    except Exception:
        pass

    # 2. Queue Email
    send_low_stock_email(low_stock_items)


def send_low_stock_email(items):
    """Queues low stock warning directly in the Frappe Email Queue table."""
    managers = frappe.get_all(
        "Has Role",
        filters={"role": "Stock Manager", "parenttype": "User"},
        pluck="parent"
    )
    recipients = [m for m in managers if "@" in m]

    if not recipients:
        admin_email = frappe.db.get_value("User", "Administrator", "email")
        recipients = [admin_email] if admin_email and "@" in admin_email else ["admin@frapnova.local"]

    item_list_html = "".join([
        f"<li>{i['item_name']}: <b>{i['current_stock']} left</b></li>"
        for i in items
    ])
    html_message = f"<h3>Inventory Warning</h3><p>The following items are running low:</p><ul>{item_list_html}</ul>"

    # Direct Email Queue insertion
    eq = frappe.new_doc("Email Queue")
    eq.sender = "system@frapnova.local"
    eq.message = html_message
    for recipient in recipients:
        eq.append("recipients", {
            "recipient": recipient,
            "status": "Not Sent"
        })
    eq.insert(ignore_permissions=True)
    frappe.db.commit()