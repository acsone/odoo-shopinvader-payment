# -*- coding: utf-8 -*-
# Copyright 2019 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, models


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    @api.multi
    def _get_invader_payables(self):
        """
        Inherit to return invoices to pay
        :return: recordset
        """
        self.ensure_one()
        if self.invoice_ids:
            return self.invoice_ids.filtered(lambda i: i.state != "paid")
        return super(PaymentTransaction, self)._get_invader_payables()
