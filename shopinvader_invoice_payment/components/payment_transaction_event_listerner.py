# -*- coding: utf-8 -*-
# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.component.core import Component
from odoo.addons.shopinvader import shopinvader_response


class AccountInvoicePaymentTransactionEventListener(Component):
    _name = "account.invoice.payment.transaction.event.listener"
    _inherit = "base.event.listener"
    _apply_on = ["account.invoice"]

    def _confirm_and_invalidate_session(self, account_invoice):
        shopinvader_backend = account_invoice.shopinvader_backend_id
        if not shopinvader_backend:
            return
        # In case of the invoice is not already validated
        account_invoice.action_invoice_open()
        account_invoice.action_invoice_paid()
        response = shopinvader_response.get()
        response.set_session("invoice_id", 0)
        response.set_store_cache("invoice", {})
        response.set_store_cache("last_invoice_id", account_invoice.id)

    def _save_transaction_reference(self, transaction, account_invoice):
        """
        Save the transaction reference into the invoice
        :param transaction: payment.transaction recordset
        :param account_invoice: account.invoice recordset
        :return: bool
        """
        if transaction.acquirer_reference:
            return account_invoice.write(
                {"transaction_id": transaction.acquirer_reference}
            )
        return True

    def on_payment_transaction_done(self, account_invoice, transaction):
        self._confirm_and_invalidate_session(account_invoice)
        self._save_transaction_reference(transaction, account_invoice)
