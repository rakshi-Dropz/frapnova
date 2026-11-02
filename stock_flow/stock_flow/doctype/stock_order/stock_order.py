# Copyright (c) 2026, FRAPNORA and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


def get_recipient_email(user_id):
    """Resolves a valid email address even if user is 'Administrator' or using a dummy local domain."""
    if not user_id or user_id == "Administrator":
        admin_email = frappe.db.get_value("User", "Administrator", "email")
        if admin_email and "@" in admin_email and not (admin_email.endswith("@frapnora.com") or admin_email.endswith("@frapnora.local")):
            return admin_email
        return "rakshitha@dropz.in"

    if "@" in user_id:
        if user_id.endswith("@frapnora.com") or user_id.endswith("@frapnora.local"):
            return "rakshitha@dropz.in"
        return user_id

    user_email = frappe.db.get_value("User", user_id, "email")
    if user_email and "@" in user_email and not (user_email.endswith("@frapnora.com") or user_email.endswith("@frapnora.local")):
        return user_email

    return "rakshitha@dropz.in"


class StockOrder(Document):
    def validate(self):
        user_roles = frappe.get_roles()
        is_manager = (
            "Stock Manager" in user_roles 
            or "System Manager" in user_roles 
            or frappe.session.user == "Administrator"
        )

        # 1. Enforce a valid agent identifier
        if not getattr(self, "agent", None) or self.agent == "session.user":
            self.agent = frappe.session.user if frappe.session.user != "Guest" else "rakshitha@dropz.in"

        # 2. Block unauthorized manual status changes to Approved in draft mode
        if getattr(self, "status", None) == "Approved" and self.docstatus == 0 and not is_manager:
            frappe.throw("Permission denied: Only Stock Managers can approve orders.")

        # 3. Always recalculate total server-side
        if self.rate and self.quantity:
            self.total_amount = flt(self.rate) * flt(self.quantity)

    def on_submit(self):
        # 1. Update document status fields
        if hasattr(self, "status"):
            self.db_set("status", "Approved")
        if hasattr(self, "tracking_status") and not self.tracking_status:
            self.db_set("tracking_status", "Approved")

        # NOTE: Inventory deduction occurs strictly at cart checkout (api.py).
        # We do not touch Stock Item quantities here to prevent double-deduction.

        # 2. Resolve target recipient and send approval notification immediately
        recipient_user = getattr(self, "agent", None) or self.owner
        recipient_email = get_recipient_email(recipient_user)

        message = f"""
        <p>Dear <b>{recipient_user}</b>,</p>
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
                sender="FRAPNORA Notifications <rakshitha@dropz.in>",
                subject=f"Order {self.name} Approved",
                message=message,
                reference_doctype="Stock Order",
                reference_name=self.name,
                now=True  # Dispatches immediately over SMTP without requiring manual 'Send Now'
            )
        except Exception as e:
            frappe.log_error(title="Approval Email Failed", message=str(e))

    def on_cancel(self):
        # 1. Update document status fields
        if hasattr(self, "status"):
            self.db_set("status", "Rejected")
        if hasattr(self, "tracking_status"):
            self.db_set("tracking_status", "Rejected")

        # 2. Return deducted stock back to catalog upon cancellation or rejection
        item_code = getattr(self, "item", getattr(self, "stock_item", None))
        if item_code and frappe.db.exists("Stock Item", item_code):
            current_stock = flt(frappe.db.get_value("Stock Item", item_code, "current_stock") or 0)
            frappe.db.set_value("Stock Item", item_code, "current_stock", current_stock + flt(self.quantity or 0))