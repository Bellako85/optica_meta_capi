from odoo import fields, models
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class OpticaAppointment(models.Model):
    _inherit = "optica.appointment"

    x_meta_schedule_sent = fields.Boolean(
        string="Meta Schedule Sent",
        copy=False,
        readonly=True,
    )

    x_meta_schedule_event_id = fields.Char(
        string="Meta Schedule Event ID",
        copy=False,
        readonly=True,
    )

    x_meta_fbp = fields.Char(
        string="Meta FBP",
        copy=False,
        readonly=True,
    )

    x_meta_fbc = fields.Char(
        string="Meta FBC",
        copy=False,
        readonly=True,
    )

    x_meta_client_ip = fields.Char(
        string="IP del cliente",
        copy=False,
        readonly=True,
    )

    x_meta_user_agent = fields.Char(
        string="Agente de usuario",
        copy=False,
        readonly=True,
    )

    def action_send_schedule_to_meta(self):
        meta = self.env["meta.capi.mixin"]

        for appointment in self:

            # Evitar enviar eventos de citas creadas en el sitio web.
            if appointment.appointment_origin != "backend":
                raise UserError(
                    "Esta cita proviene del sitio web. "
                    "El evento Schedule se registra desde la página de gracias."
                )

            # Evitar enviar dos veces la misma cita.
            if appointment.x_meta_schedule_sent:
                raise UserError(
                    f"La cita de {appointment.patient_name} ya fue enviada a Meta."
                )

            # Solo permitir citas confirmadas.
            if appointment.state != "confirmed":
                raise UserError(
                    "La cita debe estar confirmada antes de enviarse a Meta."
                )

            event_id = f"schedule_manual_{appointment.id}"

            partner = appointment.partner_id

            user_data = meta._meta_build_user_data(
                partner=partner,
                fbp=appointment.x_meta_fbp,
                fbc=appointment.x_meta_fbc,
                client_ip_address=appointment.x_meta_client_ip,
                client_user_agent=appointment.x_meta_user_agent,
                external_id=str(partner.id) if partner else None,
            )

            custom_data = {
                "appointment_id": appointment.id,
                "appointment_date": str(appointment.appointment_date or ""),
                "appointment_type": appointment.appointment_type or "",
            }

            _logger.info(
                "META CAPI: enviando Schedule_Manual para cita=%s",
                appointment.id,
            )
            _logger.info("META CAPI: event_id=%s", event_id)

            result = meta._meta_send_event(
                event_name="Schedule_Manual",
                user_data=user_data,
                custom_data=custom_data,
                event_id=event_id,
                action_source="system_generated",
            )

            _logger.info("META CAPI: result=%s", result)

            if not result.get("error") and not result.get("skipped"):
                appointment.sudo().write({
                    "x_meta_schedule_sent": True,
                    "x_meta_schedule_event_id": event_id,
                })
            else:
                raise UserError(
                    "No se pudo enviar el evento a Meta. "
                    "Revisa los logs del servidor."
                )
