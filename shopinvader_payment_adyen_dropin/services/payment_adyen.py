# Copyright 2019 ACSONE SA/NV (http://acsone.eu).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component


class PaymentServiceAdyenShopinvader(Component):

    # expose Adyen payment service under /shopinvader

    _name = "payment.service.adyen.dropin.shopinvader"
    _inherit = ["payment.service.adyen_web_dropin", "base.shopinvader.service"]
    _usage = "payment_adyen_dropin"
    _collection = "shopinvader.backend"

    def _get_shopinvader_session(self):
        # HTTP_SESS are data that are store in the shopinvader session
        # and forwarded to odoo at each request
        # it allow to access to some specific field of the user session
        # By security always force typing
        # Note: rails cookies store session are serveless ;)
        return {
            "cart_id": int(
                self.request.httprequest.environ.get("HTTP_SESS_CART_ID", 0)
            )
        }
