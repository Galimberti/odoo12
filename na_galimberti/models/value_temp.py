from odoo import api, fields, models, tools, SUPERUSER_ID, _, exceptions


class NaValueChar(models.Model):
    _name = "na.value.char"

    name = fields.Char(string='Valore')
    category_value_id = fields.Many2one('na.category.value', string='Category Value Line')


class NaValueInt(models.Model):
    _name = "na.value.int"

    name = fields.Integer(string='Valore')
    category_value_id = fields.Many2one('na.category.value', string='Category Value Line')

    @api.model
    def create(self, vals):
        name = ''
        if isinstance(vals['name'], str):
            for cha in vals['name']:
                if cha.isdigit():
                    name += cha
            vals['name'] = int(name)

        return super(NaValueInt, self).create(vals)


class NaValueDec(models.Model):
    _name = "na.value.dec"

    name = fields.Float(string='Valore')
    category_value_id = fields.Many2one('na.category.value', string='Category Value Line')

    @api.model
    def create(self, vals):
        name = ''
        if isinstance(vals['name'], str):
            for cha in vals['name']:
                if cha.isdigit():
                    name += cha
                elif cha == '.' or cha == ',':
                    name += '.'
            vals['name'] = float(name)

        return super(NaValueDec, self).create(vals)
