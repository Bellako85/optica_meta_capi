from odoo import fields, models
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = "crm.lead"

    x_meta_contact_sent = fields.Boolean(
        string="Meta Contact Sent",
        copy=False,
        readonly=True,
    )

    x_meta_contact_event_id = fields.Char(
        string="Meta Contact Event ID",
        copy=False,
        readonly=True,
    )

    def action_send_contact_to_meta(self):
        meta = self.env["meta.capi.mixin"]

        for lead in self:
            if lead.x_meta_contact_sent:
                raise UserError(
                    f"La oportunidad {lead.name} ya fue enviada a Meta."
                )

            # En tu base actual, Calificado = ID 2
            if lead.stage_id.id != 2:
                raise UserError(
                    "La oportunidad debe estar en la etapa Calificado "
                    "antes de enviar Contact a Meta."
                )

            if not lead.partner_id:
                raise UserError(
                    "La oportunidad debe tener un cliente vinculado antes "
                    "de enviarla a Meta."
                )

            event_id = f"contact_{lead.id}"

            user_data = meta._meta_build_user_data(
                partner=lead.partner_id,
                external_id=str(lead.partner_id.id),
            )

            custom_data = {
                "lead_event_source": "Odoo_CRM",
                "event_source": "crm",
                "lead_id": lead.id,
            }

            _logger.info(
                "META CAPI: enviando Contact para oportunidad=%s",
                lead.id,
            )
            _logger.info("META CAPI: event_id=%s", event_id)
            _logger.info("META CAPI: user_data=%s", user_data)

            result = meta._meta_send_event(
                event_name="Contact",
                user_data=user_data,
                custom_data=custom_data,
                event_id=event_id,
                action_source="system_generated",
            )

            _logger.info("META CAPI: result=%s", result)

            if not result.get("error") and not result.get("skipped"):
                lead.sudo().write({
                    "x_meta_contact_sent": True,
                    "x_meta_contact_event_id": event_id,
                })
            else:
                raise UserError(
                    "No se pudo enviar Contact a Meta. "
                    "Revisa los logs del servidor."
                )
