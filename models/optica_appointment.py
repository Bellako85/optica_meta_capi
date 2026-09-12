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

    def action_send_schedule_to_meta(self):
        meta = self.env["meta.capi.mixin"]

        for appointment in self:
            if appointment.x_meta_schedule_sent:
                raise UserError(
                    f"La cita de {appointment.patient_name} ya fue enviada a Meta."
                )

            if appointment.state != "confirmed":
                raise UserError(
                    "La cita debe estar confirmada antes de enviar Schedule a Meta."
                )

            event_id = f"schedule_{appointment.id}"

            partner = appointment.partner_id

            user_data = meta._meta_build_user_data(
                partner=partner,
                external_id=str(partner.id) if partner else None,
            )

            custom_data = {
                "appointment_id": appointment.id,
                "appointment_date": str(appointment.appointment_date or ""),
                "appointment_type": appointment.appointment_type or "",
            }

            _logger.info(
                "META CAPI: enviando Schedule para cita=%s",
                appointment.id,
            )
            _logger.info("META CAPI: event_id=%s", event_id)
            _logger.info("META CAPI: user_data=%s", user_data)

            result = meta._meta_send_event(
                event_name="Schedule",
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
                    "No se pudo enviar Schedule a Meta. Revisa los logs del servidor."
                )
