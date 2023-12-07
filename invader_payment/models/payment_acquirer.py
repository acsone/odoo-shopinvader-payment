# Copyright 2024 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class PaymentAcquirer(models.Model):
    _inherit = "payment.acquirer"

    return_url_suffix = fields.Char()
