# Copyright (c) 2026, Frapnova and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

class StockOrder(Document):
    def validate(self):
        user_roles = frappe.get_roles()
        is_manager = (
            "Stock Manager" in user_roles 
            or "System Manager" in user_roles 
            or frappe.session.user == "Administrator"
        )

        # 1. Enforce a valid agent email
        if not getattr(self, "agent", None) or self.agent == "session.user":
            self.agent = frappe.session.user if frappe.session.user != "Guest" else "agent@example.com"

        # 2. Block unauthorized manual status changes to Approved in draft mode
        if getattr(self, "status", None) == "Approved" and self.docstatus == 0 and not is_manager:
            frappe.throw("Permission denied: Only Stock Managers can approve orders.")

        # 3. Always recalculate total server-side
        if self.rate and self.quantity:
            self.total_amount = flt(self.rate) * flt(self.quantity)

    def on_submit(self):
        # 1. Update status fields
        if hasattr(self, "status"):
            self.db_set("status", "Approved")
        if hasattr(self, "tracking_status") and not self.tracking_status:
            self.db_set("tracking_status", "Approved")

        # NOTE: Inventory is already deducted when the agent checks out the cart.
        # DO NOT deduct stock here to prevent double deduction!

        # 2. Queue the HTML approval email to the Agent
        recipient_email = getattr(self, "agent", None) or self.owner
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
                  <td style="padding: 8px; border: 1px solid #e5e7eb;">₹{self.rate:,.2f}</td>
                  <td style="padding: 8px; border: 1px solid #e5e7eb;">₹{self.total_amount:,.2f}</td>
                </tr>
              </tbody>
            </table>
            <p>Best regards,<br><b>FRAPNORA Operations Team</b></p>
            """

            try:
                frappe.sendmail(
                    recipients=[recipient_email],
                    subject=f"Order {self.name} Approved",
                    message=message,
                    reference_doctype="Stock Order",
                    reference_name=self.name,
                    now=False
                )
            except Exception as e:
                frappe.log_error(title="Approval Email Failed", message=str(e))

    def on_cancel(self):
        # 1. Update status
        if hasattr(self, "status"):
            self.db_set("status", "Rejected")
        if hasattr(self, "tracking_status"):
            self.db_set("tracking_status", "Rejected")

        # 2. Return deducted stock back to the catalog if cancelled/rejected
        item_code = getattr(self, "item", getattr(self, "stock_item", None))
        if item_code and frappe.db.exists("Stock Item", item_code):
            current_stock = flt(frappe.db.get_value("Stock Item", item_code, "current_stock") or 0)
            frappe.db.set_value("Stock Item", item_code, "current_stock", current_stock + flt(self.quantity or 0))