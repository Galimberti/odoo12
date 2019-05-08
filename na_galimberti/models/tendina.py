from odoo import api, fields, models, tools, SUPERUSER_ID, _, exceptions


class NaTendina(models.Model):
    _name = "na.tendina"

    name = fields.Char(string='Codice', required=True)
    option_ids = fields.One2many('na.tendina.option', 'parent_id', string='Opzioni')


class NaTendinaOption(models.Model):
    _name = "na.tendina.option"

    name = fields.Char(string='Nome', required=True)
    parent_id = fields.Many2one('na.tendina', string='Codice Padre')
