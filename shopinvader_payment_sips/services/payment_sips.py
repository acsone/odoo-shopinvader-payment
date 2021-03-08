# Copyright 2019 ACSONE SA/NV (http://acsone.eu).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component
from odoo.addons.invader_payment_sips.services.payment_sips import _sips_parse_data
from odoo.addons.shopinvader import shopinvader_response


class PaymentServiceSipsShopinvader(Component):

    # expose SIPS payment service under /shopinvader

    _name = "payment.service.sips.shopinvader"
    _inherit = ["payment.service.sips", "base.shopinvader.service"]
    _usage = "payment_sips"
    _collection = "shopinvader.backend"

    def normal_return(
        self, target, success_redirect, cancel_redirect, **params
    ):
        """We override normal_return to set last_sale in store_cache.

        This is normally done in sale.order.payment.transaction.event.listener,
        but in some weird cases, normal_return is called without the sess-cart-id
        http header. This is probably not fixing the root cause but it's the
        best I have found for now...
        """
        res = super().normal_return(target, success_redirect, cancel_redirect, **params)
        data_o = _sips_parse_data(params.get("Data"))  # seal was validated in super()
        transaction = self.env["payment.transaction"].search(
            [("reference", "=", data_o.get("transactionReference"))]
        )
        assert transaction  # was validated in super()
        response = shopinvader_response.get(raise_if_not_found=False)
        if response and transaction.state == "done":
            payables = transaction._get_invader_payables()
            if len(payables) == 1 and payables[0]._name == "sale.order":
                last_sale = self.component(usage="cart")._to_json(payables[0])
                response.set_session("cart_id", 0)
                response.set_store_cache("cart", {})
                response.set_store_cache("last_sale", last_sale.get("data", {}))

        return res
