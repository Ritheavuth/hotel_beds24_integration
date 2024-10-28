from odoo import models, fields, exceptions

class SetPropertyIdWizard(models.TransientModel):
    _name = 'set.property.id.wizard'
    _description = 'Set Property ID Wizard'

    property_id = fields.Char(required=True)

    def set_property_id(self):
        self.env['ir.config_parameter'].set_param('beds24_property_id', self.property_id)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'beds24.room.type',
            'view_mode': 'tree,form',
            'target': 'current',
        }