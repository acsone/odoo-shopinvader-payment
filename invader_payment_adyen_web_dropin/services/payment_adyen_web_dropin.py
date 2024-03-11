# Copyright 2023 ACSONE SA/NV (http://acsone.eu).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# isort: skip_file
# Need to skip this file because conflict with black
import logging


from odoo.addons.base_rest import restapi
from odoo.addons.base_rest.components.service import (
    skip_secure_response,
    to_int,
)
from odoo.addons.component.core import AbstractComponent
from odoo.addons.invader_payment_adyen_abstract.services.payment_adyen import (
    ADYEN_TRANSACTION_STATUSES,
)


_logger = logging.getLogger(__name__)

try:
    from cerberus import Validator
except ImportError as err:
    _logger.debug(err)


class PaymentServiceAdyenWebDropin(AbstractComponent):

    _name = "payment.service.adyen_web_dropin"
    _inherit = "payment.service.adyen.abstract"
    _usage = "payment_adyen_dropin"
    _description = "REST Services for Adyen web-dropin payments"

    def paymentMethods(self, target, **params):
        """
        This is the service to provide Payment Methods depending on transaction
        details and on partner country.
        :return:
        """
        payment_mode_id = params.get("payment_mode_id")
        transaction_obj = self.env["payment.transaction"]
        payable = self.payment_service._invader_find_payable_from_target(
            target, **params
        )
        # Adyen part
        acquirer = self.env["payment.acquirer"].browse(payment_mode_id)
        transaction = transaction_obj.create(
            payable._invader_prepare_payment_transaction_data(acquirer)
        )
        response = transaction.trigger_transaction()
        return self._generate_adyen_response(
            response.message, payable, target, transaction, **params
        )

    def _validator_payments(self):
        """
        Validator of payments service
        target: see _invader_get_target_validator()
        payment_mode_id: The payment mode used to pay
        transaction_id: As the request to Adyen so not create some kind of
            transaction 'token', we must pass the transaction_id to the flow
        :return: dict
        """
        res = self.payment_service._invader_get_target_validator()
        res.update(
            {
                "payment_mode_id": {
                    "coerce": to_int,
                    "type": "integer",
                    "required": True,
                },
                "transaction_id": {
                    "coerce": to_int,
                    "type": "integer",
                    "required": True,
                },
                "payment_method": {"type": "dict", "required": True},
                "return_url": {"type": "string", "required": True},
            }
        )
        return res

    def _validator_return_payments(self):
        return Validator(
            {
                "redirect": {
                    "type": "dict",
                    "schema": {
                        "data": {"type": "dict"},
                        "url": {"type": "string"},
                        "method": {"type": "string"},
                    },
                },
                "resultCode": {"type": "string"},
                "pspReference": {"type": "string"},
                "details": {"type": "list"},
                "action": {"type": "dict"},
            },
            allow_unknown=True,
        )

    def payments(
        self,
        target,
        transaction_id,
        payment_mode_id,
        payment_method,
        return_url,
        **params
    ):
        transaction_obj = self.env["payment.transaction"]
        payable = self.payment_service._invader_find_payable_from_target(
            target, **params
        )

        acquirer = self.env["payment.acquirer"].browse(payment_mode_id)
        self.payment_service._check_provider(acquirer, "adyen")

        transaction = transaction_obj.browse(transaction_id)
        transaction.return_url = return_url
        request = self._prepare_adyen_payments_request(
            transaction, payment_method
        )
        adyen = self._get_service(transaction)
        response = adyen.checkout.payments(request)
        self._update_transaction_with_response(transaction, response)
        result_code = response.message.get("resultCode")
        if result_code == "Authorised":
            transaction._set_transaction_done()
        else:
            transaction.write(
                {"state": ADYEN_TRANSACTION_STATUSES[result_code]}
            )

        return self._generate_adyen_response(
            response.message, payable, target, transaction, **params
        )

    def _prepare_adyen_payments_request(self, transaction, payment_method):
        """
        https://docs.adyen.com/checkout/drop-in-web#step-3-make-a-payment
        Prepare payments request
        :param transaction:
        :param payment_method:
        :return:
        """
        return transaction._prepare_adyen_payments_request(payment_method)

    def _validator_paymentResult(self):
        schema = {
            "transaction_id": {
                "coerce": to_int,
                "type": "integer",
                "required": True,
            },
            "success_redirect": {"type": "string"},
            "cancel_redirect": {"type": "string"},
        }
        return Validator(schema, allow_unknown=True)

    def _validator_return_paymentResult(self):
        schema = {"redirect_to": {"type": "string"}}
        return Validator(schema, allow_unknown=True)

    @restapi.method(
        [(["/paymentResult"], ["GET", "POST"])],
        input_param=restapi.CerberusValidator("_validator_paymentResult"),
        output_param=restapi.CerberusValidator(
            "_validator_return_paymentResult"
        ),
    )
    def paymentResult(self, **params):
        transaction = self.env["payment.transaction"].browse(
            params.get("transaction_id")
        )
        # Response will be an AdyenResult object
        adyen = self._get_service(transaction)
        request = self._prepare_payment_details(transaction, **params)
        response = adyen.checkout.payments_details(request)
        self._update_transaction_with_response(transaction, response)
        result_code = response.message.get("resultCode")
        return_url = params.get("success_redirect")
        notify = False
        if result_code == "Authorised":
            if transaction.state == "draft":
                transaction._set_transaction_done()
            else:
                notify = True
        elif result_code in ("Cancelled", "Refused"):
            return_url = params.get("cancel_redirect")
            transaction.write(
                {"state": ADYEN_TRANSACTION_STATUSES[result_code]}
            )
        else:
            transaction.write(
                {"state": ADYEN_TRANSACTION_STATUSES[result_code]}
            )

        if notify:
            # Payment state has been changed through another process
            # (e.g. webhook). So, do the stuff for shopinvader_session
            transaction._notify_state_changed_event()
        res = {}
        res["redirect_to"] = return_url
        return res

    def _validator_webhook(self):
        schema = {
            "notificationItems": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "NotificationRequestItem": {
                            "type": "dict",
                            "schema": {"additionalData": {"type": "dict"}},
                        }
                    },
                },
            },
        }
        return Validator(schema, allow_unknown=True)

    def _validator_return_webhook(self):
        """
        Returns nothing
        :return:
        """
        return Validator({}, allow_unknown=True)

    @skip_secure_response
    @restapi.method(
        [(["/webhook"], ["GET", "POST"])],
        input_param=restapi.CerberusValidator("_validator_webhook"),
        output_param=restapi.CerberusValidator("_validator_return_webhook"),
    )
    def webhook(self, **params):
        """
        Implement the webhook notification.
        See: https://docs.adyen.com/development-resources/notifications
        Example of webhook for a successful payment:
        {
          "live": "false",
          "notificationItems":[
            {
              "NotificationRequestItem":{
                "eventCode":"AUTHORISATION",
                "merchantAccountCode":"YOUR_MERCHANT_ACCOUNT",
                "reason":"033899:1111:03/2030",
                "amount":{
                  "currency":"EUR",
                  "value":2500
                },
                "operations":["CANCEL","CAPTURE","REFUND"],
                "success":"true",
                "paymentMethod":"mc",
                "additionalData":{
                  "expiryDate":"03/2030",
                  "authCode":"033899",
                  "cardBin":"411111",
                  "cardSummary":"1111",
                  "checkoutSessionId":"CSF46729982237A879"
                },
                "merchantReference":"YOUR_REFERENCE",
                "pspReference":"NC6HT9CRT65ZGN82",
                "eventDate":"2021-09-13T14:10:22+02:00"
              }
            }
          ]
        }

        And an unsuccessful payment:
        {
          "live": "false",
          "notificationItems":[
            {
              "NotificationRequestItem":{
                "eventCode":"AUTHORISATION",
                "merchantAccountCode":"YOUR_MERCHANT_ACCOUNT",
                "reason":"validation 101 Invalid card number",
                "amount":{
                  "currency":"EUR",
                  "value":2500
                },
                "success":"false",
                "paymentMethod":"unknowncard",
                "additionalData":{
                  "expiryDate":"03/2030",
                  "cardBin":"411111",
                  "cardSummary":"1112",
                  "checkoutSessionId":"861631540104159H"
                },
                "merchantReference":"YOUR_REFERENCE",
                "pspReference":"KHQC5N7G84BLNK43",
                "eventDate":"2021-09-13T14:14:05+02:00"
              }
            }
          ]
        }
        :param transaction_id: int (optional)
        :param params:
        :return: str
        """
        # In case of exception, Adyen recommends to not return anything
        try:
            return self.env["payment.transaction"].manage_adyen_dropin_webhook(
                params, queue_job=True
            )
        except Exception:
            return ""
