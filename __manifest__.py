{
    "name": "Hotel Reservation Beds24",
    "version": "13.0.1",
    "author": "Theavuth (B9)",
    "website": "",
    "summary": 'Small demo of Hotel Reservation using beds24',
    "category": 'Hotel',
    'depends': [
        'base',
        'hotel',
        'hotel_reservation',
        'product',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/actions.xml',
        'views/menu.xml',
        'wizards/authorize_wizard_view.xml'
    ],
    'application': True,
    'installable': True,
}
