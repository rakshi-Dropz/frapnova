// Copyright (c) 2026, Rakshi and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Stock Order", {
// 	refresh(frm) {

// 	},
// });
frappe.ui.form.on('Stock Order', {
    refresh: function(frm) {
        if (frm.doc.docstatus === 0 && frappe.user_roles.includes("Stock Manager")) {
            frm.add_custom_button(__('Approve Order'), function() {
                frappe.call({
                    method: 'stock_flow.api.approve_stock_order',
                    args: { order_id: frm.doc.name },
                    callback: function(r) {
                        if (!r.exc) {
                            frappe.msgprint(__('Order approved successfully.'));
                            frm.reload_doc();
                        }
                    }
                });
            }).addClass('btn-success');
        }
    },

    quantity: function(frm) {
        if (frm.doc.quantity && frm.doc.rate) {
            frm.set_value('total_amount', frm.doc.quantity * frm.doc.rate);
        }
    }
});