from odoo import api, fields, models, tools, SUPERUSER_ID, _, exceptions
from odoo.exceptions import UserError
import re


class NaValueLine(models.Model):
    _name = "na.value.line"

    name = fields.Char(string='Valore')
    category_value_id = fields.Many2one('na.category.value', string='Category Value Line')


class NaCaratteristica(models.Model):
    _name = "na.caratteristica"

    name = fields.Char(string='Nome', required=True)
    uom_id = fields.Many2one('uom.uom', string='UoM')
    tipo_dato = fields.Selection(string='Tipo Dato', placeholder='Scegli il tipo di Dato', required=True,
                                 selection=[('integer', 'Intero'), ('float', 'Decimale'), ('char', 'Testo'),
                                            ('selection', 'Tendina')], )
    cod_tendina = fields.Many2one('na.tendina', string='Codice Tendina')
    valori_multipli = fields.Boolean(string='Ammessi Valori Multipli')
    obbligatorio = fields.Boolean(string='Obbligatorio')
    variabile_ordine = fields.Boolean(string='Variabile su Ordine')

    category_ids = fields.Many2many('product.category', column1='caratteristica_id', column2='category_id',
                                    string='Categorie')

    codice_pattern = fields.Char(string='Codice note prodotti')

    @api.model
    def create(self, vals):
        res = super(NaCaratteristica, self).create(vals)
        if not res.codice_pattern:
            res.codice_pattern = '<%' + res.name + '%>'
        return res

    def add_new_caratteristica(self):
        just_one = False
        for product in self.env['product.template'].search([(1, '=', 1)]):
            passa = False
            categ_id = product.categ_id
            while categ_id:
                if categ_id.id in self.category_ids.ids:
                    passa = True
                    break
                categ_id = categ_id.parent_id

            if passa and not product.category_value_ids.filtered(lambda r: r.caratteristica_id.id == self.id):
                self.env['na.category.value'].create({
                    'product_id': product.id,
                    'categ_id': product.categ_id.id,
                    'caratteristica_id': self.id,
                    'type': self.tipo_dato,
                    'uom_id': self.uom_id.id,
                })
                if not just_one:
                    just_one = True
        if not just_one:
            raise UserError('Tutti i prodotti sono già stati aggiornati!')


class NaCategoryValue(models.Model):
    _name = "na.category.value"

    product_id = fields.Many2one('product.template', string='Prodotto', required=True)
    categ_id = fields.Many2one('product.category', string='Categoria', required=True)
    caratteristica_id = fields.Many2one('na.caratteristica', string='Caratteristica', required=True)

    value = fields.One2many('na.value.line', 'category_value_id', string='Valore')
    value_char = fields.Char('Valore/i')
    value_ids = fields.Char('Valori IDS')

    tendina_m2o = fields.Many2one('na.tendina.option', string='Valore')
    intero = fields.Integer(string='Valore')
    testo = fields.Char(string='Valore')
    decimale = fields.Float(string='Valore')
    type = fields.Selection([('integer', 'Intero'), ('float', 'Decimale'), ('char', 'Testo'), ('selection', 'Tendina')],
                            string='Tipo')
    uom_id = fields.Many2one('uom.uom', string='UoM')
    valori_multipli = fields.Boolean(related='caratteristica_id.valori_multipli', string='Obbligatorio')
    cod_tendina = fields.Integer(related='caratteristica_id.cod_tendina.id', string='Id Codice Tendina')

    value_char_ids = fields.One2many('na.value.char', 'category_value_id', string='Valori')
    value_int_ids = fields.One2many('na.value.int', 'category_value_id', string='Valori')
    value_dec_ids = fields.One2many('na.value.dec', 'category_value_id', string='Valori')
    tendina_m2m = fields.Many2many('na.tendina.option', 'category_value_id', 'option_id', string='Valori')

    @api.onchange('testo', 'intero', 'decimale', 'tendina_m2o', 'value_char_ids', 'value_int_ids', 'value_dec_ids',
                  'tendina_m2m')
    def change_value(self):
        value_line = self.env['na.value.line']
        name_list = []
        type = self.type

        if self.valori_multipli:
            if type == 'char':
                rel_list = self.value_char_ids
            elif type == 'integer':
                rel_list = self.value_int_ids
            elif type == 'float':
                rel_list = self.value_dec_ids
            elif type == 'selection':
                rel_list = self.tendina_m2m
            for val in rel_list:
                name_list.append(str(val.name))
        else:
            if type == 'char':
                name_list.append(self.testo)
            elif type == 'integer':
                name_list.append(str(self.intero))
            elif type == 'float':
                name_list.append(str(self.decimale))
            elif type == 'selection':
                name_list.append(self.tendina_m2o.name)

        value_char = ''
        value_ids = ''
        self_id = self._origin.id
        for name in name_list:
            if not name:
                name = ''

            line = value_line.create({
                'name': name,
                'category_value_id': self_id,
            })
            if value_char:
                value_char += ', ' + name
            else:
                value_char += name
            if value_ids:
                value_ids += ',' + str(line.id)
            else:
                value_ids += str(line.id)

        self.value_char = value_char
        self.value_ids = value_ids

    @api.multi
    def write(self, vals):
        res = super(NaCategoryValue, self).write(vals)

        if self.value_ids:
            true_ids = self.value_ids.split(',')
            all_ids = self.env['na.value.line'].search([('category_value_id', '=', self.id)])
            for one_id in all_ids:
                if str(one_id.id) not in true_ids:
                    one_id.unlink()

        return res


class ProductCategory(models.Model):
    _inherit = "product.category"

    caratteristica_ids = fields.Many2many('na.caratteristica', column1='category_id', column2='caratteristica_id',
                                          string='Caratteristiche')
    pattern_product = fields.Char('Pattern per Prodotto')
    complete_name = fields.Char(
        'Complete Name', compute='_compute_complete_name',
        store=True)

    def get_display_name(self):
        display_name = self.name
        parent_id = self.parent_id
        while parent_id:
            display_name = parent_id.name + ' / ' + display_name
            parent_id = parent_id.parent_id
        return display_name

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = category.get_display_name()
            else:
                category.complete_name = category.name

    # @api.model
    # def create(self, vals):
    #     res = super(ProductCategory, self).create(vals)
    #     self.update_pattern()
    #     return res
    #
    # def update_pattern(self):
    #     category_ids = self.env['product.category'].search([(1, '=', 1)])
    #     for category in category_ids:
    #         id_list = [category.id]
    #         parent = category.parent_id
    #
    #         x = 1
    #         while x < 3:
    #             if parent:
    #                 id_list.append(parent.id)
    #                 parent = parent.parent_id
    #             else:
    #                 id_list.append(category.id)
    #             x += 1
    #
    #         self._cr.execute('SELECT caratteristica_id, prefix, postfix, sequence '
    #                          'FROM na_caratteristica_product_category_rel '
    #                          'WHERE category_id IN (%s, %s, %s) AND sequence IS NOT NULL '
    #                          'ORDER BY sequence' %
    #                          (id_list[0], id_list[1], id_list[2]))
    #         result = self._cr.fetchall()
    #         if result:
    #
    #             pattern = ''
    #             for res in result:
    #                 caratteristica_id = res[0]
    #                 caratteristica = self.env['na.caratteristica'].search([('id', '=', caratteristica_id)])
    #                 codice_pattern = re.sub('<%', '', caratteristica.codice_pattern)
    #                 codice_pattern = re.sub('%>', '', codice_pattern)
    #
    #                 prefix = res[1]
    #                 postfix = res[2]
    #                 if pattern:
    #                     pattern += ' '
    #                 if prefix:
    #                     prefix = re.sub('<%UM%>', '<%UM_' + codice_pattern + '%>', prefix)
    #                     pattern += prefix + ' '
    #                 pattern += caratteristica.codice_pattern
    #                 if postfix:
    #                     postfix = re.sub('<%UM%>', '<%UM_' + codice_pattern + '%>', postfix)
    #                     pattern += ' ' + postfix
    #
    #                 # sequence = res[3]
    #             if pattern:
    #                 if pattern != category.pattern_product:
    #                     category.pattern_product = pattern


class NaCaratteristicaProductCategoryRel(models.Model):
    _name = 'na_caratteristica_product_category_rel'

    category_id = fields.Many2one('product.category', string='Categoria')
    caratteristica_id = fields.Many2one('na.caratteristica', string='Caratteristica')

    prefix = fields.Char('Prefisso')
    postfix = fields.Char('Postfisso')
    sequence = fields.Integer('Sequenza')
