// Copyright (c) 2026, Frapnova and contributors
// For license information, please see license.txt

frappe.query_reports["Stock Order Summary Report"] = {
    "filters": [
        {
            "fieldname": "agent",
            "label": __("Agent"),
            "fieldtype": "Data"
        },
        {
            "fieldname": "item",
            "label": __("Item"),
            "fieldtype": "Link",
            "options": "Stock item"
        },
        {
            "fieldname": "status",
            "label": __("Status"),
            "fieldtype": "Select",
            "options": ["", "Draft", "Approved", "Rejected"]
        }
    ]
};