# -*- coding: utf-8 -*-

from odoo import fields, http
from odoo.exceptions import ValidationError
from odoo.http import request


class OpticaAppointmentController(http.Controller):
    """Public website routes to schedule optical appointments."""

    def _parse_float_time(self, value):
        if not value:
            return 0.0
        if ":" in value:
            hours, minutes = value.split(":", 1)
            return int(hours) + (int(minutes) / 60.0)
        return float(value)

    def _prepare_appointment_values(self, post):
        httprequest = request.httprequest
        user_agent = httprequest.user_agent.string if httprequest.user_agent else ""
        client_ip = httprequest.headers.get("X-Forwarded-For") or httprequest.remote_addr
        fbp = httprequest.cookies.get("_fbp")
        fbc = httprequest.cookies.get("_fbc")
        return {
            "patient_name": post.get("patient_name", "").strip(),
            "whatsapp": post.get("whatsapp", "").strip(),
            "email": post.get("email", "").strip(),
            "appointment_date": post.get("appointment_date"),
            "appointment_time": self._parse_float_time(post.get("appointment_time")),
            "duration": 0.5,
            "state": "draft",
            "x_meta_fbp": fbp or False,
            "x_meta_fbc": fbc or False,
            "x_meta_client_ip": client_ip or False,
            "x_meta_user_agent": user_agent or False,
        }
        
    def _validate_appointment_form(self, post):
        errors = {}
        required_fields = {
            "patient_name": "El nombre es obligatorio.",
            "whatsapp": "El WhatsApp es obligatorio.",
            "email": "El email es obligatorio.",
            "appointment_date": "La fecha deseada es obligatoria.",
            "appointment_time": "La hora deseada es obligatoria.",
        }
        for field_name, message in required_fields.items():
            if not post.get(field_name):
                errors[field_name] = message
        appointment_date = False
        appointment_time = False
        if post.get("appointment_date"):
            try:
                appointment_date = fields.Date.to_date(post.get("appointment_date"))
            except ValueError:
                errors["appointment_date"] = "La fecha indicada no es válida."
        try:
            appointment_time = self._parse_float_time(post.get("appointment_time"))
        except (ValueError, TypeError):
            errors["appointment_time"] = "La hora indicada no es válida."
        else:
            if post.get("appointment_time") and not 0.0 <= appointment_time <= 23.99:
                errors["appointment_time"] = "La hora debe estar entre 00:00 y 23:59."
        if appointment_date and appointment_time is not False:
            weekday = appointment_date.weekday()
            if weekday == 6:
                errors["appointment_date"] = "No agendamos citas los domingos."
            elif weekday <= 4:
                if not 10.0 <= appointment_time <= 18.5:
                    errors["appointment_time"] = "El horario de lunes a viernes es de 10:00 a 19:00."
            elif weekday == 5:
                if not 10.0 <= appointment_time <= 16.5:
                    errors["appointment_time"] = "El horario del sábado es de 10:00 a 17:00."
        return errors

    def _is_slot_available(self, post):
        appointment_date = post.get("appointment_date")
        appointment_time = self._parse_float_time(post.get("appointment_time"))
        duration = 0.5
        new_start = appointment_time
        new_end = appointment_time + duration
        appointments = request.env["optica.appointment"].sudo().search([
            ("appointment_date", "=", appointment_date),
            ("state", "in", ["draft", "confirmed"]),
        ])
        for appointment in appointments:
            existing_start = appointment.appointment_time
            existing_end = appointment.appointment_time + (appointment.duration or 0.5)
            if existing_start < new_end and existing_end > new_start:
                return False
        return True

    @http.route("/agendar-cita", type="http", auth="public", website=True, methods=["GET", "POST"])
    def appointment_form(self, **post):
        values = {"errors": {}, "form_values": post}
        if request.httprequest.method == "POST":
            errors = self._validate_appointment_form(post)
            if errors:
                values["errors"] = errors
                return request.render("optica_appointment.appointment_form", values)
            if not self._is_slot_available(post):
                values["errors"] = {"general": "Ese horario ya fue solicitado. Por favor elige otra hora disponible."}
                return request.render("optica_appointment.appointment_form", values)
            try:
                cita = request.env["optica.appointment"].sudo().create(self._prepare_appointment_values(post))
                # Guarda el event_id que genera optica_meta_capi para deduplicar Píxel + CAPI
                cita.flush()
                event_id = cita.x_meta_event_id or f"schedule_{cita.id}"
                request.session['last_schedule_event_id'] = event_id
            except ValidationError:
                values["errors"] = {"general": "Ese horario ya fue solicitado. Por favor elige otra hora disponible."}
                return request.render("optica_appointment.appointment_form", values)
            return request.redirect("/agendar-cita/gracias")
        return request.render("optica_appointment.appointment_form", values)

    @http.route("/agendar-cita/gracias", type="http", auth="public", website=True)
    def appointment_success(self, **kwargs):
        event_id = request.session.pop('last_schedule_event_id', False)
        if not event_id:
            cita = request.env["optica.appointment"].sudo().search([], order="id desc", limit=1)
            event_id = cita.x_meta_event_id if cita and cita.x_meta_event_id else "schedule_noid"
        return request.render("optica_appointment.appointment_success", {"event_id": event_id})
