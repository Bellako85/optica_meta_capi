from odoo import models
from odoo.http import request


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super().action_confirm()

        meta = self.env['meta.capi.mixin']

        for order in self:

            partner = order.partner_id

            user_data = meta._meta_build_user_data(
                partner=partner,
                request_obj=request if request else None
            )

            custom_data = {
                'value': float(order.amount_total),
                'currency': order.currency_id.name or 'MXN',
                'content_name': order.name,
            }

            event_id = f'purchase_sale_order_{order.id}'

            meta._meta_send_event(
                event_name='Purchase',
                user_data=user_data,
                custom_data=custom_data,
                event_id=event_id,
                action_source='website'
            )

        return res
