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
        auth_token = self.env['ir.config_parameter'].get_param("beds24_token")

        if not auth_token:
            raise exceptions.UserError(_("Token doesn't exist. Please configure the Beds24 token by Authorize."))

        url = f'https://beds24.com/api/v2/bookings?status={self.status}'
        headers = {
            'accept': 'application/json',
            'token': auth_token
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            bookings = data["data"]

            self.reservation_lines.unlink()  # Clear existing lines
            for booking in bookings:
                self.env['beds24_hls.wizard.reservation'].create({
                    'wizard_id': self.id,
                    'name': f"{booking['id']}",
                    'start_date': booking.get('arrival', ''),
                    'end_date': booking.get('departure', ''),
                    'status': booking.get('status', '')
                })

        elif response.status_code == 401:
            refresh_token = self.env['ir.config_parameter'].get_param("beds24_refresh_token")

            if not refresh_token:
                raise exceptions.UserError(
                    _("Refresh Token doesn't exist. Please configure the Beds24 Refresh Token by Authorize."))

            url = 'https://beds24.com/api/v2/authentication/token'
            headers = {
                'accept': 'application/json',
                'refreshToken': refresh_token
            }

            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                response = response.json()
                token = response['token']
                self.env['ir.config_parameter'].set_param('beds24_token', token)
                return self.beds24_get_bookings()
            else:
                raise exceptions.AccessError(_(f"Request failed with status code {response.status_code}"))
        else:
            raise exceptions.AccessError(_(f"Request failed with status code {response.status_code}"))

        return {
            'name': 'Beds24 Booking List',
            'view_mode': 'tree',
            'res_model': 'beds24_hls.wizard.reservation',
            'view_id': self.env.ref('beds24_hls.view_beds24_hls_wizard_reservation_tree').id,
            'target': 'current',
            'type': 'ir.actions.act_window',
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
