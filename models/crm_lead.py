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

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def _hash_data(self, data):
        if not data:
            return ""
        clean_data = str(data).strip().lower()
        return hashlib.sha256(clean_data.encode('utf-8')).hexdigest()

    def write(self, vals):
        res = super(CrmLead, self).write(vals)
        
        if 'stage_id' in vals:
            # Recuperamos primero las configuraciones desde ir.config_parameter
            config_parameters = self.env['ir.config_parameter'].sudo()
            
            # Verificamos si la integración está activa en tus Ajustes
            meta_enabled = config_parameters.get_param('optica_meta_capi.meta_capi_enabled')
            if not meta_enabled:
                _logger.info("META CAPI CRM: Envío omitido porque la integración está desactivada en Ajustes.")
                return res

            # Buscamos tu etapa "Calificado" (Asegúrate de que el ID 2 corresponda a tu etapa real)
            STAGE_CALIFICADO_ID = 2 

            if vals.get('stage_id') == STAGE_CALIFICADO_ID:
                for lead in self:
                    try:
                        # Jalamos los tokens y credenciales dinámicas de tu pantalla de Ajustes
                        access_token = config_parameters.get_param('optica_meta_capi.meta_access_token') or ''
                        pixel_id = config_parameters.get_param('optica_meta_capi.meta_pixel_id') or ''
                        test_event_code = config_parameters.get_param('optica_meta_capi.meta_test_event_code') or ''

                        if not access_token or not pixel_id:
                            _logger.error("META CAPI CRM: No se puede enviar el evento porque falta el Access Token o el Pixel ID en los Ajustes.")
                            continue

                        # Inicializamos la API con las credenciales de tus Ajustes
                        FacebookAdsApi.init(access_token=access_token)

                        # Hasheamos los datos del cliente
                        email_raw = lead.email_from or ""
                        phone_raw = lead.phone or ""

                        email_hash = self._hash_data(email_raw)
                        phone_hash = self._hash_data(phone_raw)

                        if not email_hash and not phone_hash:
                            _logger.warning("META CAPI CRM: Se omitió el Lead para %s por falta de teléfono y correo.", lead.name)
                            continue

                        user_data = UserData(
                            emails=[email_hash] if email_hash else None,
                            phones=[phone_hash] if phone_hash else None
                        )

                        custom_data = CustomData(
                            custom_properties={
                                'lead_event_source': 'Odoo_CRM',
                                'event_source': 'crm'
                            }
                        )

                        event = Event(
                            event_name="Lead",
                            event_time=int(time.time()),
                            user_data=user_data,
                            custom_data=custom_data,
                            action_source="system_generated"
                        )

                        # Construimos la petición agregando el código de prueba si está lleno en tus ajustes
                        kwargs = {'events': [event], 'pixel_id': pixel_id}
                        if test_event_code:
                            kwargs['test_event_code'] = test_event_code

                        event_request = EventRequest(**kwargs)
                        event_response = event_request.execute()
                        
                        _logger.info("META CAPI CRM: Evento 'Lead' enviado con éxito para: %s. Código de prueba usado: %s", lead.name, test_event_code)

                    except Exception as e:
                        _logger.error("META CAPI CRM ERROR: Falló el envío del lead %s. Motivo: %s", lead.name, str(e))
        return res
