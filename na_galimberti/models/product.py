from odoo import api, fields, models, tools, SUPERUSER_ID, _, exceptions
import re
import math
import requests
from datetime import datetime


# class ProductProduct(models.Model):
#     _inherit = "product.product"
#
#     @api.multi
#     def name_get(self):
#         # if len(self.ids) >        1:
#
#         #     return super(ProductProduct, self).name_get()
#
#         def _name_get(d):
#             code = self._context.get('display_default_code', True) and d.get('default_code', False) or False
#             name = '%s' % code
#             return d['id'], name
#
#         partner_id = self._context.get('partner_id')
#         if partner_id:
#             partner_ids = [partner_id, self.env['res.partner'].browse(partner_id).commercial_partner_id.id]
#         else:
#             partner_ids = []
#
#         # all user don't have access to seller and partner
#         # check access and use superuser
#         self.check_access_rights("read")
#         self.check_access_rule("read")
#
#         result = []
#         for product in self.sudo():
#             sellers = []
#             if partner_ids:
#                 sellers = [x for x in product.seller_ids if (x.name.id in partner_ids) and (x.product_id == product)]
#                 if not sellers:
#                     sellers = [x for x in product.seller_ids if (x.name.id in partner_ids) and not x.product_id]
#             if sellers:
#                 for s in sellers:
#                     mydict = {
#                         'id': product.id,
#                         'default_code': s.product_code or product.default_code,
#                     }
#                     temp = _name_get(mydict)
#                     if temp not in result:
#                         result.append(temp)
#             else:
#                 mydict = {
#                     'id': product.id,
#                     'default_code': product.default_code,
#                 }
#                 result.append(_name_get(mydict))
#         return result


class ProductRicarico(models.Model):
    _name = 'product.ricarico'

    name = fields.Char('Descrizione', required=True)
    ricarico = fields.Float('Ricarico (%)', required=True)
    aum_sciolto = fields.Float('Aum. Sciolto (%)', required=True)
    ricarico_minimo = fields.Float('Ricarico minomo (%)', required=True)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    name = fields.Char('Name', index=True, required=False, translate=True)

    category_value_ids = fields.One2many('na.category.value', 'product_id', string='Valori Categorie')
    link = fields.Char('Link Scheda Tecnica')
    flag_pacco = fields.Boolean('Gestire con Pacchi', default=True)
    flag_pacco_only = fields.Boolean('Pacco Unico')
    confezione_vendita = fields.Many2one('product.packaging', string='Confezione Vendita',
                                         domain=[('conf_type', '=', 'Vendita')])
    confezione_acquisto = fields.Many2one('product.packaging', string='Confezione Acquisto',
                                          domain=[('conf_type', '=', 'Acquisto')])

    pacchi_ids = fields.One2many('na.pacchi.product', 'product_id', string='Pacchi')

    # Note pattern
    name_pattern = fields.Char('Pattern del Nome')
    description_sale_pattern = fields.Text(
        'Sale Description', translate=True,
        help="A description of the Product that you want to communicate to your customers. "
             "This description will be copied to every Sales Order, Delivery Order and Customer Invoice/Credit Note")
    description_purchase_pattern = fields.Text(
        'Purchase Description', translate=True,
        help="A description of the Product that you want to communicate to your vendors. "
             "This description will be copied to every Purchase Order, Receipt and Vendor Bill/Credit Note.")
    description_picking_pattern = fields.Text('Description on Picking', translate=True)
    description_pickingout_pattern = fields.Text('Description on Delivery Orders', translate=True)
    description_pickingin_pattern = fields.Text('Description on Receptions', translate=True)

    conv_rate = fields.Float('Tasso di Conversione')
    uom_base = fields.Many2one('uom.uom', string='Unità di Misura')
    qty_available_uom_base = fields.Float('Quantità Disponibile (UdM Base)', compute='_get_converted_qty_available')

    fornitore = fields.Many2one('res.partner', string='Fornitore', domain=[('supplier', '=', True)])
    codice_fornitore = fields.Char('Codice Fornitore')

    qty_to_order = fields.Float('Quantità Richiesta')
    qty_ottimale = fields.Float('Quantità Ottimale')
    qty_on_sale = fields.Float('Quantità in Vendita', compute='_get_all_qty')
    qty_on_purchase = fields.Float('Quantità in Acquisto', compute='_get_all_qty')
    qty_proposta = fields.Float('Quantità Proposta', compute='_get_all_qty')
    qty_effettiva = fields.Float('Quantità Effettiva')
    qty_prenotata = fields.Float('Quantità Prenotata', compute='_get_all_qty')

    users_sheet = fields.Many2many('res.users', string='Utente richiesta ZAP')
    stamp_gsheet = fields.Datetime()

    su_misura = fields.Boolean('Su misura')

    ricarico_id = fields.Many2one('product.ricarico', string='Ricarico')
    prezzo_pk_proposto = fields.Float('Prezzo Pk. proposto', readonly=True, compute='_get_ricarico_values')
    aggiust_pk = fields.Float('Aggiustamento Pk')
    aggiust_sciolto = fields.Float('Aggiust. sciolto')
    prezzo_impresa = fields.Float('Prezzo Impresa', readonly=True, compute='_get_ricarico_values')
    prezzo_privato = fields.Float('Prezzo Privato', readonly=True, compute='_get_ricarico_values')

    @api.multi
    def _get_ricarico_values(self):
        for product in self:
            if product.ricarico_id:
                product.prezzo_pk_proposto = product.standard_price + (
                        product.standard_price * product.ricarico_id.ricarico / 100)
                prezzo_pk_proposto = round(product.prezzo_pk_proposto, 2)
                product.prezzo_impresa = prezzo_pk_proposto + product.aggiust_pk
                product.prezzo_privato = prezzo_pk_proposto + (
                        prezzo_pk_proposto * product.ricarico_id.aum_sciolto / 100) + product.aggiust_sciolto

    @api.onchange('confezione_vendita', 'confezione_acquisto', 'fornitore')
    def onchange_confezione_fornitore(self):
        dominio_v = [('conf_type', '=', 'Vendita')]
        dominio_a = [('conf_type', '=', 'Acquisto')]
        if self.fornitore:
            dominio_v.append(('fornitore', '=', self.fornitore.id))
            dominio_a.append(('fornitore', '=', self.fornitore.id))
        domain = {
            'confezione_vendita': dominio_v,
            'confezione_acquisto': dominio_a,
        }
        return {'domain': domain}

    @api.onchange('conv_rate')
    def onchange_conv_rate(self):
        if self.conv_rate < 0:
            self.conv_rate = 0

    def _get_converted_qty_available(self):
        for product in self:
            if product.conv_rate:
                product.qty_available_uom_base = product.qty_available * product.conv_rate

    def _get_all_qty(self):
        for product in self:
            qty_on_sale = 0
            qty_on_purchase = 0
            qty_prenotata = 0
            product_product = self.env['product.product'].search([('product_tmpl_id', '=', product.id)])
            for move in self.env['stock.move'].search([('product_id', '=', product_product.id),
                                                       ('to_refund', '=', False), ('picking_id', '!=', False)]):
                if move.picking_id.state != 'done':
                    if move.origin[0:2] == 'SO':
                        qty_on_sale += move.product_uom_qty
                    elif move.origin[0:2] == 'PO':
                        qty_on_purchase += move.product_uom_qty
                if move.purchase_line_id:
                    order_line = self.env['sale.order.line'].search([
                        ('purchase_id', '=', move.purchase_line_id.order_id.id)])
                    for line in order_line:
                        qty_prenotata += line.product_uom_qty - line.qty_delivered

            product.qty_on_sale = qty_on_sale
            product.qty_on_purchase = qty_on_purchase
            product.qty_proposta = (product.qty_ottimale + product.qty_on_sale) - \
                                   (product.qty_on_purchase + product.qty_available)
            product.qty_prenotata = qty_prenotata
            if product.qty_proposta < 0:
                product.qty_proposta = 0

    @api.onchange('qty_to_order')
    def onchange_qty_to_order(self):
        product_product = self.env['product.product'].search([('product_tmpl_id', '=', self._origin.id)])
        product = product_product.product_tmpl_id
        if product.fornitore:
            if product.confezione_acquisto:
                pack = product.confezione_acquisto
                if not self.qty_to_order % pack.qty == 0:
                    self.qty_effettiva = int(pack.qty * math.ceil(float(self.qty_to_order)/pack.qty))
                else:
                    self.qty_effettiva = self.qty_to_order

    def add_caratteristiche(self, vals, write=False):
        if write:
            all_ids = {}
            for category_value_id in self.category_value_ids:
                all_ids[category_value_id.id] = False

        na_category_value = self.env['na.category.value']
        categ_id = vals['categ_id']

        categ = self.env['product.category'].search([('id', '=', categ_id)])
        while categ:

            for caratteristica_id in categ.caratteristica_ids:
                car_id = caratteristica_id.id
                tipo_dato = caratteristica_id.tipo_dato
                categ_value = na_category_value.search([('product_id', '=', self.id), ('categ_id', '=', categ.id),
                                                        ('caratteristica_id', '=', car_id)])
                if not categ_value:
                    categ_value = na_category_value.create({
                        'product_id': self.id,
                        'categ_id': categ.id,
                        'caratteristica_id': car_id,
                        'type': tipo_dato,
                        'uom_id': caratteristica_id.uom_id.id,
                    })
                elif categ_value.type != tipo_dato:
                    categ_value.type = tipo_dato

                if write:
                    if categ_value.id in all_ids:
                        all_ids[categ_value.id] = True

            categ = categ.parent_id

        if write:
            for value in all_ids.items():
                if not value[1]:
                    category_remove = na_category_value.search([('id', '=', value[0])])
                    category_remove.unlink()

    def create_pattern(self, base_pattern):
        category_value_ids = self.category_value_ids
        for category_value in category_value_ids:
            codice_pattern = category_value.caratteristica_id.codice_pattern
            if codice_pattern:
                value_char = category_value.value_char
                if not value_char:
                    value_char = ''
                base_pattern = base_pattern.replace(codice_pattern, value_char)

                codice_uom = re.sub('<%', '', codice_pattern)
                codice_uom = re.sub('%>', '', codice_uom)
                codice_uom = '<%UM_' + codice_uom + '%>'

                uom_string = ''
                if category_value.uom_id:
                    uom_string = category_value.uom_id.name

                base_pattern = re.sub(codice_uom, uom_string, base_pattern)

        return base_pattern

    def get_pattern(self):
        tmp_categ = self.categ_id
        list_parent = []
        pattern_product = ''
        while tmp_categ:
            if tmp_categ.pattern_product and not pattern_product:
                pattern_product = tmp_categ.pattern_product
            list_parent.insert(0, tmp_categ)
            tmp_categ = tmp_categ.parent_id

        if pattern_product:
            x = 1
            while x <= 3:
                l_categ = '<%L' + str(x) + ' Categoria%>'
                new_string = ''
                try:
                    # if pattern_product == list_parent[x-1].pattern_product:
                    new_string = list_parent[x-1].name
                    # else:
                    #     new_string = list_parent[x-1].pattern_product
                except:
                    pass
                if not new_string:
                    new_string = ''
                pattern_product = re.sub(l_categ, new_string, pattern_product)

                x += 1

            return pattern_product
        return False

    @api.model
    def create(self, vals):
        if 'default_code' in vals:
            if not vals['default_code']:
                vals['default_code'] = self.env['ir.sequence'].next_by_code('na.rif.product.sequence')
        else:
            vals['default_code'] = self.env['ir.sequence'].next_by_code('na.rif.product.sequence')
        res = super(ProductTemplate, self).create(vals)
        if 'categ_id' in vals:
            if not res.name_pattern:
                pattern_product = res.get_pattern()
                if pattern_product:
                    res.name_pattern = res.description_sale_pattern = \
                        res.description_purchase_pattern = res.get_pattern()
            res.add_caratteristiche(vals)
        return res

    @api.multi
    def write(self, vals):
        res = super(ProductTemplate, self).write(vals)
        if 'categ_id' in vals:
            pattern_product = self.get_pattern()
            if pattern_product:
                self.name_pattern = self.description_sale_pattern = \
                    self.description_purchase_pattern = self.get_pattern()
            self.add_caratteristiche(vals, write=True)

        note_list = ['name', 'description_sale', 'description_purchase', 'description_picking', 'description_pickingout',
                     'description_pickingin']
        for note in note_list:
            if note in vals:
                return res
        for note in note_list:
            pattern_note = note + '_pattern'
            if self[pattern_note]:
                if note == 'name' and self.description_sale_pattern != self.name_pattern:
                    self.description_sale_pattern = self.name_pattern
                if note == 'name' and self.description_purchase_pattern != self.name_pattern:
                    self.description_purchase_pattern = self.name_pattern
                self.write({
                    note: self.create_pattern(base_pattern=self[pattern_note])
                })
        return res

    @api.multi
    def copy(self, default=None):
        res = super(ProductTemplate, self).copy(default=default)
        for product in res:
            for category_value_id in product.category_value_ids:
                category_value_id.unlink()

        for product in self:
            for category_value_id in product.category_value_ids:
                category_value_id.copy(default={'product_id': res.id})
        return res

    @api.multi
    def unlink(self):
        for product in self:
            for category_value_id in product.category_value_ids:
                category_value_id.unlink()
        return super(ProductTemplate, self).unlink()

    def open_product_form(self):
        if self.id:
            return {
                'res_id': self.id,
                'view_mode': 'form',
                'res_model': 'product.template',
                'type': 'ir.actions.act_window',
                'context': {},
            }

    @api.multi
    def create_purchase_orders(self):
        fornitori = {}
        for product in self.search([('id', 'in', self._context['active_ids'])]):
            if product.fornitore and product.qty_effettiva:
                if product.fornitore not in fornitori:
                    fornitori[product.fornitore] = [product]
                else:
                    fornitori[product.fornitore].append(product)
        for key in fornitori:
            if fornitori[key]:
                purchase_id = self.env['purchase.order'].create({
                    'partner_id': key.id,
                    'date_order': datetime.now(),
                    'date_planned': datetime.now(),
                    'payment_term_id': key.property_supplier_payment_term_id.id,
                })
                for product in fornitori[key]:
                    line = self.env['purchase.order.line'].create({
                        'order_id': purchase_id.id,
                        'product_id': self.env['product.product'].search([('product_tmpl_id', '=', product.id)]).id,
                        'name': product.description_purchase,
                        'date_planned': datetime.now(),
                        'product_qty': product.qty_effettiva,
                        'product_uom': product.uom_po_id.id,
                        'price_unit': product.standard_price,
                        'udm_base': product.uom_base.id if product.uom_base else None,
                        'qty_udm_base': product.qty_effettiva * product.conv_rate if product.conv_rate else None,
                    })
                    self.env['na.pacchi'].get_category_values(this=line)
                    if product.confezione_acquisto:
                        line.product_packaging = product.confezione_acquisto
                    product.qty_to_order = product.qty_effettiva = 0
        return False

    @api.multi
    def send_zapier_info(self):
        payload = {
            'name': self.name if self.name else ' ',
            'categ_id_complete_name': self.categ_id.complete_name if self.categ_id.complete_name else ' ',
            'default_code': self.default_code if self.default_code else ' ',
            'fornitore_name': self.fornitore.name if self.fornitore.name else ' ',
            'codice_fornitore': self.codice_fornitore if self.codice_fornitore else ' ',
            'list_price': self.list_price if self.list_price else ' ',
            'standard_price': self.standard_price if self.standard_price else ' ',
            'confezione_vendita_name': self.confezione_vendita.name.name if self.confezione_vendita.name else ' ',
            'confezione_vendita_qty': self.confezione_vendita.qty if self.confezione_vendita.qty else ' ',
            'confezione_acquisto_name': self.confezione_acquisto.name.name if self.confezione_acquisto.name else ' ',
            'confezione_acquisto_qty': self.confezione_acquisto.qty if self.confezione_acquisto.qty else ' ',
            'uom_base_name': self.uom_base.name if self.uom_base.name else ' ',
            'uom_id_name': self.uom_id.name if self.uom_id.name else ' ',
            'uom_po_id_name': self.uom_po_id.name if self.uom_po_id.name else ' ',
            'description': self.description if self.description else ' ',
            'qty_ottimale': self.qty_ottimale if self.qty_ottimale else ' ',
            'flag_pacco': 'Si' if self.flag_pacco else 'No',
            'flag_pacco_only': 'Si' if self.flag_pacco_only else 'No',
            'id': self.id if self.id else ' ',
        }

        self.users_sheet = [(4, self.env.uid)]

        try:
            r = requests.post(self.env['ir.config_parameter'].sudo().get_param(
                'nexapp.zap.update_etichetta_articolo_scaffale'), data=payload)
        except:
            pass
        return True


class PackagingName(models.Model):
    _name = 'product.packaging.name'

    name = fields.Char('Nome')


class ProductPackaging(models.Model):
    _inherit = 'product.packaging'

    priority = fields.Integer('Priorità')
    fornitore = fields.Many2one('res.partner', string='Fornitore', domain=[('supplier', '=', True)])
    conf_type = fields.Selection([('Vendita', 'Vendita'), ('Acquisto', 'Acquisto')], string='Tipo')

    name = fields.Many2one('product.packaging.name', string='Imballaggio', required=True)
