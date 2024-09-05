# Copyright 2019 ACSONE SA/NV (http://acsone.eu).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.component.core import AbstractComponent

import stripe

class PaymentServiceStripe(AbstractComponent):

    _inherit = "payment.service.stripe"

    def _get_chargeable_provider(self):
        """
        Overwrite to add providers which use the charge api
        :return: list of str
        """
        res = super()._get_chargeable_provider()
        res.append("stripe_bancontact")
        return res

    def _get_front_end_base_url(self):
        return ""

    def _prepare_stripe_intent(self, transaction, stripe_payment_method_id):
        """
        Prepare a StripeIntent with payment.transaction data
        :param tx_data:
        :param stripe_payment_method_id:
        :return: StripeIntent
        """
        if transaction.acquirer_id.provider != "stripe_bancontact":
            return super()._prepare_stripe_intent(transaction, stripe_payment_method_id)
        metadata = {"reference": transaction.reference}
        return_url = ("{base_url}/payment-redirect?"
                      "stripe_payment_method_id={stripe_payment_method_id}"
                      "&acquirer_id={acquirer_id}"
                      "&publishable_key={publishable_key}"
                      "&target={target}"
                      "&type={type}").format(
            base_url=self._get_front_end_base_url(),
            stripe_payment_method_id=stripe_payment_method_id,
            acquirer_id=transaction.acquirer_id.id,
            publishable_key=transaction.acquirer_id.stripe_publishable_key,
            target=transaction.membership_ids[0].id,
            type="membership",
        )
        currency = transaction.currency_id
        intent = stripe.PaymentIntent.create(
            payment_method=stripe_payment_method_id,
            amount=self._get_formatted_amount(currency, transaction.amount),
            currency="EUR",
            confirmation_method="manual",
            confirm=True,
            description=transaction.reference,
            metadata=metadata,
            api_key=self._get_stripe_private_key(transaction),
            payment_method_types=["bancontact"],
            return_url=return_url,
        )
        return intent

    def _generate_stripe_response(self, intent, payable, target, **params):
        """
        This is the message returned to client
        :param intent: StripeIntent (None means error)
        :param payable: invader.payable record
        :return: dict
        """
        if intent:
            if (
                    intent.status == "requires_action"
                    and intent.next_action.type == "redirect_to_url"
            ):
                # Tell the client to handle the action
                return {
                    "requires_action": True,
                    "url": intent.next_action.redirect_to_url.url,
                    "return_url": intent.next_action.redirect_to_url.return_url,
                }
        return  super()._generate_stripe_response(intent, payable, target, **params)
