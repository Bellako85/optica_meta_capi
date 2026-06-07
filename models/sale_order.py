from odoo import fields, models
from odoo.exceptions import UserError
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

    x_meta_fbp = fields.Char(copy=False)
    x_meta_fbc = fields.Char(copy=False)
    x_meta_client_ip = fields.Char(copy=False)
    x_meta_user_agent = fields.Char(copy=False)
    x_meta_event_source_url = fields.Char(copy=False)
    x_meta_order_link_opened = fields.Boolean(copy=False)
    x_meta_order_link_opened_at = fields.Datetime(copy=False)

    def _meta_get_purchase_action_source(self):
        self.ensure_one()
        return 'website' if self.x_meta_order_link_opened else 'physical_store'

    def action_send_purchase_to_meta(self):
        meta = self.env['meta.capi.mixin']

        for order in self:
            if order.x_meta_purchase_sent:
                raise UserError(f"La orden {order.name} ya fue enviada a Meta.")

            if order.state not in ('sale', 'done'):
                raise UserError(
                    f"La orden {order.name} todavía no está confirmada como venta."
                )

            has_posted_payment = bool(order.invoice_ids.filtered(
                lambda inv: inv.state == 'posted' and inv.amount_residual < inv.amount_total
            ))

            if not has_posted_payment:
                raise UserError(
                    f"La orden {order.name} no tiene pago o anticipo registrado en una factura posteada."
                )

            event_id = f'purchase_sale_order_{order.id}'

            user_data = meta._meta_build_user_data(
                partner=order.partner_id,
                fbp=order.x_meta_fbp,
                fbc=order.x_meta_fbc,
                client_ip_address=order.x_meta_client_ip,
                client_user_agent=order.x_meta_user_agent,
                external_id=order.partner_id.id,
            )

            custom_data = {
                'value': float(order.amount_total or 0.0),
                'currency': order.currency_id.name or 'MXN',
                'order_id': order.name,
            }

            action_source = order._meta_get_purchase_action_source()

            _logger.info("META CAPI: enviando Purchase manual para orden=%s", order.name)
            _logger.info("META CAPI: event_id=%s", event_id)
            _logger.info("META CAPI: user_data=%s", user_data)
            _logger.info("META CAPI: custom_data=%s", custom_data)
            _logger.info("META CAPI: action_source=%s", action_source)

            result = meta._meta_send_event(
                event_name='Purchase',
                user_data=user_data,
                custom_data=custom_data,
                event_id=event_id,
                event_source_url=order.x_meta_event_source_url or None,
                action_source=action_source,
            )

            _logger.info("META CAPI: result=%s", result)

            if not result.get('error') and not result.get('skipped'):
                order.sudo().write({
                    'x_meta_purchase_sent': True,
                    'x_meta_purchase_event_id': event_id,
                })
            else:
                raise UserError(
                    f"No se pudo enviar Purchase a Meta para {order.name}. "
                    f"Revisa logs del servidor."
                )
