import frappe

def check_low_stock_and_notify():
    """Background task to inspect inventory, broadcast SocketIO, and send alerts."""
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

    # 2. Dispatch low stock email alert
    send_low_stock_email(low_stock_items)


def send_low_stock_email(items):
    """Sends low stock warning email immediately with rendered HTML."""
    # Find all users with Stock Manager or System Manager roles
    manager_names = frappe.get_all(
        "Has Role",
        filters={"role": ["in", ["Stock Manager", "System Manager"]], "parenttype": "User"},
        pluck="parent"
    )

    # Fetch valid emails for active manager accounts
    recipients = []
    if manager_names:
        recipients = frappe.get_all(
            "User",
            filters={"name": ["in", list(set(manager_names))], "enabled": 1},
            pluck="email"
        )
    
    # Filter out empty or test domains and fall back to the admin address
    valid_recipients = [r for r in recipients if r and "@" in r and not r.endswith(".local")]

    if not valid_recipients:
        valid_recipients = ["rakshitha@dropz.in"]

    # Build clean HTML list
    item_list_html = "".join([
        f"<li style='margin-bottom: 6px;'>{i['item_name']}: <b style='color: #b91c1c;'>{int(i['current_stock'])} units remaining</b></li>"
        for i in items
    ])

    html_message = f"""
    <div style="font-family: Arial, sans-serif; font-size: 14px; color: #333; line-height: 1.5;">
        <h3 style="color: #dc2626; margin-bottom: 8px;">⚠️ Low Stock Inventory Alert</h3>
        <p>The following items have reached or fallen below the threshold limit (5 units):</p>
        <ul style="background-color: #fef2f2; border: 1px solid #fecaca; border-radius: 6px; padding: 16px 28px; margin: 15px 0;">
            {item_list_html}
        </ul>
        <p>Please log in to the Frapnora portal to replenish warehouse inventory.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;" />
        <p style="font-size: 12px; color: #666;">This is an automated notification from Frapnora Stock Flow.</p>
    </div>
    """

    # sendmail with now=True builds valid MIME multipart HTML and dispatches immediately
    frappe.sendmail(
        recipients=list(set(valid_recipients)),
        subject="Low Stock Inventory Warning",
        message=html_message,
        now=True
    )