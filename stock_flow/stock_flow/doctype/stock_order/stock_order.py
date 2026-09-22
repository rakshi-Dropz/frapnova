# Copyright (c) 2026, Frapnova and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class StockOrder(Document):
    def validate(self):
        user_roles = frappe.get_roles()
        is_manager = (
            "Stock Manager" in user_roles 
            or "System Manager" in user_roles 
            or frappe.session.user == "Administrator"
        )

        # 1. Enforce default agent if empty
        if not self.agent:
            self.agent = frappe.session.user

        # 2. Block unauthorized manual status changes to Approved
        if self.status == "Approved" and self.docstatus == 0 and not is_manager:
            frappe.throw("Permission denied: Only Stock Managers can approve orders.")

        # 3. Always recalculate total server-side for integrity
        if self.rate and self.quantity:
            self.total_amount = float(self.rate) * float(self.quantity)

    def on_submit(self):
        self.status = "Approved"
        self.db_set("status", "Approved")

    def on_cancel(self):
        self.status = "Rejected"
        self.db_set("status", "Rejected")