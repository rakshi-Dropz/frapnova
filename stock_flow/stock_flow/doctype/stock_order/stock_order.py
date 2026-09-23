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

        # 1. Enforce a valid agent email (clean literal strings)
        if not self.agent or self.agent == "session.user":
            self.agent = frappe.session.user if frappe.session.user != "Guest" else "agent@example.com"

        # 2. Block unauthorized manual status changes to Approved
        if self.status == "Approved" and self.docstatus == 0 and not is_manager:
            frappe.throw("Permission denied: Only Stock Managers can approve orders.")

        # 3. Always recalculate total server-side
        if self.rate and self.quantity:
            self.total_amount = float(self.rate) * float(self.quantity)

    def on_submit(self):
        # 1. Update status
        self.status = "Approved"
        self.db_set("status", "Approved")

        # 2. Safely deduct inventory without hardcoded column assumptions
        if self.item and self.quantity:
            try:
                # Find the actual quantity field in Stock Item
                item_doc = frappe.get_doc("Stock Item", self.item)
                qty_field = None
                for candidate in ["quantity", "stock_quantity", "current_stock", "stock_qty", "available_quantity"]:
                    if hasattr(item_doc, candidate):
                        qty_field = candidate
                        break
                
                if qty_field:
                    current_val = getattr(item_doc, qty_field) or 0
                    setattr(item_doc, qty_field, max(0, int(current_val) - int(self.quantity)))
                    item_doc.save(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(title="Inventory Deduction Error", message=str(e))

        # 3. Queue the HTML approval email to the Agent
        recipient_email = self.agent or self.owner
        if recipient_email and "@" in recipient_email:
            message = f"""
            <p>Dear <b>{recipient_email}</b>,</p>
            <p>Your stock order <b>{self.name}</b> has been officially approved and processed.</p>
            <table style="width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 15px;">
              <thead>
                <tr style="background-color: #f3f4f6; text-align: left;">
                  <th style="padding: 8px; border: 1px solid #e5e7eb;">Item</th>
                  <th style="padding: 8px; border: 1px solid #e5e7eb;">Quantity</th>
                  <th style="padding: 8px; border: 1px solid #e5e7eb;">Rate</th>
                  <th style="padding: 8px; border: 1px solid #e5e7eb;">Total Amount</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td style="padding: 8px; border: 1px solid #e5e7eb;">{self.item}</td>
                  <td style="padding: 8px; border: 1px solid #e5e7eb;">{self.quantity}</td>
                  <td style="padding: 8px; border: 1px solid #e5e7eb;">₹{self.rate}</td>
                  <td style="padding: 8px; border: 1px solid #e5e7eb;">₹{self.total_amount}</td>
                </tr>
              </tbody>
            </table>
            <p>Warehouse inventory has been updated accordingly.</p>
            <p>Best regards,<br><b>Frapnova Operations Team</b></p>
            """

            frappe.sendmail(
                recipients=[recipient_email],
                subject=f"Order {self.name} Approved",
                message=message,
                reference_doctype="Stock Order",
                reference_name=self.name,
                now=False
            )

    def on_cancel(self):
        self.status = "Rejected"
        self.db_set("status", "Rejected")