import frappe

@frappe.whitelist()
def create_stock_order(item_code, quantity=1):
    """ Allows Support Agents to create Draft orders from the portal """
    user_roles = frappe.get_roles()
    if "Support Agent" not in user_roles and "System Manager" not in user_roles:
        frappe.throw("Permission denied: Only Support Agents can create stock orders.")

    doc = frappe.get_doc({
        "doctype": "Stock Order",
        "item": item_code,
        "quantity": int(quantity)
    })
    doc.insert()
    return doc.name


@frappe.whitelist()
def approve_stock_order(order_id):
    """ Allows Stock Managers to submit/approve orders from the portal """
    user_roles = frappe.get_roles()
    if "Stock Manager" not in user_roles and "System Manager" not in user_roles:
        frappe.throw("Permission denied: Only Stock Managers can approve orders.")

    doc = frappe.get_doc("Stock Order", order_id)
    doc.submit()
    return "Success"