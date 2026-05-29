from odoo import fields, models
import logging

_logger = logging.getLogger(__name__)


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
                _logger.info("META CAPI: orden %s ya estaba enviada", order.name)
                continue

            event_id = f'purchase_sale_order_{order.id}'

            user_data = meta._meta_build_user_data(
                partner=order.partner_id
            )

            custom_data = {
                'value': float(order.amount_total or 0.0),
                'currency': order.currency_id.name or 'MXN',
            }

            _logger.info("META CAPI: enviando Purchase para orden=%s", order.name)
            _logger.info("META CAPI: event_id=%s", event_id)
            _logger.info("META CAPI: user_data=%s", user_data)
            _logger.info("META CAPI: custom_data=%s", custom_data)

            result = meta._meta_send_event(
                event_name='Purchase',
                user_data=user_data,
                custom_data=custom_data,
                event_id=event_id,
                action_source='physical_store'
            )

            _logger.info("META CAPI: result=%s", result)

            if not result.get('error') and not result.get('skipped'):
                order.sudo().write({
                    'x_meta_purchase_sent': True,
                    'x_meta_purchase_event_id': event_id,
                })
                _logger.info("META CAPI: Purchase marcado como enviado para %s", order.name)
            else:
                _logger.warning("META CAPI: Purchase NO enviado para %s", order.name)

        return res
