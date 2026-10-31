import frappe
from frappe import _
from frappe.utils import now_datetime, flt

def ensure_cart_and_wishlist_tables():
    """Ensures dedicated cart and wishlist storage exists."""
    frappe.db.sql("""
        CREATE TABLE IF NOT EXISTS `tabStockFlowCart` (
            `name` varchar(140) PRIMARY KEY,
            `user` varchar(140) NOT NULL,
            `item_code` varchar(140) NOT NULL,
            `item_name` varchar(255) NOT NULL,
            `rate` decimal(18,2) DEFAULT 0.00,
            `quantity` decimal(18,2) DEFAULT 1.00,
            `creation` datetime,
            `modified` datetime,
            INDEX `idx_user` (`user`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    frappe.db.sql("""
        CREATE TABLE IF NOT EXISTS `tabStockFlowWishlist` (
            `name` varchar(140) PRIMARY KEY,
            `user` varchar(140) NOT NULL,
            `item_code` varchar(140) NOT NULL,
            `item_name` varchar(255) NOT NULL,
            `rate` decimal(18,2) DEFAULT 0.00,
            `creation` datetime,
            `modified` datetime,
            INDEX `idx_user` (`user`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    frappe.db.commit()


# ==========================================
# CART API
# ==========================================

@frappe.whitelist()
def get_agent_cart():
    ensure_cart_and_wishlist_tables()
    user = frappe.session.user
    if user == "Guest":
        return []

    items = frappe.db.sql("""
        SELECT name, item_code, item_name, rate, quantity
        FROM `tabStockFlowCart`
        WHERE user = %s
        ORDER BY creation DESC
    """, (user,), as_dict=True)

    return items


@frappe.whitelist()
def add_to_agent_cart(item_code, quantity=1):
    ensure_cart_and_wishlist_tables()
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Please log in to add items to your cart."))

    qty = flt(quantity)
    if qty <= 0:
        frappe.throw(_("Quantity must be greater than zero."))

    item = frappe.db.get_value("Stock Item", item_code, ["name", "item_name", "rate", "current_stock"], as_dict=True)
    if not item:
        frappe.throw(_("Item {0} does not exist in the catalog.").format(item_code))

    available_stock = flt(item.current_stock or 0)
    if available_stock <= 0:
        frappe.throw(_("{0} is currently out of stock.").format(item.item_name))

    existing = frappe.db.sql("""
        SELECT name, quantity FROM `tabStockFlowCart`
        WHERE user = %s AND item_code = %s
    """, (user, item_code), as_dict=True)

    now = now_datetime()

    if existing:
        new_qty = flt(existing[0].quantity) + qty
        if new_qty > available_stock:
            frappe.throw(_("Cannot add {0} more units. Maximum available stock is {1}.").format(qty, available_stock))

        frappe.db.sql("""
            UPDATE `tabStockFlowCart`
            SET quantity = %s, modified = %s
            WHERE name = %s
        """, (new_qty, now, existing[0].name))
    else:
        if qty > available_stock:
            frappe.throw(_("Requested quantity ({0}) exceeds available stock ({1}).").format(qty, available_stock))

        cart_id = frappe.generate_hash(length=12)
        frappe.db.sql("""
            INSERT INTO `tabStockFlowCart` (name, user, item_code, item_name, rate, quantity, creation, modified)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (cart_id, user, item_code, item.item_name, flt(item.rate), qty, now, now))

    frappe.db.commit()
    return {"message": "Success", "item_code": item_code}


@frappe.whitelist()
def remove_from_agent_cart(name=None, cart_id=None):
    ensure_cart_and_wishlist_tables()
    user = frappe.session.user
    target_id = name or cart_id
    if not target_id:
        return

    frappe.db.sql("""
        DELETE FROM `tabStockFlowCart`
        WHERE name = %s AND user = %s
    """, (target_id, user))

    frappe.db.commit()
    return {"message": "Removed"}


@frappe.whitelist()
def checkout_agent_cart(shipping_address="", dispatch_notes=""):
    ensure_cart_and_wishlist_tables()
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Please log in to place an order."))

    cart_items = frappe.db.sql("""
        SELECT name, item_code, item_name, rate, quantity
        FROM `tabStockFlowCart`
        WHERE user = %s
    """, (user,), as_dict=True)

    if not cart_items:
        frappe.throw(_("Your cart is empty. Please add items before checking out."))

    created_orders = []

    for line in cart_items:
        item_code = line.item_code
        req_qty = flt(line.quantity)

        stock_val = frappe.db.get_value("Stock Item", item_code, ["current_stock", "item_name"], as_dict=True)
        live_stock = flt(stock_val.current_stock or 0) if stock_val else 0

        if live_stock < req_qty:
            frappe.throw(_("Insufficient stock for {0}. Only {1} available.").format(stock_val.item_name, live_stock))

        order = frappe.new_doc("Stock Order")

        for field in ["item", "stock_item", "item_code"]:
            if hasattr(order, field) or field in order.as_dict():
                setattr(order, field, item_code)

        order.quantity = req_qty
        order.rate = flt(line.rate)
        order.total_amount = flt(line.rate) * req_qty
        order.docstatus = 0

        if hasattr(order, "tracking_status"):
            order.tracking_status = "Pending"
        if hasattr(order, "shipping_address"):
            order.shipping_address = shipping_address
        if hasattr(order, "dispatch_notes"):
            order.dispatch_notes = dispatch_notes
        if hasattr(order, "agent"):
            order.agent = user

        order.insert(ignore_permissions=True)
        created_orders.append(order.name)

        # Single authoritative deduction at checkout
        new_stock = max(0, live_stock - req_qty)
        frappe.db.set_value("Stock Item", item_code, "current_stock", new_stock)

    frappe.db.sql("DELETE FROM `tabStockFlowCart` WHERE user = %s", (user,))
    frappe.db.commit()

    return {
        "status": "success",
        "orders_created": created_orders
    }


# ==========================================
# WISHLIST API
# ==========================================

@frappe.whitelist()
def get_agent_wishlist():
    ensure_cart_and_wishlist_tables()
    user = frappe.session.user
    if user == "Guest":
        return []

    items = frappe.db.sql("""
        SELECT name, item_code, item_name, rate
        FROM `tabStockFlowWishlist`
        WHERE user = %s
        ORDER BY creation DESC
    """, (user,), as_dict=True)

    return items


@frappe.whitelist()
def add_to_agent_wishlist(item_code):
    ensure_cart_and_wishlist_tables()
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Please log in to manage your wishlist."))

    item = frappe.db.get_value("Stock Item", item_code, ["name", "item_name", "rate"], as_dict=True)
    if not item:
        frappe.throw(_("Item not found."))

    exists = frappe.db.sql("""
        SELECT name FROM `tabStockFlowWishlist`
        WHERE user = %s AND item_code = %s
    """, (user, item_code), as_dict=True)

    if not exists:
        wishlist_id = frappe.generate_hash(length=12)
        now = now_datetime()
        frappe.db.sql("""
            INSERT INTO `tabStockFlowWishlist` (name, user, item_code, item_name, rate, creation, modified)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (wishlist_id, user, item_code, item.item_name, flt(item.rate), now, now))
        frappe.db.commit()

    return {"message": "Success"}


@frappe.whitelist()
def remove_from_agent_wishlist(name=None, wishlist_id=None):
    ensure_cart_and_wishlist_tables()
    user = frappe.session.user
    target = name or wishlist_id
    if not target:
        return

    frappe.db.sql("DELETE FROM `tabStockFlowWishlist` WHERE name = %s AND user = %s", (target, user))
    frappe.db.commit()
    return {"message": "Removed"}


# ==========================================
# ORDER TRACKING & APPROVALS API
# ==========================================

@frappe.whitelist()
def get_order_tracking(order_id):
    order = frappe.get_doc("Stock Order", order_id)
    courier = getattr(order, "courier_name", None) or getattr(order, "courier_partner", "—")
    return {
        "name": order.name,
        "item": getattr(order, "item", getattr(order, "stock_item", order_id)),
        "quantity": getattr(order, "quantity", 1),
        "total_amount": getattr(order, "total_amount", 0.0),
        "docstatus": order.docstatus,
        "tracking_status": getattr(order, "tracking_status", "Pending"),
        "courier_name": courier or "—",
        "tracking_number": getattr(order, "tracking_number", ""),
    }


@frappe.whitelist()
def update_order_tracking(order_id, status, courier_name="", tracking_number=""):
    """Only the Administrator or System Manager is permitted to advance shipment milestones."""
    user = frappe.session.user
    user_roles = frappe.get_roles(user)

    if user != "Administrator" and "System Manager" not in user_roles:
        frappe.throw(_("Access Denied: Only the Administrator can update shipping milestones."))

    allowed_statuses = ["Pending", "Approved", "Packed", "Dispatched", "Delivered", "Rejected"]
    if status not in allowed_statuses:
        frappe.throw(_("Invalid status '{0}'. Must be one of: {1}").format(status, ", ".join(allowed_statuses)))

    updates = {"tracking_status": status}

    meta = frappe.get_meta("Stock Order")
    if courier_name:
        if meta.has_field("courier_name"):
            updates["courier_name"] = courier_name
        if meta.has_field("courier_partner"):
            updates["courier_partner"] = courier_name

    if tracking_number and meta.has_field("tracking_number"):
        updates["tracking_number"] = tracking_number

    frappe.db.set_value("Stock Order", order_id, updates)
    frappe.db.commit()

    return {"status": "success", "order_id": order_id, "new_status": status}


@frappe.whitelist()
def approve_stock_order(order_id):
    user = frappe.session.user
    roles = frappe.get_roles(user)
    if user != "Administrator" and "System Manager" not in roles and "Stock Manager" not in roles and "Manager" not in roles:
        frappe.throw(_("Access Denied: You do not have permission to approve orders."))

    order = frappe.get_doc("Stock Order", order_id)
    if order.docstatus == 0:
        order.submit()  # Triggers StockOrder.on_submit() cleanly without double-deduction
    
    # Ensure tracking status is set to Approved
    frappe.db.set_value("Stock Order", order_id, "tracking_status", "Approved")
    frappe.db.commit()
    return {"message": "Order approved"}


@frappe.whitelist()
def reject_stock_order(order_id):
    user = frappe.session.user
    roles = frappe.get_roles(user)
    if user != "Administrator" and "System Manager" not in roles and "Stock Manager" not in roles and "Manager" not in roles:
        frappe.throw(_("Access Denied: You do not have permission to reject orders."))

    order = frappe.get_doc("Stock Order", order_id)
    if order.docstatus == 1:
        # Cancel submitted doc (triggers on_cancel which returns the stock)
        order.cancel()
    else:
        # Draft order: mark docstatus as cancelled and return stock
        order.docstatus = 2
        if hasattr(order, "tracking_status"):
            order.tracking_status = "Rejected"
        order.save(ignore_permissions=True)
        
        item_code = getattr(order, "item", getattr(order, "stock_item", None))
        if item_code and frappe.db.exists("Stock Item", item_code):
            current_stock = flt(frappe.db.get_value("Stock Item", item_code, "current_stock") or 0)
            frappe.db.set_value("Stock Item", item_code, "current_stock", current_stock + flt(order.quantity or 0))

    frappe.db.commit()
    return {"message": "Order rejected"}


@frappe.whitelist()
def get_agent_performance_summary():
    data = frappe.db.sql("""
        SELECT owner AS agent, COUNT(name) AS total_orders, SUM(total_amount) AS total_revenue
        FROM `tabStock Order`
        WHERE docstatus = 1
        GROUP BY owner
        ORDER BY total_revenue DESC
    """, as_dict=True)
    return data


# ==========================================
# PRODUCT CRUD
# ==========================================

@frappe.whitelist()
def create_stock_item(item_name, category="", rate=0, current_stock=0, image_url=""):
    doc = frappe.new_doc("Stock Item")
    doc.item_name = item_name
    doc.category = category
    doc.rate = flt(rate)
    doc.current_stock = flt(current_stock)
    if image_url:
        doc.image = image_url
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return doc.as_dict()


@frappe.whitelist()
def update_stock_item(item_code, rate, current_stock, category="", image_url=None):
    updates = {
        "rate": flt(rate),
        "current_stock": flt(current_stock)
    }
    if category:
        updates["category"] = category
    if image_url is not None:
        updates["image"] = image_url

    frappe.db.set_value("Stock Item", item_code, updates)
    frappe.db.commit()
    return {"message": "Updated"}


@frappe.whitelist()
def delete_stock_item(item_code):
    frappe.delete_doc("Stock Item", item_code, ignore_permissions=True)
    frappe.db.commit()
    return {"message": "Deleted"}