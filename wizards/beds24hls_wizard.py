from odoo import models, fields, api, exceptions, _
import requests

class Beds24HLSWizard(models.TransientModel):
    _name = 'beds24_hls.wizard'
    _description = 'Beds24 HLS Wizard'

    start_date = fields.Date(string='Start Date', required=True, default=fields.Date.context_today)
    end_date = fields.Date(string='End Date', required=True, default=fields.Date.context_today)
    status = fields.Selection([('confirmed', "Confirmed"), ('request', "Requested"),
                               ('new', "New"), ('cancelled', "Cancelled"),
                               ('black', "Black"), ('inquiry', "Inquiry")],
                              string='Status', required=True,
                              default='confirmed', help="Type for request to GetBookings from Beds24")
    reservation_lines = fields.One2many('beds24_hls.wizard.reservation', 'wizard_id', string="Reservation",
                                        help="Reservation Lines that have been created")

    def beds24_get_bookings(self):
        self.ensure_one()
        auth_token = self.env['ir.config_parameter'].sudo().get_param("beds24_token")

        if not auth_token:
            raise exceptions.UserError(_("Token doesn't exist. Please configure the Beds24 token by Authorize."))

        url = f'https://beds24.com/api/v2/bookings?status={self.status}'
        headers = {
            'accept': 'application/json',
            'token': auth_token
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            if response.status_code == 401:
                return self._refresh_token_and_retry()
            raise exceptions.UserError(_("Error connecting to Beds24: %s") % str(e))

        bookings = response.json().get("data", [])
        self._create_reservation_lines(bookings)

        return self._get_reservation_action()

    def _refresh_token_and_retry(self):
        refresh_token = self.env['ir.config_parameter'].sudo().get_param("beds24_refresh_token")
        if not refresh_token:
            raise exceptions.UserError(_("Refresh Token doesn't exist. Please configure the Beds24 Refresh Token by Authorize."))

        url = 'https://beds24.com/api/v2/authentication/token'
        headers = {
            'accept': 'application/json',
            'refreshToken': refresh_token
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            new_token = response.json()['token']
            self.env['ir.config_parameter'].sudo().set_param('beds24_token', new_token)
            return self.beds24_get_bookings()
        except requests.exceptions.RequestException as e:
            raise exceptions.UserError(_("Error refreshing token: %s") % str(e))

    def _create_reservation_lines(self, bookings):
        self.reservation_lines.unlink()  # Clear existing lines
        for booking in bookings:
            self.env['beds24_hls.wizard.reservation'].create({
                'wizard_id': self.id,
                'name': str(booking['id']),
                'start_date': booking.get('arrival', ''),
                'end_date': booking.get('departure', ''),
                'status': booking.get('status', '')
            })

    def _get_reservation_action(self):
        return {
            'name': _('Beds24 Respond Bookings'),
            'view_mode': 'tree,form',
            'res_model': 'beds24_hls.wizard.reservation',
            'domain': [('wizard_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

class Beds24HLSWizardReservation(models.TransientModel):
    _name = 'beds24_hls.wizard.reservation'
    _description = 'Beds24 HLS Wizard Reservation'

    wizard_id = fields.Many2one('beds24_hls.wizard', string="Wizard", required=True)
    name = fields.Char(string="Reservation ID", required=True)
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    status = fields.Selection([('confirmed', "Confirmed"), ('request', "Requested"),
                               ('new', "New"), ('cancelled', "Cancelled"),
                               ('black', "Black"), ('inquiry', "Inquiry")],
                              string='Status', required=True)