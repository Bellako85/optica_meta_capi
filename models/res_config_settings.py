from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    meta_pixel_id = fields.Char(
        string='Meta Pixel ID',
        config_parameter='optica_meta_capi.meta_pixel_id'
    )

    meta_access_token = fields.Char(
        string='Meta Access Token',
        config_parameter='optica_meta_capi.meta_access_token'
    )

    meta_test_event_code = fields.Char(
        string='Meta Test Event Code',
        config_parameter='optica_meta_capi.meta_test_event_code'
    )

    meta_capi_enabled = fields.Boolean(
        string='Enable Meta CAPI',
        config_parameter='optica_meta_capi.meta_capi_enabled'
    )
