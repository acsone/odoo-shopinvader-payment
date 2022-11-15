# Copyright 2019 ACSONE SA/NV (http://acsone.eu).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo.fields import first

from odoo.addons.component.core import AbstractComponent

_logger = logging.getLogger(__name__)


class PaymentServiceAdyen(AbstractComponent):
    _inherit = "payment.service.adyen"

    def _klarna_partner_info(self, partner):
        return {
            "city": partner.city,
            "country": partner.country_id.code,
            "houseNumberOrName": "",
            "postalCode": partner.zip,
            "street": partner.street,
        }

    def _klarna_company_info(self, record):
        company = self.env.company
        if hasattr(record, "company_id") and record.company_id:
            company = record.company_id
        lang = company.partner_id.lang or self.env.lang or "en_US"
        if hasattr(record, "partner_id") and record.partner_id:
            lang = record.partner_id.lang
        values = {
            "shopperLocale": lang,
            "shopperEmail": company.email,
            "shopperName": {
                "firstName": company.display_name,
            },
        }
        if company.phone:
            values.update({"telephoneNumber": company.phone})
        return values

    def _prepare_adyen_payment_adyen_klarna_sale_order_line(
        self, transaction, payment_method, line
    ):
        currency = transaction.currency_id
        return {
            "id": line.id,
            "quantity": line.product_uom_qty,
            "taxPercentage": self._get_formatted_amount(currency, line.tax_id.amount),
            "description": line.display_name,
            "amountIncludingTax": self._get_formatted_amount(
                currency, line.price_total
            ),
        }

    def _prepare_adyen_payment_adyen_klarna_sale_order(
        self, transaction, payment_method
    ):
        sale = first(transaction.sale_order_ids)
        request = self._klarna_company_info(sale)
        request.update(
            {
                "shopperReference": sale.reference or sale.name,
                "billingAddress": self._klarna_partner_info(
                    sale.partner_invoice_id or sale.partner_id
                ),
                "deliveryAddress": self._klarna_partner_info(
                    sale.partner_shipping_id or sale.partner_id
                ),
                "lineItems": [
                    self._prepare_adyen_payment_adyen_klarna_sale_order_line(
                        transaction, payment_method, line
                    )
                    for line in sale.order_line
                ],
            }
        )
        return request

    def _prepare_adyen_payment_adyen_klarna_invoice_line(
        self, transaction, payment_method, line
    ):
        currency = transaction.currency_id
        return {
            "id": line.id,
            "quantity": line.quantity,
            "taxPercentage": self._get_formatted_amount(
                currency, first(line.tax_ids).amount
            ),
            "description": line.display_name,
            "amountIncludingTax": self._get_formatted_amount(
                currency, line.price_total
            ),
        }

    def _prepare_adyen_payment_adyen_klarna_invoice(self, transaction, payment_method):
        invoice = first(transaction.invoice_ids)
        request = self._klarna_company_info(invoice)
        request.update(
            {
                "shopperReference": invoice.ref or invoice.name,
                "billingAddress": self._klarna_partner_info(invoice.partner_id),
                "deliveryAddress": self._klarna_partner_info(
                    invoice.partner_shipping_id or invoice.partner_id
                ),
                "lineItems": [
                    self._prepare_adyen_payment_adyen_klarna_invoice_line(
                        transaction, payment_method, line
                    )
                    for line in invoice.invoice_line_ids
                ],
            }
        )
        return request

    def _prepare_adyen_payments_request(self, transaction, payment_method):
        """
        https://docs.adyen.com/checkout/drop-in-web#step-3-make-a-payment
        Prepare payments request
        :param transaction:
        :param payment_method:
        :return:
        """
        request = super()._prepare_adyen_payments_request(
            transaction=transaction, payment_method=payment_method
        )
        if "klarna" in payment_method.get("type", ""):
            if transaction.sale_order_ids:
                request.update(
                    self._prepare_adyen_payment_adyen_klarna_sale_order(
                        transaction, payment_method
                    )
                )
            elif transaction.invoice_ids:
                request.update(
                    self._prepare_adyen_payment_adyen_klarna_invoice(
                        transaction, payment_method
                    )
                )
        return request
