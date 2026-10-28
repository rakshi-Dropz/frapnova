import frappe
from frappe.utils import flt, cint, now_datetime

@frappe.whitelist()
def create_stock_item(item_name, rate, current_stock, category=None, image_url=None):
    roles = frappe.get_roles(frappe.session.user)
    if "System Manager" not in roles and frappe.session.user != "Administrator":
        frappe.throw("Unauthorized", frappe.PermissionError)

    doc = frappe.get_doc({
        "doctype": "Stock Item",
        "item_name": item_name,
        "rate": flt(rate),
        "current_stock": cint(current_stock),
        "category": category or "Uncategorized",
        "image": image_url or ""
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return doc.name

@frappe.whitelist()
def update_stock_item(item_code, rate, current_stock, image_url=None, category=None):
    roles = frappe.get_roles(frappe.session.user)
    if "System Manager" not in roles and frappe.session.user != "Administrator":
        frappe.throw("Unauthorized", frappe.PermissionError)

    doc = frappe.get_doc("Stock Item", item_code)
    doc.rate = flt(rate)
    doc.current_stock = cint(current_stock)
    if category is not None:
        doc.category = category
    if image_url:
        doc.image = image_url
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return doc.name

@frappe.whitelist()
def delete_stock_item(item_code):
    roles = frappe.get_roles(frappe.session.user)
    if "System Manager" not in roles and frappe.session.user != "Administrator":
        frappe.throw("Unauthorized", frappe.PermissionError)

    frappe.delete_doc("Stock Item", item_code, ignore_permissions=True)
    frappe.db.commit()
    return {"message": "deleted"}

@frappe.whitelist()
def create_stock_order(item_code, quantity):
    qty = cint(quantity)
    if qty <= 0:
        frappe.throw("Quantity must be greater than zero.")

    stock_item = frappe.get_doc("Stock Item", item_code)
    if stock_item.current_stock < qty:
        frappe.throw(f"Insufficient stock. Available: {stock_item.current_stock}")

    order = frappe.get_doc({
        "doctype": "Stock Order",
        "item": item_code,
        "quantity": qty,
        "rate": stock_item.rate,
        "total_amount": flt(stock_item.rate) * qty,
        "docstatus": 0,
        "tracking_status": "Pending"
    })
    order.insert(ignore_permissions=True)
    frappe.db.commit()
    return order.name

@frappe.whitelist()
def approve_stock_order(order_id):
    roles = frappe.get_roles(frappe.session.user)
    if "Stock Manager" not in roles and "System Manager" not in roles and frappe.session.user != "Administrator":
        frappe.throw("Unauthorized: Manager role required to approve.", frappe.PermissionError)

    order = frappe.get_doc("Stock Order", order_id)
    if order.docstatus == 1:
        return {"message": "Already approved"}

    item = frappe.get_doc("Stock Item", order.item)
    if item.current_stock < order.quantity:
        frappe.throw(f"Cannot approve: Insufficient stock. Available: {item.current_stock}")

    item.current_stock = item.current_stock - order.quantity
    item.save(ignore_permissions=True)

    order.docstatus = 1
    order.tracking_status = "Approved"
    order.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": "Order approved"}

@frappe.whitelist()
def reject_stock_order(order_id):
    roles = frappe.get_roles(frappe.session.user)
    if "Stock Manager" not in roles and "System Manager" not in roles and frappe.session.user != "Administrator":
        frappe.throw("Unauthorized: Manager role required to reject.", frappe.PermissionError)

    order = frappe.get_doc("Stock Order", order_id)
    order.docstatus = 2
    order.tracking_status = "Rejected"
    order.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": "Order rejected"}

@frappe.whitelist()
def update_order_tracking(order_id, status, courier_name=None, tracking_number=None):
    roles = frappe.get_roles(frappe.session.user)
    if "Stock Manager" not in roles and "System Manager" not in roles and frappe.session.user != "Administrator":
        frappe.throw("Unauthorized. Manager role required.", frappe.PermissionError)

    order = frappe.get_doc("Stock Order", order_id)
    order.tracking_status = status

    if courier_name:
        order.courier_name = courier_name
    if tracking_number:
        order.tracking_number = tracking_number

    if status == "Dispatched":
        order.dispatched_on = now_datetime()
    elif status == "Delivered":
        order.delivered_on = now_datetime()

    order.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": "success", "status": order.tracking_status}

@frappe.whitelist()
def get_order_tracking(order_id):
    order = frappe.db.get_value(
        "Stock Order",
        order_id,
        [
            "name", "item", "quantity", "rate", "total_amount",
            "tracking_status", "courier_name", "tracking_number",
            "shipping_address", "dispatch_notes", "creation", "docstatus"
        ],
        as_dict=True
    )
    if not order:
        frappe.throw(f"Order {order_id} not found.", frappe.DoesNotExistError)
    return order

@frappe.whitelist()
def get_agent_performance_summary():
    roles = frappe.get_roles(frappe.session.user)
    if "Stock Manager" not in roles and "System Manager" not in roles and frappe.session.user != "Administrator":
        frappe.throw("Unauthorized", frappe.PermissionError)

    return frappe.db.sql("""
        SELECT 
            owner AS agent, 
            COUNT(name) AS total_orders, 
            SUM(total_amount) AS total_revenue
        FROM `tabStock Order`
        WHERE docstatus = 1
        GROUP BY owner
        ORDER BY total_revenue DESC
    """, as_dict=True)

@frappe.whitelist()
def get_agent_cart():
    user = frappe.session.user
    if user == "Guest":
        return []
    return frappe.get_all(
        "Stock Cart",
        filters={"owner": user},
        fields=["name", "item_code", "item_name", "quantity", "rate", "total_amount"]
    )

@frappe.whitelist()
def add_to_agent_cart(item_code, quantity=1):
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Login required", frappe.PermissionError)

    qty = cint(quantity)
    if qty <= 0:
        frappe.throw("Invalid quantity")

    stock_item = frappe.get_doc("Stock Item", item_code)
    existing = frappe.db.get_value("Stock Cart", {"owner": user, "item_code": item_code}, "name")

    if existing:
        cart_item = frappe.get_doc("Stock Cart", existing)
        cart_item.quantity += qty
        cart_item.total_amount = cart_item.quantity * stock_item.rate
        cart_item.save(ignore_permissions=True)
    else:
        cart_item = frappe.get_doc({
            "doctype": "Stock Cart",
            "item_code": item_code,
            "item_name": stock_item.item_name,
            "quantity": qty,
            "rate": stock_item.rate,
            "total_amount": qty * stock_item.rate
        })
        cart_item.insert(ignore_permissions=True)

    frappe.db.commit()
    return {"message": "Item added to cart"}

@frappe.whitelist()
def remove_from_agent_cart(name):
    frappe.delete_doc("Stock Cart", name, ignore_permissions=True)
    frappe.db.commit()
    return {"message": "Item removed"}

@frappe.whitelist()
def checkout_agent_cart(shipping_address="", dispatch_notes=""):
    user = frappe.session.user
    items = frappe.get_all("Stock Cart", filters={"owner": user}, fields=["*"])
    if not items:
        frappe.throw("Cart is empty")

    created_orders = []
    for itm in items:
        stock_item = frappe.get_doc("Stock Item", itm.item_code)
        if stock_item.current_stock < itm.quantity:
            frappe.throw(f"Insufficient stock for {itm.item_name}. Available: {stock_item.current_stock}")

        order = frappe.get_doc({
            "doctype": "Stock Order",
            "item": itm.item_code,
            "quantity": itm.quantity,
            "rate": itm.rate,
            "total_amount": itm.total_amount,
            "docstatus": 0,
            "tracking_status": "Pending",
            "shipping_address": shipping_address,
            "dispatch_notes": dispatch_notes
        })
        order.insert(ignore_permissions=True)
        created_orders.append(order.name)

    frappe.db.delete("Stock Cart", {"owner": user})
    frappe.db.commit()
    return {"message": "Success", "orders": created_orders}

@frappe.whitelist()
def get_agent_wishlist():
    user = frappe.session.user
    if user == "Guest":
        return []
    return frappe.get_all(
        "Stock Wishlist",
        filters={"owner": user},
        fields=["name", "item_code", "item_name", "rate"]
    )

@frappe.whitelist()
def add_to_agent_wishlist(item_code):
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Login required", frappe.PermissionError)

    if frappe.db.exists("Stock Wishlist", {"owner": user, "item_code": item_code}):
        return {"message": "Already in wishlist"}

    stock_item = frappe.get_doc("Stock Item", item_code)
    wish = frappe.get_doc({
        "doctype": "Stock Wishlist",
        "item_code": item_code,
        "item_name": stock_item.item_name,
        "rate": stock_item.rate
    })
    wish.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"message": "Added to wishlist"}

@frappe.whitelist()
def remove_from_agent_wishlist(name):
    frappe.delete_doc("Stock Wishlist", name, ignore_permissions=True)
    frappe.db.commit()
    return {"message": "Removed from wishlist"}