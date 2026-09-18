import frappe

@frappe.whitelist()
def create_stock_item(item_name, rate, current_stock, image_url=None):
    user_roles = frappe.get_roles()
    if "System Manager" not in user_roles and frappe.session.user != "Administrator":
        frappe.throw("Permission denied: Only Administrators can add products.")

    if not item_name or not item_name.strip():
        frappe.throw("Item Name is required.")

    item_code = item_name.strip()
    rate_val = float(rate or 0)
    stock_val = float(current_stock or 0)

    image_path = (image_url or "").strip()
    if image_path.startswith("/private/files/"):
        image_path = image_path.replace("/private/files/", "/files/")

    frappe.db.sql("""
        INSERT INTO `tabStock Item` (name, item_name, rate, current_stock, image, creation, modified, owner, docstatus)
        VALUES (%s, %s, %s, %s, %s, NOW(), NOW(), %s, 0)
        ON DUPLICATE KEY UPDATE 
            item_name=%s, rate=%s, current_stock=%s, image=%s, modified=NOW()
    """, (item_code, item_name, rate_val, stock_val, image_path, frappe.session.user, item_name, rate_val, stock_val, image_path))

    frappe.db.commit()
    return item_code


@frappe.whitelist()
def update_stock_item(item_code, rate=None, current_stock=None, image_url=None):
    user_roles = frappe.get_roles()
    if "System Manager" not in user_roles and frappe.session.user != "Administrator":
        frappe.throw("Permission denied: Only Administrators can edit products.")

    if not frappe.db.exists("Stock Item", item_code):
        frappe.throw(f"Stock Item '{item_code}' does not exist.")

    image_path = (image_url or "").strip()
    if image_path.startswith("/private/files/"):
        image_path = image_path.replace("/private/files/", "/files/")

    updates = {}
    if rate is not None and str(rate).strip() != "":
        updates["rate"] = float(rate)
    if current_stock is not None and str(current_stock).strip() != "":
        updates["current_stock"] = float(current_stock)
    if image_path:
        updates["image"] = image_path

    if updates:
        frappe.db.set_value("Stock Item", item_code, updates)
        frappe.db.commit()

    return "Success"


@frappe.whitelist()
def delete_stock_item(item_code):
    user_roles = frappe.get_roles()
    if "System Manager" not in user_roles and frappe.session.user != "Administrator":
        frappe.throw("Permission denied: Only Administrators can delete products.")

    frappe.delete_doc("Stock Item", item_code, ignore_permissions=True)
    frappe.db.commit()
    return "Success"


@frappe.whitelist()
def create_stock_order(item_code, quantity=1):
    if frappe.session.user == "Guest":
        frappe.throw("Please log in to place orders.")

    qty = float(quantity)
    if qty <= 0:
        frappe.throw("Quantity must be greater than zero.")

    if not frappe.db.exists("Stock Item", item_code):
        frappe.throw(f"Stock Item '{item_code}' does not exist.")

    item_data = frappe.db.get_value("Stock Item", item_code, ["rate", "image"], as_dict=True) or {}
    rate = float(item_data.get("rate") or 0)

    image_path = item_data.get("image") or ""
    if image_path.startswith("/private/files/"):
        image_path = image_path.replace("/private/files/", "/files/")

    doc = frappe.get_doc({
        "doctype": "Stock Order",
        "item": item_code,
        "quantity": qty,
        "rate": rate,
        "total_amount": rate * qty,
        "item_image": image_path
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return doc.name


@frappe.whitelist()
def approve_stock_order(order_id):
    if frappe.session.user == "Guest":
        frappe.throw("Please log in to approve orders.")

    user_roles = frappe.get_roles()
    if "Stock Manager" not in user_roles and "System Manager" not in user_roles and frappe.session.user != "Administrator":
        frappe.throw("Permission denied: Only Stock Managers can approve orders.")

    doc = frappe.get_doc("Stock Order", order_id)
    doc.flags.ignore_permissions = True

    if doc.docstatus == 1:
        frappe.throw("Order is already submitted/approved.")

    current_stock = frappe.db.get_value("Stock Item", doc.item, "current_stock") or 0
    if current_stock < doc.quantity:
        frappe.throw(f"Insufficient stock for '{doc.item}'. Available: {current_stock}")

    new_stock = current_stock - doc.quantity
    frappe.db.set_value("Stock Item", doc.item, "current_stock", new_stock)

    doc.submit()
    frappe.db.commit()
    return "Success"
    @frappe.whitelist(allow_guest=False)
def bulk_process_orders(order_ids):
    """Whitelisted API endpoint to process multiple pending order approvals at once."""
    user_roles = frappe.get_roles()
    if "Stock Manager" not in user_roles and "System Manager" not in user_roles and frappe.session.user != "Administrator":
        frappe.throw("Access denied: Stock Manager privileges required.")

    if isinstance(order_ids, str):
        import json
        order_ids = json.loads(order_ids)

    processed = []
    for oid in order_ids:
        doc = frappe.get_doc("Stock Order", oid)
        if doc.docstatus == 0:
            doc.flags.ignore_permissions = True
            current_stock = frappe.db.get_value("Stock Item", doc.item, "current_stock") or 0
            if current_stock >= doc.quantity:
                frappe.db.set_value("Stock Item", doc.item, "current_stock", current_stock - doc.quantity)
                doc.submit()
                processed.append(oid)

    frappe.db.commit()
    return {"status": "Success", "approved_orders": processed}