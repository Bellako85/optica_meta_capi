import hashlib
import json
import logging
import time
import requests

from odoo import models

_logger = logging.getLogger(__name__)


class MetaCapiMixin(models.AbstractModel):
    _name = 'meta.capi.mixin'
    _description = 'Meta CAPI Helper'

    def _meta_get_param(self, key, default=False):
        return self.env['ir.config_parameter'].sudo().get_param(
            f'optica_meta_capi.{key}',
            default
        )

    def _meta_is_enabled(self):
        return self._meta_get_param('meta_capi_enabled') in ['True', True, '1', 1]

    def _meta_hash(self, value):
        if not value:
            return False
        value = str(value).strip().lower()
        return hashlib.sha256(value.encode('utf-8')).hexdigest()

    def _meta_clean_phone(self, phone):
        if not phone:
            return False
        return ''.join(c for c in str(phone) if c.isdigit())

    def _meta_build_user_data(self, partner=None, request_obj=None):
        user_data = {}

        if partner:
            if partner.email:
                user_data['em'] = [self._meta_hash(partner.email)]

            phone = self._meta_clean_phone(partner.mobile or partner.phone)
            if phone:
                user_data['ph'] = [self._meta_hash(phone)]

            user_data['external_id'] = [self._meta_hash(str(partner.id))]

        if request_obj:
            user_data['client_ip_address'] = request_obj.httprequest.remote_addr
            user_data['client_user_agent'] = request_obj.httprequest.user_agent.string

            fbp = request_obj.httprequest.cookies.get('_fbp')
            fbc = request_obj.httprequest.cookies.get('_fbc')

            if fbp:
                user_data['fbp'] = fbp
            if fbc:
                user_data['fbc'] = fbc

        return user_data

    def _meta_send_event(self, event_name, user_data, custom_data=None, event_id=None,
                         event_source_url=None, action_source='website'):
        if not self._meta_is_enabled():
            return {'skipped': True, 'reason': 'Meta CAPI disabled'}

        pixel_id = self._meta_get_param('meta_pixel_id')
        access_token = self._meta_get_param('meta_access_token')
        test_event_code = self._meta_get_param('meta_test_event_code')

        if not pixel_id or not access_token:
            return {'skipped': True, 'reason': 'Missing Pixel ID or Access Token'}

        payload = {
            'data': [{
                'event_name': event_name,
                'event_time': int(time.time()),
                'action_source': action_source,
                'user_data': user_data or {},
                'custom_data': custom_data or {},
            }]
        }

        if event_id:
            payload['data'][0]['event_id'] = event_id

        if event_source_url:
            payload['data'][0]['event_source_url'] = event_source_url

        if test_event_code:
            payload['test_event_code'] = test_event_code

        url = f'https://graph.facebook.com/v19.0/{pixel_id}/events'

        try:
            response = requests.post(
                url,
                params={'access_token': access_token},
                json=payload,
                timeout=20
            )

            result = response.json()

            _logger.info(
                'Meta CAPI event sent: %s | payload=%s | response=%s',
                event_name,
                json.dumps(payload, ensure_ascii=False),
                result
            )

            return {
                'status_code': response.status_code,
                'payload': payload,
                'response': result,
            }

        except Exception as e:
            _logger.exception('Meta CAPI error sending event %s', event_name)
            return {
                'error': str(e),
                'payload': payload,
            }
