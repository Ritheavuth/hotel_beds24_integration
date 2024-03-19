from odoo import models, fields, api, exceptions

import requests


base_url = "https://beds24.com/api/v2"


class Beds24Booking(models.Model):
    _name = "beds24.booking"
    _description = "Handle bookings from beds24"

    name = fields.Char()

    status = fields.Selection(
        [
            ('new', "New"),
            ('request', "Request"),
            ('confirmed', "Confirmed"),
            ('black', "Black"),
        ]
    )

    @api.model
    def get_bookings(self):

        auth_token = self.env['ir.config_parameter'].get_param("beds24_token")

        url = 'https://beds24.com/api/v2/bookings'

        # Define the headers
        headers = {
            'accept': 'application/json',
            'token': auth_token
        }

        # Make the GET request
        response = requests.get(url, headers=headers)

        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()

            print("RESPONSE DATA", data)

            bookings = data["data"]

            print("BOOKINGS DATA", bookings)

            for booking in bookings:
                # Check if a booking with the same name already exists
                existing_booking = self.search([('name', '=', f"B24/{booking['id']}")]).exists()
                if not existing_booking:
                    # If not, create a new booking
                    self.create({
                        "name": f"B24/{booking['id']}",
                        "status": booking['status'],
                    })
                
                else:
                    # If it exists, update the status
                    existing_booking_ids = self.search([('name', '=', f"B24/{booking['id']}")]).ids
                    self.browse(existing_booking_ids).write({
                        "status": booking['status'],
                    })

        else:
            raise ValueError(f"Request failed with status code {response.status_code}")
        

        return {
                'name': 'Beds24 Booking List',
                'view_mode': 'tree',
                'res_model': 'beds24.booking',
                'view_id': self.env.ref('hotel_reservation_beds24.beds24_bookings_list_view').id,
                'target': 'current',
                'type': 'ir.actions.act_window',
            }

        
class Beds24Property(models.Model):
    _name = "beds24_property"
    _description = "Handle properties on Beds24"

    name = fields.Char()

    @api.model
    def get_properties(self):        
        url = base_url + "/properties"
