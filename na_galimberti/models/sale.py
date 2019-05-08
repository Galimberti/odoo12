from odoo import api, fields, models, tools, SUPERUSER_ID, _, exceptions
from odoo.exceptions import UserError
from odoo.tools import float_compare
from .pacchi import value_list
import requests
import json
import datetime
import base64


class SaleMacrocategorie(models.Model):
    _name = 'sale.macrocategorie'

    sale_id = fields.Many2one('sale.order', string='Ordine di Vendita')
    categ_id = fields.Many2one('product.category', string='Categoria', readonly=True)
    sum_costo = fields.Float('Somma Costo', readonly=True)
    costo_preventivato = fields.Float('Costo Preventivato')
    differenza = fields.Float()

    @api.multi
    def write(self, vals):
        if 'sum_costo' in vals:
            sum_costo = vals['sum_costo']
        else:
            sum_costo = self.sum_costo

        if 'costo_preventivato' in vals:
            costo_preventivato = vals['costo_preventivato']
        else:
            costo_preventivato = self.costo_preventivato

        vals['differenza'] = costo_preventivato - sum_costo
        return super(SaleMacrocategorie, self).write(vals)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    associa_acquisto = fields.Boolean('Associa Ordine di Acquisto', copy=False)
    acquisto_associato = fields.Boolean('Acquisto Associato', copy=False)

    users_sheet = fields.Many2many('res.users', string='Utente richiesta ZAP')
    stamp_gsheet = fields.Datetime()

    macrocategorie = fields.One2many('sale.macrocategorie', 'sale_id', string='Macrocategorie')

    prezzo_privato = fields.Boolean('Prezzo Privato')

    def create_linked_purchase(self):
        if self.associa_acquisto:
            if self.order_line:
                forn_dict = {}
                for line in self.order_line:
                    fornitore = line.product_id.fornitore
                    if fornitore:
                        if fornitore.id in forn_dict:
                            purchase = forn_dict[fornitore.id]
                        else:
                            purchase = self.env['purchase.order'].create({
                                'partner_id': fornitore.id,
                                'date_order': self.create_date,
                                'date_planned': self.create_date,
                            })
                            forn_dict[fornitore.id] = purchase

                        purchase_line = self.env['purchase.order.line'].create({
                            'product_id': line.product_id.id,
                            'name': line.name,
                            'lunghezza': line.lunghezza,
                            'larghezza': line.larghezza,
                            'spessore': line.spessore,
                            'diametro': line.diametro,
                            'product_packaging': line.product_id.confezione_vendita.id,
                            'date_planned': line.create_date,
                            'product_qty': line.product_uom_qty,
                            'product_uom': line.product_uom.id,
                            'price_unit': line.price_unit,
                            'taxes_id': [(6, 0, line.tax_id.ids)],
                            'order_id': purchase.id,
                        })

                        line.purchase_id = purchase.id
                        line.purchase_line_id = purchase_line.id
                        if not self.acquisto_associato:
                            self.acquisto_associato = True
                    else:
                        raise UserError('Errore! Non tutti i prodotti hanno un fornitore associato.')

    @api.multi
    def _action_confirm(self):
        super(SaleOrder, self)._action_confirm()
        for order in self:
            order.order_line.na_action_launch_procurement_rule()
            picking = self.env['stock.picking'].search([('sale_id', '=', order.id)])
            if picking:
                picking.do_unreserve()
        self.create_linked_purchase()

    @api.multi
    def send_zapier_info(self):
        state = 'Preventivo' if self.state == 'draft' else ''
        state = 'Preventivo inviato' if self.state == 'sent' and not state else state
        state = 'Ordine di vendita' if self.state == 'sale' and not state else state
        state = 'Bloccato' if self.state == 'done' and not state else state
        state = 'Annullato' if self.state == 'cancel' and not state else state

        payload = [[
            self.name if self.name else ' ',
            self.partner_id.name if self.partner_id.name else ' ',
            self.partner_id.street if self.partner_id.street else ' ',
            self.partner_id.city if self.partner_id.city else ' ',
            self.partner_id.zip if self.partner_id.zip else ' ',
            self.partner_id.state_id.name if self.partner_id.state_id.name else ' ',
            self.partner_id.country_id.name if self.partner_id.country_id.name else ' ',
            self.confirmation_date if self.confirmation_date else ' ',
            self.payment_term_id.name if self.payment_term_id.name else ' ',
            self.user_id.name if self.user_id else ' ',
            self.client_order_ref if self.client_order_ref else ' ',
            self.note if self.note else ' ',
            self.amount_untaxed if self.amount_untaxed else 0,
            self.amount_tax if self.amount_tax else 0,
            self.amount_total if self.amount_total else 0,
            state,
            self.id if self.id else None,
        ]]

        for line in self.order_line:
            payload.append([
                line.product_id.name if line.product_id.name else ' ',
                line.name if line.name else ' ',
                line.lunghezza if line.lunghezza else ' ',
                line.larghezza if line.larghezza else ' ',
                line.spessore if line.spessore else ' ',
                line.diametro if line.diametro else ' ',
                line.product_packaging.name if line.product_packaging.name else ' ',
                line.product_uom_qty if line.product_uom_qty else 0,
                line.qty_delivered if line.qty_delivered else 0,
                line.qty_invoiced if line.qty_invoiced else 0,
                line.product_uom.name if line.product_uom.name else ' ',
                line.price_unit if line.price_unit else 0,
                line.price_subtotal if line.price_subtotal else 0,
                line.product_id.default_code if line.product_id.default_code else '',
            ])

        self.users_sheet = [(4, self.env.uid)]

        def myconverter(o):
            if isinstance(o, datetime.datetime):
                return o.__str__()

        pbase64 = base64.b64encode(bytes(json.dumps(payload, default=myconverter), 'utf-8'))
        pbase64 = "".join(map(chr, pbase64))
        payload_json = json.dumps({'payload': pbase64, 'file_name': self.name + '_' + state, 'order_id': self.id},
                                  default=myconverter)
        try:
            r = requests.post(self.env['ir.config_parameter'].sudo().get_param(
                'nexapp.zap.update_dati_vendita'), data=payload_json)
        except:
            pass
        return True


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    lunghezza = fields.Char(string='Lunghezza')
    larghezza = fields.Char(string='Larghezza')
    spessore = fields.Char(string='Spessore')
    diametro = fields.Char(string='Diametro')
    purchase_id = fields.Many2one('purchase.order', string='Ordine Acquisto', readonly=True, copy=False)
    purchase_line_id = fields.Many2one('purchase.order.line', string='Riga Ordine Acquisto', copy=False)

    qty_udm_base = fields.Float(string='Q.ty UdM Base', copy=False)
    udm_base = fields.Many2one('uom.uom', string='UdM Base', copy=False)

    @api.onchange('product_id', 'product_uom_qty')
    def onchange_qty_get_udm_base(self):
        if self.product_id:
            product_template = self.product_id.product_tmpl_id
            if product_template.uom_base:
                self.udm_base = product_template.uom_base.id
                if self.product_uom_qty and product_template.conv_rate:
                    self.qty_udm_base = self.product_uom_qty * product_template.conv_rate

    @api.onchange('qty_udm_base')
    def onchange_get_qty(self):
        if self.product_id:
            product_template = self.product_id.product_tmpl_id
            if product_template.uom_base:
                if self.qty_udm_base and product_template.conv_rate:
                    self.product_uom_qty = self.qty_udm_base / product_template.conv_rate

    def get_macrocategoria_values(self):
        categ_id = self.product_id.categ_id
        while categ_id.parent_id:
            categ_id = categ_id.parent_id

        costo = self.product_id.standard_price * self.product_uom_qty

        return self.env['sale.macrocategorie'].search([('sale_id', '=', self.order_id.id),
                                                       ('categ_id', '=', categ_id.id)]), categ_id, costo

    @api.model
    def create(self, vals):
        res = super(SaleOrderLine, self).create(vals)

        macrocategoria, categ_id, costo = res.get_macrocategoria_values()

        if macrocategoria:
            macrocategoria.sum_costo += costo
        else:
            macrocategoria.create({
                'sale_id': res.order_id.id,
                'categ_id': categ_id.id,
                'sum_costo': costo,
            })

        return res

    @api.multi
    def write(self, vals):
        if 'product_uom_qty' in vals:
            macrocategoria, categ_id, costo = self.get_macrocategoria_values()
            if macrocategoria:
                macrocategoria.sum_costo -= costo

        res = super(SaleOrderLine, self).write(vals)

        if 'product_uom_qty' in vals:
            macrocategoria, categ_id, costo = self.get_macrocategoria_values()
            if macrocategoria:
                macrocategoria.sum_costo += costo

        if 'qty_udm_base' not in vals and 'udm_base' not in vals:
            self.onchange_qty_get_udm_base()
        return res

    @api.multi
    def unlink(self):
        macrocategoria, categ_id, costo = self.get_macrocategoria_values()
        if macrocategoria:
            macrocategoria.sum_costo -= costo
            if macrocategoria.sum_costo == 0:
                macrocategoria.unlink()

        return super(SaleOrderLine, self).unlink()

    @api.onchange('product_id')
    def onchange_product_id(self):
        self.env['na.pacchi'].get_category_values(this=self)

    @api.onchange('product_id')
    def onchange_product_id_warning_pacco_only(self):
        if self.product_id.flag_pacco_only:
            warning = {}
            title = _("Warning")
            message = 'Questo è un prodotto con Pacco Unico'
            warning['title'] = title
            warning['message'] = message
            result = {'warning': warning}
            return result
        return {}

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        if not self.product_id:
            return {'domain': {'product_uom': []}}

        vals = {}
        domain = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
        if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
            vals['product_uom'] = self.product_id.uom_id
            vals['product_uom_qty'] = 1.0

        product = self.product_id.with_context(
            lang=self.order_id.partner_id.lang,
            partner=self.order_id.partner_id.id,
            quantity=vals.get('product_uom_qty') or self.product_uom_qty,
            date=self.order_id.date_order,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.product_uom.id
        )

        result = {'domain': domain}

        warning = {}
        if product.sale_line_warn != 'no-message':
            title = _("Warning for %s") % product.name
            message = product.sale_line_warn_msg
            warning['title'] = title
            warning['message'] = message
            result = {'warning': warning}
            if product.sale_line_warn == 'block':
                self.product_id = False
                return result

        if product.description_sale:
            vals['name'] = product.description_sale
        if product.confezione_vendita:
            vals['product_packaging'] = product.confezione_vendita

        self._compute_tax_id()
        self.update(vals)

        return result

    @api.onchange('product_id')
    def onchange_product_get_price(self):
        product = self.product_id
        if not self.order_id.prezzo_privato:
            if product.prezzo_impresa:
                self.price_unit = product.prezzo_impresa
        else:
            if product.prezzo_privato:
                self.price_unit = product.prezzo_privato
        if not self.price_unit:
            if self.order_id.pricelist_id and self.order_id.partner_id:
                self.price_unit = self.env['account.tax']._fix_tax_included_price_company(
                    self._get_display_price(product), product.taxes_id, self.tax_id, self.company_id)

    @api.multi
    def na_action_launch_procurement_rule(self):
        """
        Launch procurement group run method with required/custom fields genrated by a
        sale order line. procurement group will launch '_run_move', '_run_buy' or '_run_manufacture'
        depending on the sale order line product rule.
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        errors = []
        for line in self:
            if line.state != 'sale' or not line.product_id.type in ('consu', 'product'):
                continue
            qty = 0.0
            for move in line.move_ids.filtered(lambda r: r.state != 'cancel'):
                qty += move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom,
                                                          rounding_method='HALF-UP')
            if float_compare(qty, line.product_uom_qty, precision_digits=precision) >= 0:
                continue

            group_id = line.order_id.procurement_group_id
            if not group_id:
                group_id = self.env['procurement.group'].create({
                    'name': line.order_id.name, 'move_type': line.order_id.picking_policy,
                    'sale_id': line.order_id.id,
                    'partner_id': line.order_id.partner_shipping_id.id,
                })
                line.order_id.procurement_group_id = group_id
            else:
                # In case the procurement group is already created and the order was
                # cancelled, we need to update certain values of the group.
                updated_vals = {}
                if group_id.partner_id != line.order_id.partner_shipping_id:
                    updated_vals.update({'partner_id': line.order_id.partner_shipping_id.id})
                if group_id.move_type != line.order_id.picking_policy:
                    updated_vals.update({'move_type': line.order_id.picking_policy})
                if updated_vals:
                    group_id.write(updated_vals)

            values = line._prepare_procurement_values(group_id=group_id)

            ############################################################################################################

            for value in value_list:
                values[value] = line[value]

            ############################################################################################################

            product_qty = line.product_uom_qty - qty

            procurement_uom = line.product_uom
            quant_uom = line.product_id.uom_id
            get_param = self.env['ir.config_parameter'].sudo().get_param
            if procurement_uom.id != quant_uom.id and get_param('stock.propagate_uom') != '1':
                product_qty = line.product_uom._compute_quantity(product_qty, quant_uom, rounding_method='HALF-UP')
                procurement_uom = quant_uom

            try:
                self.env['procurement.group'].run(line.product_id, product_qty, procurement_uom,
                                                  line.order_id.partner_shipping_id.property_stock_customer, line.name,
                                                  line.order_id.name, values)
            except UserError as error:
                errors.append(error.name)
        if errors:
            raise UserError('\n'.join(errors))
        return True
