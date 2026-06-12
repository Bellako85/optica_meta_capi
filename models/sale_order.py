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

    def action_send_purchase_to_meta(self, event_name='Purchase'):
        """
        Envía eventos a la Conversions API de Meta.
        Por defecto actúa como 'Purchase' para no romper compatibilidad,
        pero permite pasarle cualquier evento de manera dinámica (ej. 'InitiateCheckout').
        """
        meta = self.env['meta.capi.mixin']

        for order in self:
            # --- VALIDACIONES EXCLUSIVAS PARA COMPRAS ---
            if event_name == 'Purchase':
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

            # --- CONSTRUCCIÓN DINÁMICA DEL EVENT ID ---
            # Evita que el ID colisione si mandas más de un evento diferente para la misma orden.
            event_id = f'{event_name.lower()}_sale_order_{order.id}'

            # --- RECOPILACIÓN Y LIMPIEZA DE DATOS DEL CLIENTE ---
            raw_phone = order.partner_id.phone or order.partner_id.mobile or ''
            clean_phone = ''.join(c for c in raw_phone if c.isdigit())

            user_data = meta._meta_build_user_data(
                partner=order.partner_id,
                fbp=order.x_meta_fbp,
                fbc=order.x_meta_fbc,
                client_ip_address=order.x_meta_client_ip,
                client_user_agent=order.x_meta_user_agent,
                external_id=str(order.partner_id.id),
            )
            
            # --- DATOS DEL VALOR DE LA ORDEN ---
            custom_data = {
                'value': float(order.amount_total or 0.0),
                'currency': order.currency_id.name or 'MXN',
                'order_id': order.name,
            }

            action_source = order._meta_get_purchase_action_source()

            # --- LOGS DE CONTROL ---
            _logger.info("META CAPI: enviando evento %s para orden=%s", event_name, order.name)
            _logger.info("META CAPI: event_id=%s", event_id)
            _logger.info("META CAPI: user_data=%s", user_data)
            _logger.info("META CAPI: custom_data=%s", custom_data)
            _logger.info("META CAPI: action_source=%s", action_source)

            # --- ENVÍO DEL EVENTO A META ---
            result = meta._meta_send_event(
                event_name=event_name,  # Totalmente dinámico
                user_data=user_data,
                custom_data=custom_data,
                event_id=event_id,
                event_source_url=order.x_meta_event_source_url or None,
                action_source=action_source,
            )

            _logger.info("META CAPI: result=%s", result)

            # --- MANEJO DE RESPUESTA ---
            if not result.get('error') and not result.get('skipped'):
                # Solo si el evento fue una compra, guardamos el estado en la base de datos de Odoo
                if event_name == 'Purchase':
                    order.sudo().write({
                        'x_meta_purchase_sent': True,
                        'x_meta_purchase_event_id': event_id,
                    })
            else:
                raise UserError(
                    f"No se pudo enviar el evento {event_name} a Meta para {order.name}. "
                    f"Revisa los logs del servidor."
                )
