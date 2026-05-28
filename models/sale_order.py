from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    x_meta_purchase_sent = fields.Boolean(
        string='Meta Purchase Sent',
        copy=False,
        readonly=True
    )

    x_meta_purchase_event_id = fields.Char(
        string='Meta Purchase Event ID',
        copy=False,
        readonly=True
    )

    def action_confirm(self):
        res = super().action_confirm()

        meta = self.env['meta.capi.mixin']

        for order in self:
            if order.x_meta_purchase_sent:
                continue

            event_id = f'purchase_sale_order_{order.id}'

            full_name = order.partner_id.name or ''
            name_parts = full_name.strip().split(' ', 1)
            first_name = name_parts[0] if name_parts and name_parts[0] else ''
            last_name = name_parts[1] if len(name_parts) > 1 else ''

            user_data = meta._meta_build_user_data(
                partner=order.partner_id,
                first_name=first_name,
                last_name=last_name,
            )

            custom_data = {
                'value': float(order.amount_total),
                'currency': order.currency_id.name or 'MXN',
                'content_name': order.name,
                'delivery_category': 'in_store',
            }

            result = meta._meta_send_event(
                event_name='Purchase',
                user_data=user_data,
                custom_data=custom_data,
                event_id=event_id,
                action_source='physical_store'
            )

            if not result.get('error') and not result.get('skipped'):
                order.sudo().write({
                    'x_meta_purchase_sent': True,
                    'x_meta_purchase_event_id': event_id,
                })

        return res
