// Copyright (c) 2026, Frapnova and contributors
// For license information, please see license.txt

frappe.ui.form.on('Stock Order', {
    onload: function(frm) {
        // Set agent automatically on new records
        if (frm.is_new() && !frm.doc.agent) {
            frm.set_value('agent', frappe.session.user);
        }
    },

    refresh: function(frm) {
        // 1. Force fields to be Read-Only in Desk UI
        frm.set_df_property('status', 'read_only', 1);
        frm.set_df_property('agent', 'read_only', 1);
        frm.set_df_property('total_amount', 'read_only', 1);

        // 2. Role-based workflow buttons for Stock Managers & Admins on Draft orders
        let is_manager = frappe.user_roles.includes("Stock Manager") || 
                         frappe.user_roles.includes("System Manager") || 
                         frappe.session.user === "Administrator";

        if (frm.doc.docstatus === 0 && !frm.is_new() && is_manager) {
            // Approve Button
            frm.add_custom_button(__('Approve Order'), function() {
                frappe.confirm(__('Approve and submit this order? Stock will be deducted.'), function() {
                    frappe.call({
                        method: 'stock_flow.api.approve_stock_order',
                        args: { order_id: frm.doc.name },
                        freeze: true,
                        freeze_message: __('Approving order...'),
                        callback: function(r) {
                            if (!r.exc) {
                                frappe.show_alert({
                                    message: __('Order approved successfully!'),
                                    indicator: 'green'
                                }, 4);
                                frm.reload_doc();
                            }
                        }
                    });
                });
            }).addClass('btn-success');

            // Reject Button
            frm.add_custom_button(__('Reject Order'), function() {
                frappe.confirm(__('Are you sure you want to reject this order?'), function() {
                    frappe.call({
                        method: 'stock_flow.api.reject_stock_order',
                        args: { order_id: frm.doc.name },
                        freeze: true,
                        freeze_message: __('Rejecting order...'),
                        callback: function(r) {
                            if (!r.exc) {
                                frappe.show_alert({
                                    message: __('Order rejected.'),
                                    indicator: 'red'
                                }, 4);
                                frm.reload_doc();
                            }
                        }
                    });
                });
            }).addClass('btn-danger');
        }

        // 3. Desk Intro Banner based on document state
        if (frm.doc.docstatus === 0 && !frm.is_new()) {
            frm.set_intro(__('Draft Order: Awaiting approval by Stock Manager.'), 'orange');
        } else if (frm.doc.docstatus === 1) {
            frm.set_intro(__('Submitted: Approved and stock deducted.'), 'green');
        } else if (frm.doc.docstatus === 2) {
            frm.set_intro(__('Cancelled / Rejected.'), 'red');
        }
    },

    item: function(frm) {
        // 4. Auto-populate rate, image, and available stock when Item is selected
        if (frm.doc.item) {
            frappe.db.get_value('Stock Item', frm.doc.item, ['rate', 'image', 'current_stock'])
                .then(r => {
                    let data = r.message;
                    if (data) {
                        frm.set_value('rate', flt(data.rate));
                        
                        if (data.image) {
                            frm.set_value('item_image', data.image);
                        }

                        // Set default quantity if blank
                        if (!frm.doc.quantity || frm.doc.quantity <= 0) {
                            frm.set_value('quantity', 1);
                        }

                        calculate_total(frm);

                        // Real-time Desk warning if stock is low
                        if (flt(data.current_stock) <= 5) {
                            frappe.show_alert({
                                message: __('Notice: Only {0} unit(s) remaining for this item.', [data.current_stock]),
                                indicator: 'orange'
                            }, 5);
                        }
                    }
                });
        }
    },

    quantity: function(frm) {
        if (frm.doc.quantity <= 0) {
            frappe.msgprint(__('Quantity must be greater than zero.'));
            frm.set_value('quantity', 1);
        }
        calculate_total(frm);
    },

    rate: function(frm) {
        calculate_total(frm);
    },

    validate: function(frm) {
        if (!frm.doc.quantity || flt(frm.doc.quantity) <= 0) {
            frappe.throw(__('Quantity must be at least 1.'));
        }
    }
});

function calculate_total(frm) {
    let rate = flt(frm.doc.rate);
    let qty = flt(frm.doc.quantity);
    frm.set_value('total_amount', rate * qty);
}