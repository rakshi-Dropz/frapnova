import frappe

def check_low_stock_and_notify():
    """Background job to check low stock items and notify managers via SocketIO."""
    low_stock_items = frappe.db.get_all(
        "Stock Item",
        filters={"current_stock": ["<=", 5]},
        fields=["name", "item_name", "current_stock"]
    )

    if low_stock_items:
        frappe.publish_realtime(
            event="low_stock_alert",
            message={
                "title": "Low Stock Alert",
                "count": len(low_stock_items),
                "items": [item.item_name for item in low_stock_items]
            },
            user="manager@example.com"
        )

        frappe.enqueue(
            "stock_flow.tasks.send_low_stock_email",
            queue="short",
            items=low_stock_items
        )

def send_low_stock_email(items):
    """Background worker task to dispatch low stock email alerts."""
    item_list_html = "".join([f"<li>{i['item_name']}: <b>{i['current_stock']} left</b></li>" for i in items])

    frappe.sendmail(
        recipients=["manager@example.com"],
        subject="[Frapnova] Low Stock Alert",
        message=f"<h3>Inventory Warning</h3><ul>{item_list_html}</ul>"
    )