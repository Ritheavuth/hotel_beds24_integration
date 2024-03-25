from odoo import models, fields, exceptions
import requests

class AuthorizeWizard(models.TransientModel):
    _name = 'authorize.wizard'
    _description = 'Authorize Beds24 Wizard'

    invite_code = fields.Char(required=True)

    def authorize_beds24(self):
        # Define the URL
        url = 'https://beds24.com/api/v2/authentication/setup'

        # Define the headers
        headers = {
            'accept': 'application/json',
            'code': self.invite_code
        }

        # Make the GET request
        response = requests.get(url, headers=headers)

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the JSON response
            data = response.json()
            print(data)

            token = data["token"]
            refresh_token = data["refreshToken"]

            if token:
                # Store the token in the system parameter
                self.env['ir.config_parameter'].set_param('beds24_token', token)
                self.env['ir.config_parameter'].set_param('beds24_refresh_token', refresh_token)

                token = self.env['ir.config_parameter'].get_param('beds24_token')

                print("BEDS24 Token", token)

                print(f"Token stored successfully: {token}")


            else:
                raise exceptions.UserError("Token not found in the response.")
        
        else:

            data = response.json()

            print("Error", data)

            raise exceptions.UserError(f"{data['error']}")
        