# Copyright (c) 2026, Rakshi and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class StockOrder(Document):
	pass
import frappe
from frappe.model.document import Document

class StockOrder(Document):
    def on_submit(self):
        self.status = "Submitted"
        self.db_set("status", "Submitted")

    def on_cancel(self):
        self.status = "Cancelled"
        self.db_set("status", "Cancelled")