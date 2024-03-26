from odoo import models, fields, api, exceptions, _

import requests

from datetime import datetime

from dateutil.parser import parse


base_url = "https://beds24.com/api/v2"

class Beds24Booking(models.Model):
    _name = "beds24.booking"
    _description = "Handle bookings from beds24"

    name = fields.Char(string="Booking ID", required=True)

    first_name = fields.Char(string="First Name", required=True)

    last_name = fields.Char(string="Last Name", required=True)

    email = fields.Char(string="Email", required=True)

    num_adult = fields.Integer(string="Adults", required=True)

    num_children = fields.Integer(string="Children", required=True)

    booking_date = fields.Char(string="Booking Date", required=True)

    arrival_date = fields.Date(string="Arrival Date", required=True)

    departure_date = fields.Date(string="Departure Date")

    room_id = fields.Char(string="Room ID")

    status = fields.Selection(
        [
            ('new', "New"),
            ('request', "Request"),
            ('confirmed', "Confirmed"),
            ('black', "Black"),
        ]
    )

    @api.model
    def get_beds24_bookings(self):
        auth_token = self.env['ir.config_parameter'].get_param("beds24_token")

        if not auth_token:
            raise exceptions.UserError(_("Token doesn't exist. Please configure the Beds24 token by Authorize."))

        url = 'https://beds24.com/api/v2/bookings?status=confirmed'
        headers = {
            'accept': 'application/json',
            'token': auth_token
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            bookings = data["data"]

            for booking in bookings:
                print("BOOKING", booking)
                existing_booking = self.search([('name', '=', f"{booking['id']}")]).exists()
                if not existing_booking:
                    self.create({
                        "name": f"{booking['id']}",
                        "first_name": booking.get('firstName', ''),
                        "last_name": booking.get('lastName', ''),
                        "num_adult": booking.get('numAdult', 0),
                        "num_children": booking.get('numChild', 0),
                        "booking_date": booking['bookingTime'],
                        "arrival_date": fields.Date.from_string(booking.get('arrival', '')),
                        "departure_date": fields.Date.from_string(booking.get('departure', '')),
                        "room_id": booking.get('roomId', ''),
                        "status": booking['status'],
                    })
                else:
                    existing_booking_ids = self.search([('name', '=', f"B24/{booking['id']}")]).ids
                    self.browse(existing_booking_ids).write({
                        "first_name": booking.get('firstName', ''),
                        "last_name": booking.get('lastName', ''),
                        "num_adult": booking.get('numAdult', 0),
                        "num_children": booking.get('numChild', 0),
                        "booking_date": booking['bookingTime'],
                        "arrival_date": fields.Date.from_string(booking.get('arrival', '')),
                        "departure_date": fields.Date.from_string(booking.get('departure', '')),
                        "room_id": booking.get('roomId', ''),
                    })

        elif response.status_code == 401:

            refresh_token = self.env['ir.config_parameter'].get_param("beds24_refresh_token")


            if not refresh_token:
                raise exceptions.UserError(_("Refresh Token doesn't exist. Please configure the Beds24 Refresh Token by Authorize."))
            
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

                return self.get_beds24_bookings()
            
            else:

                raise exceptions.AccessError(_(f"Request failed with status code {response.status_code}"))

        else:
            raise exceptions.AccessError(_(f"Request failed with status code {response.status_code}"))
        
        return {
            'name': 'Beds24 Booking List',
            'view_mode': 'tree',
            'res_model': 'beds24.booking',
            'view_id': self.env.ref('hotel_reservation_beds24.beds24_bookings_list_view').id,
            'target': 'current',
            'type': 'ir.actions.act_window',
        }

    
    def create_hotel_reservation(self):

        hotel_room_obj = self.env['hotel.room']
        partner_obj = self.env['res.partner']
        hotel_room_reservation_line_obj = self.env['hotel.room.reservation.line']
        hotel_reservation_line_obj = self.env['hotel_reservation.line']
        hotel_reservation_obj = self.env['hotel.reservation']

        if self.status == "cancelled":
            return exceptions.ValidationError(_(f'Booking ID ({self.name}) is already cancelled.'))
        else:

            date_ordered = datetime.strptime(self.booking_date, "%Y-%m-%dT%H:%M:%SZ")
            check_in = str(self.arrival_date) + "T07:00:00"
            check_out = str(self.departure_date) + "T05:00:00"

            beds24_checkin = parse(check_in)
            beds24_checkout = parse(check_out)
            reservation_line = []

            print("Date", beds24_checkin, beds24_checkout)

            # Check Guest Logic

            guest = {
                'name': f"{self.first_name} {self.last_name}",
                'firstname': self.first_name,
                'lastname': self.last_name,
                'email': self.email,
            }

            partner = self.env['res.partner']

            if guest['email']:
                partner = partner_obj.search([('email', '=', guest['email'])])

            if partner.id:
                partner_id = partner.id
            else:
                partner_id = partner_obj.create(guest).id
                property_account_receivable_id = self.env['account.account'].search([('code', '=', '130100'),
                                                                                     ('name', '=', 'City Ledger'),
                                                                                     ('company_id', '=', 23)])
                property_account_payable_id = self.env['account.account'].search([('code', '=', '200100'),
                                                                                  ('name', '=', 'Accounts Payables'),
                                                                                  ('company_id', '=', 23)])
                guest['property_account_receivable_id'] = property_account_receivable_id
                guest['property_account_payable_id'] = property_account_payable_id
            
            # End Guest

            # Assuming room_id is a single room ID
            room = hotel_room_obj.search([('beds24_room_id', '=', self.room_id)], limit=1)

            if not room:
                raise exceptions.ValidationError(_("Room not found for ID: {}").format(self.room_id))

            if room.status == "available":
                vals = {
                    'date_order': date_ordered,
                    'checkin': beds24_checkin,
                    'checkout': beds24_checkout,
                    'beds24_booking_id': self.name,
                    'partner_id': partner_id,
                    'partner_shipping_id': partner_id,
                    'partner_order_id': partner_id,
                    'partner_invoice_id': partner_id,
                    'pricelist_id': 4,
                }
                reservation_id = hotel_reservation_obj.create(vals)

                room_reservation_line_vals = {
                    'room_id': room.id,
                    'reservation_id': reservation_id.id,
                    'check_in': reservation_id.checkin,
                    'check_out': reservation_id.checkout,
                    'state': 'assigned',
                }
                new_line = hotel_room_reservation_line_obj.create(room_reservation_line_vals)

                reservation_line.append(new_line)

                reservation_line_vals = {
                    'line_id': reservation_id.id,
                    'categ_id': room.room_categ_id.id,
                    'name': False,
                    'reserve': [[6, False, [room.id]]]
                }

                room = room.write({'isroom': False, 'status': 'occupied'})

                new_reservation_line = hotel_reservation_line_obj.create(reservation_line_vals)
            
            else:

                raise exceptions.ValidationError(_("Room is already occupied"))




class Product(models.Model):
    _inherit = 'product.template'
    _description = "Inherit product.category model to some customize fields"

    beds24_room_id = fields.Char(string="Beds24 Room ID", unique=True)


class HotelRoom(models.Model):
    _inherit = "hotel.room"
    _description = "Inheriting Hotel Room to add additional fields"

    beds24_room_id = fields.Char(string="Beds24 Room ID", unique=True)


class HotelReservation(models.Model):
    _inherit = "hotel.reservation"
    _description = "Inheriting Hotel reservation to add additional fields"

    beds24_booking_id = fields.Char(string="Beds24 Booking ID")


class Beds24Room(models.Model):
    _name = "beds24.room"

    name = fields.Char(unique=True, required=True)
    room_id = fields.Char(string="Room ID", required=True)
    property_id = fields.Char(string="Property ID", required=True)
    qty = fields.Integer(string="Qty")
    max_people = fields.Integer(string="Max People")
    max_adult =  fields.Integer(string="Max Adult")
    max_children =  fields.Integer(string="Max Children")

    def get_beds24_rooms(self):
        
        auth_token = self.env['ir.config_parameter'].get_param("beds24_token")

        if not auth_token:
            raise exceptions.UserError(_("Token doesn't exist. Please configure the Beds24 token by Authorize."))

        property_id = "226937" # Property ID for Testing

        url = f'https://beds24.com/api/v2/properties?id={property_id}&includeAllRooms=true'
        headers = {
            'accept': 'application/json',
            'token': auth_token
        }

        response = requests.get(url, headers=headers)

        hotel_room_obj = self.env['hotel.room']

        if response.status_code == 200:

            data = response.json()

            rooms = data['data'][0]['roomTypes']

            for room in rooms:
                existing_room = self.search([('room_id', '=', f"{room['id']}")]).exists()
                if not existing_room:
                    new_room = self.create({
                        "name": f"{room['name']}",
                        "room_id": room['id'],
                        "property_id": room['propertyId'],
                        "qty": room['qty'],
                        "max_people": room['maxPeople'],
                        "max_adult": room['maxAdult'],
                        "max_children": room['maxChildren'],
                    })
                

                    
                else:
                    existing_room_ids = self.search([('room_id', '=', f"{room['id']}")]).ids
                    self.browse(existing_room_ids).write({
                        "qty": room.get('qty', 0),
                        "max_people": room.get('maxPeople', 0),
                        "max_adult": room.get('maxAdult', 0),
                        "max_children": room.get('maxChildren', 0),
                    })

                hotel_exist = hotel_room_obj.search([('name', '=', room['name'])]).exists()

                if hotel_exist:

                        existing_room_ids = hotel_room_obj.search([('name', '=', room['name'])]).ids

                        hotel_room_obj.browse(existing_room_ids).write({
                            'beds24_room_id': room['id']
                        })

                else:

                    return exceptions.ValidationError(_(f"{room['name']} doesn't exist"))


        
class Beds24Property(models.Model):
    _name = "beds24_property"
    _description = "Handle properties on Beds24"

    name = fields.Char()

    @api.model
    def get_properties(self):        
        url = base_url + "/properties"
