import frappe

@frappe.whitelist()
def create_stock_order(item_code, quantity=1):
    user_roles = frappe.get_roles()
    if "Support Agent" not in user_roles and "System Manager" not in user_roles:
        frappe.throw("Permission denied: Only Support Agents can create stock orders.")

    qty = float(quantity)
    if qty <= 0:
        frappe.throw("Quantity must be greater than zero.")

    # Fetch rate and image from master Stock Item
    item_doc = frappe.get_doc("Stock Item", item_code)
    rate = float(item_doc.rate or 0)
    total_amount = rate * qty

    doc = frappe.get_doc({
        "doctype": "Stock Order",
        "item": item_code,
        "quantity": qty,
        "rate": rate,
        "total_amount": total_amount,
        "item_image": item_doc.image
    })
    doc.insert()
    return doc.name


@frappe.whitelist()
def approve_stock_order(order_id):
    user_roles = frappe.get_roles()
    if "Stock Manager" not in user_roles and "System Manager" not in user_roles:
        frappe.throw("Permission denied: Only Stock Managers can approve orders.")

    doc = frappe.get_doc("Stock Order", order_id)
    doc.submit()
    return "Success"