# Copyright 2019 ACSONE SA/NV (http://acsone.eu).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)
try:
    pass
except ImportError as err:
    _logger.debug(err)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    adyen_payment_data = fields.Char(groups="base.group_user")
    adyen_payment_method = fields.Char()

    def _get_formatted_amount(self, force_amount=False):
        """
        The expected amount format by Adyen
        :param transaction: payment.transaction
        :param amount: float
        :return: int
        """
        value = super()._get_formatted_amount(force_amount=force_amount)
        if "adyen" in self.acquirer_id.provider:
            value = int(value * 100)
        return value

    def _prepare_adyen_session(self):
        """
        https://docs.adyen.com/checkout/drop-in-web#step-3-make-a-payment
        Prepare payments request
        :return:
        """
        self.ensure_one()
        partner = self.partner_id
        lang = partner.lang or self.env.lang or "en_US"
        request = {
            "merchantAccount": self._get_adyen_dropin_merchant_account(),
            "amount": {
                "value": self._get_formatted_amount(),
                "currency": self.currency_id.name,
            },
            "returnUrl": self.return_url,
            "reference": self.reference,
            "countryCode": partner.country_id.code,
        }
        if lang:
            request.update({"shopperLocale": lang})
        if partner.email:
            request.update({"shopperEmail": partner.email})
        return request
