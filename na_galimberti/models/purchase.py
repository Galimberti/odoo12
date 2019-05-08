from odoo import api, fields, models, tools, SUPERUSER_ID, _, exceptions
from .pacchi import value_list
import requests
import json
import datetime
import base64


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    flag_supplier_product = fields.Boolean('Prodotti Fornitore')
    opportunity_id = fields.Many2one('crm.lead', string='Opportunità', domain="[('type', '=', 'opportunity')]")

    sale_order_lines = fields.One2many('sale.order.line', 'purchase_id', string='Righe Ordine di Vendita')

    destinazione = fields.Char('Destinazione', default='Via del Mulino 21 Lomagna LC 23871 Lombardia IT')
    referente = fields.Many2one('res.partner', string='Referente')
    note = fields.Text('Note')

    users_sheet = fields.Many2many('res.users', string='Utente richiesta ZAP')
    stamp_gsheet = fields.Datetime()

    @api.multi
    def send_zapier_info(self):
        state = 'RDP' if self.state == 'draft' else ''
        state = 'RDP Inviata' if self.state == 'sent' and not state else state
        state = 'Da approvare' if self.state == 'to approve' and not state else state
        state = 'Ordine di acquisto' if self.state == 'purchase' and not state else state
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
            self.destinazione if self.destinazione else ' ',
            self.date_order if self.date_order else ' ',
            self.date_planned if self.date_planned else ' ',
            self.payment_term_id.name if self.payment_term_id.name else ' ',
            self.partner_ref if self.partner_ref else ' ',
            self.referente.name if self.referente else ' ',
            self.note if self.note else ' ',
            self.notes if self.notes else ' ',
            self.amount_untaxed if self.amount_untaxed else 0,
            self.amount_tax if self.amount_tax else 0,self.amount_total if self.amount_total else 0,
            state,
            self.incoterm_id.name if self.incoterm_id.name else ' ',
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
                line.qty_received if line.qty_received else 0,
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
                'nexapp.zap.update_dati_acquisto'), data=payload_json)
        except:
            pass
        return True


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    lunghezza = fields.Char(string='Lunghezza')
    larghezza = fields.Char(string='Larghezza')
    spessore = fields.Char(string='Spessore')
    diametro = fields.Char(string='Diametro')

    product_packaging = fields.Many2one('product.packaging', string='Confezione', default=False)

    qty_udm_base = fields.Float(string='Q.ty UdM Base', copy=False)
    udm_base = fields.Many2one('uom.uom', string='UdM Base', copy=False)

    @api.onchange('product_id', 'product_qty')
    def onchange_qty_get_udm_base(self):
        if self.product_id:
            product_template = self.product_id.product_tmpl_id
            if product_template.uom_base:
                self.udm_base = product_template.uom_base.id
                if self.product_qty and product_template.conv_rate:
                    self.qty_udm_base = self.product_qty * product_template.conv_rate

    @api.onchange('qty_udm_base')
    def onchange_get_qty(self):
        if self.product_id:
            product_template = self.product_id.product_tmpl_id
            if product_template.uom_base:
                if self.qty_udm_base and product_template.conv_rate:
                    self.product_qty = self.qty_udm_base / product_template.conv_rate

    @api.onchange('product_packaging')
    def _onchange_product_packaging(self):
        if self.product_packaging:
            return self._check_package()

    @api.multi
    def _check_package(self):
        default_uom = self.product_id.uom_po_id
        pack = self.product_packaging
        qty = self.product_qty
        q = default_uom._compute_quantity(pack.qty, self.product_uom)
        if qty and q and (qty % q):
            newqty = qty - (qty % q) + q
            return {
                'warning': {
                    'title': _('Avviso'),
                    'message': _("Questo prodotto è confezionato in %.2f %s. Dovresti vendere %.2f %s.") % (
                        pack.qty, default_uom.name, newqty, self.product_uom.name),
                },
            }
        return {}

    @api.onchange('product_id')
    def onchange_product_id(self):
        self.env['na.pacchi'].get_category_values(this=self)
        if self.product_id:
            self.price_unit = self.product_id.standard_price
            if self.product_id.uom_po_id:
                self.product_uom = self.product_id.uom_po_id.id
            if self.product_id.description_purchase:
                self.name = self.product_id.description_purchase

            if self.product_id.confezione_acquisto:
                self.product_packaging = self.product_id.confezione_acquisto

        if self.order_id.flag_supplier_product:
            dominio = {
                "product_id": [('fornitore', '=', self.order_id.partner_id.id)],
            }
            return {'domain': dominio}

    @api.multi
    def _create_stock_moves(self, picking):
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        for line in self:
            for val in line._prepare_stock_moves(picking):
                for value in value_list:
                    val[value] = line[value]
                done += moves.create(val)
        return done
