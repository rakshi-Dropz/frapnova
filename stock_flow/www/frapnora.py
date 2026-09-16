import frappe

def get_context(context):
    context.no_cache = 1
    
    user = frappe.session.user
    context.is_guest = (user == "Guest")
    
    if not context.is_guest:
        user_roles = frappe.get_roles(user)
        
        context.is_admin = "System Manager" in user_roles
        context.is_checker = "Stock Manager" in user_roles and not context.is_admin
        context.is_maker = "Support Agent" in user_roles and not context.is_admin
        
        context.user_fullname = frappe.utils.get_fullname(user)
        context.user_email = user
        
        # Querying Stock Order (matching your DocType)
        if context.is_checker:
            context.pending_entries = frappe.get_all(
                "Stock Order",
                filters={"docstatus": 0},
                fields=["name", "owner", "creation"]
            )
            context.approved_entries = frappe.get_all(
                "Stock Order",
                filters={"docstatus": 1},
                fields=["name", "owner", "creation"]
            )
        elif context.is_maker:
            context.my_entries = frappe.get_all(
                "Stock Order",
                filters={"owner": user},
                fields=["name", "docstatus", "creation"]
            )
            
    return context