# Copyright (c) 2026, Frapnova and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {
            "fieldname": "order_id",
            "label": _("Order ID"),
            "fieldtype": "Link",
            "options": "Stock Order",
            "width": 140
        },
        {
            "fieldname": "agent",
            "label": _("Agent"),
            "fieldtype": "Data",
            "width": 160
        },
        {
            "fieldname": "item",
            "label": _("Item"),
            "fieldtype": "Link",
            "options": "Stock item",
            "width": 150
        },
        {
            "fieldname": "quantity",
            "label": _("Quantity"),
            "fieldtype": "Float",
            "width": 100
        },
        {
            "fieldname": "rate",
            "label": _("Rate (₹)"),
            "fieldtype": "Currency",
            "options": "currency",
            "width": 120
        },
        {
            "fieldname": "total_amount",
            "label": _("Total Amount (₹)"),
            "fieldtype": "Currency",
            "options": "currency",
            "width": 140
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 110
        },
        {
            "fieldname": "creation",
            "label": _("Date Created"),
            "fieldtype": "Datetime",
            "width": 160
        }
    ]

def get_data(filters):
    conditions = ""
    values = {}

    if filters:
        if filters.get("agent"):
            conditions += " AND (agent = %(agent)s OR owner = %(agent)s)"
            values["agent"] = filters.get("agent")
        if filters.get("status"):
            conditions += " AND status = %(status)s"
            values["status"] = filters.get("status")
        if filters.get("item"):
            conditions += " AND item = %(item)s"
            values["item"] = filters.get("item")

    query = f"""
        SELECT 
            name AS order_id,
            COALESCE(agent, owner) AS agent,
            item,
            quantity,
            rate,
            total_amount,
            status,
            creation
        FROM `tabStock Order`
        WHERE 1=1 {conditions}
        ORDER BY creation DESC
    """

    return frappe.db.sql(query, values, as_dict=True)