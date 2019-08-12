# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.component.core import Component


class InvaderPaymentService(Component):

    _inherit = "invader.payment.service"

    def _invader_find_payable_from_target(self, target, **params):
        if target == "current_cart":
            return self.component(usage="cart")._get()
        return super()._invader_find_payable_from_target(target, **params)

    def _invader_find_payable_from_transaction(self, transaction):
        if transaction.sale_order_ids:
            return transaction.sale_order_ids
        return super()._invader_find_payable_from_transaction(transaction)

    def _invader_get_target_validator(self):
        res = super()._invader_get_target_validator()
        res["target"]["allowed"].append("current_cart")
        return res

    def _invader_payment_start(self, payable, transaction, payment_mode_id):
        res = super()._invader_payment_start(
            payable, transaction, payment_mode_id
        )
        if payable._model == "sale.order":
            payable.write({"payment_mode_id": payment_mode_id.id})
        return res

    def _invader_payment_success(self, payable, transaction):
        res = super()._invader_payment_success(payable, transaction)
        if payable._model == "sale.order":
            self.component(usage="cart")._confirm_cart(payable)
        return res
