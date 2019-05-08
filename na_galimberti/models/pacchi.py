from odoo import api, fields, models, tools, SUPERUSER_ID, _, exceptions
from odoo.exceptions import UserError

value_list = ['lunghezza', 'larghezza', 'spessore', 'diametro']


class NaPacchi(models.Model):
    _name = 'na.pacchi'

    name = fields.Char(string='Numero Pacco', readonly=True)
    pacchi_product = fields.One2many('na.pacchi.product', 'n_pacco', string='Contenuto Cartone')
    flag_readonly = fields.Boolean()
    flag_order = fields.Boolean("Questo pacco e' di un ordine")

    def get_category_values(self, this):
        if this.product_id:
            for category_value in this.product_id.category_value_ids:
                for value in value_list:
                    if value in category_value.caratteristica_id.name.lower():
                        if ' v' in category_value.caratteristica_id.name.lower():
                            if this._name == 'sale.order.line':
                                this[value] = float(category_value.value_char)
                        elif ' a' in category_value.caratteristica_id.name.lower():
                            if this._name == 'purchase.order.line':
                                this[value] = float(category_value.value_char)
                        else:
                            this[value] = float(category_value.value_char)
                        break

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('na.pacchi.sequence')
        return super(NaPacchi, self).create(vals)

    # @api.multi
    # def unlink(self):
    #     for pacco in self:
    #         if pacco.flag_readonly:
    #             raise UserError('NO!')
    #         else:
    #             res = super(NaPacchi, pacco).unlink()
    #             self._cr.commit()
    #     return res


class NaPacchiProduct(models.Model):
    _name = 'na.pacchi.product'
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.template', string='Prodotti')
    lunghezza = fields.Char(string='Lunghezza')
    larghezza = fields.Char(string='Larghezza')
    spessore = fields.Char(string='Spessore')
    diametro = fields.Char(string='Diametro')
    qty = fields.Integer(string="Quantita'")
    n_pacco = fields.Many2one('na.pacchi', string='Numero Pacco')
    qty_reserved = fields.Integer(string="Quantita' Riservata")
    flag_order = fields.Boolean(related='n_pacco.flag_order')

    @api.model
    def create(self, vals):
        vals['qty_reserver'] = vals['qty']
        return super(NaPacchiProduct, self).create(vals)

    @api.onchange('product_id')
    def onchange_product_id(self):
        value_list = ['lunghezza', 'larghezza', 'spessore', 'diametro']
        if self.product_id:
            for category_value in self.product_id.category_value_ids:
                for value in value_list:
                    if value in category_value.caratteristica_id.name:
                        if value == 'altezza':
                            value = 'spessore'
                        self[value] = float(category_value.value_char)
                        break

    def update_qty(self):
        for product in self:
            product.qty -= product.qty_reserved
