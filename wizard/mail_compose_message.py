import time
import logging
import hashlib
from odoo import models, fields, api

from facebook_business.adobjects.serverside.custom_data import CustomData
from facebook_business.adobjects.serverside.event import Event
from facebook_business.adobjects.serverside.event_request import EventRequest
from facebook_business.adobjects.serverside.user_data import UserData
from facebook_business.api import FacebookAdsApi

_logger = logging.getLogger(__name__)

class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def _hash_data(self, data):
        if not data:
            return ""
        clean_data = str(data).strip().lower()
        return hashlib.sha256(clean_data.encode('utf-8')).hexdigest()

    def action_send_mail(self):
        res = super(MailComposeMessage, self).action_send_mail()
        
        if self.model == 'optica.appointment':
            config_parameters = self.env['ir.config_parameter'].sudo()
            
            # Validamos si está activo en los Ajustes
            meta_enabled = config_parameters.get_param('optica_meta_capi.meta_capi_enabled')
            if not meta_enabled:
                _logger.info("META CAPI CITAS: Envío omitido porque la integración está desactivada en Ajustes.")
                return res

            appointment = self.env['optica.appointment'].browse(self.res_id)
            
            if appointment:
                try:
                    # Jalamos las credenciales desde tus Ajustes
                    access_token = config_parameters.get_param('optica_meta_capi.meta_access_token') or ''
                    pixel_id = config_parameters.get_param('optica_meta_capi.meta_pixel_id') or ''
                    test_event_code = config_parameters.get_param('optica_meta_capi.meta_test_event_code') or ''

                    if not access_token or not pixel_id:
                        _logger.error("META CAPI CITAS: Falta configurar el Access Token o el Pixel ID en los Ajustes.")
                        return res

                    # Inicializamos API
                    FacebookAdsApi.init(access_token=access_token)

                    # Extraemos y hasheamos datos
                    email_raw = appointment.email or ""
                    phone_raw = appointment.telefono or "" 

                    email_hash = self._hash_data(email_raw)
                    phone_hash = self._hash_data(phone_raw)

                    if not email_hash and not phone_hash:
                        _logger.warning("META CAPI CITAS: Se omitió 'Schedule' para cita %s por datos de contacto vacíos.", appointment.id)
                        return res

                    user_data = UserData(
                        emails=[email_hash] if email_hash else None,
                        phones=[phone_hash] if phone_hash else None
                    )

                    custom_data = CustomData(
                        custom_properties={
                            'lead_event_source': 'Odoo_Citas_Optica',
                            'event_source': 'crm'
                        }
                    )

                    event = Event(
                        event_name="Schedule",
                        event_time=int(time.time()),
                        user_data=user_data,
                        custom_data=custom_data,
                        action_source="system_generated"
                    )

                    # Armamos el request dinámico con el código de prueba (si aplica)
                    kwargs = {'events': [event], 'pixel_id': pixel_id}
                    if test_event_code:
                        kwargs['test_event_code'] = test_event_code

                    event_request = EventRequest(**kwargs)
                    event_response = event_request.execute()

                    _logger.info("META CAPI CITAS: Evento 'Schedule' enviado para la cita de: %s. Código de prueba: %s", appointment.paciente or "Paciente", test_event_code)

                except Exception as e:
                    _logger.error("META CAPI CITAS ERROR: Falló el envío del Schedule. Motivo: %s", str(e))
                    
        return res
