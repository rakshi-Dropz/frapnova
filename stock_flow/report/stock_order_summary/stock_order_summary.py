import frappe

def execute(filters=None):
    columns = [
        {"fieldname": "item", "label": "Item Code", "fieldtype": "Link", "options": "Stock Item", "width": 180},
        {"fieldname": "total_orders", "label": "Total Orders Placed", "fieldtype": "Int", "width": 150},
        {"fieldname": "total_qty", "label": "Total Units Ordered", "fieldtype": "Float", "width": 150},
        {"fieldname": "total_revenue", "label": "Total Value (₹)", "fieldtype": "Currency", "width": 150}
    ]

    data = frappe.db.sql("""
        SELECT 
            item,
            COUNT(name) as total_orders,
            SUM(quantity) as total_qty,
            SUM(total_amount) as total_revenue
        FROM `tabStock Order`
        WHERE docstatus = 1
        GROUP BY item
        ORDER BY total_revenue DESC
    """, as_dict=True)

    return columns, data