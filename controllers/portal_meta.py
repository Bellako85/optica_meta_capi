from odoo import fields
from odoo.http import request
from odoo.addons.sale.controllers.portal import CustomerPortal


class CustomerPortalMeta(CustomerPortal):

    def _meta_clean_order_url(self, order):
        return f"/my/orders/{order.id}"

    def _meta_store_order_visit(self, order):
        if not order:
            return

        httprequest = request.httprequest
        user_agent = httprequest.user_agent.string if httprequest.user_agent else ''
        ip = httprequest.headers.get('X-Forwarded-For') or httprequest.remote_addr
        fbp = httprequest.cookies.get('_fbp')
        fbc = httprequest.cookies.get('_fbc')

        values = {
            'x_meta_order_link_opened': True,
            'x_meta_order_link_opened_at': fields.Datetime.now(),
            'x_meta_client_ip': ip or False,
            'x_meta_user_agent': user_agent or False,
            'x_meta_event_source_url': self._meta_clean_order_url(order),
        }

        if fbp:
            values['x_meta_fbp'] = fbp
        if fbc:
            values['x_meta_fbc'] = fbc

        order.sudo().write(values)

    def portal_my_order(self, order_id=None, access_token=None, report_type=None, download=False, **kw):
        response = super().portal_my_order(
            order_id=order_id,
            access_token=access_token,
            report_type=report_type,
            download=download,
            **kw
        )

        try:
            order = request.env['sale.order'].sudo().browse(order_id)
            if order.exists():
                self._meta_store_order_visit(order)
        except Exception:
            pass

        return response
