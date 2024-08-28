from odoo import models, fields, exceptions
import requests

class AuthorizeWizard(models.TransientModel):
    _name = 'authorize.wizard'
    _description = 'Authorize Beds24 Wizard'

    invite_code = fields.Char(required=True)

    def authorize_beds24(self):
        url = 'https://beds24.com/api/v2/authentication/setup'
        headers = {
            'accept': 'application/json',
            'code': self.invite_code
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            token = data.get("token")
            refresh_token = data.get("refreshToken")

            if token:
                self.env['ir.config_parameter'].set_param('beds24_token', token)
                self.env['ir.config_parameter'].set_param('beds24_refresh_token', refresh_token)

                print(f"Token stored successfully: {token}")
            else:
                raise exceptions.UserError("Token not found in the response.")
        else:
            data = response.json()
            raise exceptions.UserError(f"{data['error']}")
