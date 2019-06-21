# Copyright 2018 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import stripe

from odoo import _, api, models
from odoo.addons.payment_stripe.models.payment import INT_CURRENCIES
from odoo.exceptions import MissingError
from odoo.tools.float_utils import float_round


class PaymentTransaction(models.Model):

    _inherit = "payment.transaction"

    @api.multi
    def _create_stripe_3d_secure(
            self, payment_method_id=False, payment_intent_id=False,
            version="2019-05-16"):
        self.ensure_one()
        stripe.api_key = self.acquirer_id.stripe_secret_key
        if payment_method_id:
            intent = stripe.PaymentIntent.create(
                payment_method=payment_method_id,
                amount=int(self.amount
                           if self.currency_id.name in INT_CURRENCIES
                           else float_round(self.amount * 100, 2)),
                currency=self.currency_id.name,
                confirmation_method='manual',
                confirm=True,
                stripe_version=version,
                metadata={
                    'reference': self.reference,
                }
            )
        else:
            intent = stripe.PaymentIntent.confirm(payment_intent_id)
        return intent

    @api.multi
    def _stripe_s2s_validate_tree(self, tree):
        self.ensure_one()
        status = tree.get("status")
        if status == "pending":
            new_state = "pending"
            self.write(
                {"state": new_state, "acquirer_reference": tree.get("id")}
            )
            return True
        return super()._stripe_s2s_validate_tree(tree=tree)

    # Webhook called by stripe when 3d secure is used
    @api.multi
    def _stripe_process_webhook(self, payload):
        self.ensure_one()
        api_key = self.acquirer_id.stripe_secret_key
        event = stripe.Event.construct_from(payload, api_key)
        self._stripe_process_event(event)

    @api.multi
    def _stripe_get_webhook_handler(self):
        return {
            "source.chargeable": self._stripe_process_source_chargeable,
            "source.canceled": self._stripe_process_source_canceled,
            "source.failed": self._stripe_process_source_failed,
            "charge.succeeded": self._stripe_process_charge_succeeded,
        }

    @api.multi
    def _stripe_process_event(self, event):
        handler = self._stripe_get_webhook_handler().get(event.type)
        if handler:
            handler(event)
        else:
            raise MissingError(_("Unknown Event"))

    @api.multi
    def _stripe_process_source_chargeable(self, event):
        response = self._create_stripe_charge(
            tokenid=event.data["object"]["id"]
        )
        self.env["payment.transaction"].sudo().with_context(
            lang=None
        ).form_feedback(response, "stripe")

    @api.multi
    def _stripe_process_source_failed(self, event):
        self.write({"state": "error"})

    @api.multi
    def _stripe_process_source_canceled(self, event):
        self.write({"state": "cancel"})

    @api.multi
    def _stripe_process_charge_succeeded(self, event):
        """ Dummy event received after a source.chargeable """
        # pylint: disable=unnecessary-pass
        pass
