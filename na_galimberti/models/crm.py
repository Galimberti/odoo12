from odoo import api, fields, models, tools, SUPERUSER_ID, _, exceptions
import requests


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    fornitore_id = fields.Many2one('res.partner', string='Fornitore', domain=[('supplier', '=', True)])
    vendor_id = fields.Many2one('res.partner', string='Responsabile Gali', domain=[('dipendente_gali', '=', True)])
    settore = fields.Many2one('na.settore', string='Settore')
    stato_lavoro = fields.Many2one('na.stato.lavoro', string='Stato Lavoro')
    consegna_probabile = fields.Char('Consegna Probabile')
    durata_fornitura = fields.Char('Durata Fornitura')
    tipo_offerta = fields.Selection([('Opportunità di Vendita', 'Opportunità di Vendita'),
                                     ('Richiesta di Offerta', 'Richiesta di Offerta')], string='Tipo Opportunità',
                                    default='Opportunità di Vendita')
    referenti_cliente = fields.Many2many('res.partner', string='Referente/i Cliente', domain=[])
    cliente_finale = fields.Many2one('res.partner', string='Cliente Finale')
    sorgente_deal = fields.Many2one('res.partner', string='Sorgente')

    purchase_number = fields.Integer(compute='_compute_purchase_amount_total', string="Number of Quotations")
    purchase_ids = fields.One2many('purchase.order', 'opportunity_id', string='Acquisti')

    @api.depends('purchase_ids')
    def _compute_purchase_amount_total(self):
        for lead in self:
            nbr = 0
            for order in lead.purchase_ids:
                if order.state != 'cancel':
                    nbr += 1
            lead.purchase_number = nbr

    @api.onchange('partner_id', 'fornitore_id')
    def onchange_for_referenti_cliente(self):
        pf_id = None
        if self.partner_id:
            pf_id = self.partner_id.id
        elif self.fornitore_id:
            pf_id = self.fornitore_id.id

        if pf_id:
            domain = {'referenti_cliente': [('parent_id', '=', pf_id)]}
            return {'domain': domain}

    @api.onchange('tipo_offerta')
    def tipo_offerta_onchange(self):
        if self.tipo_offerta == 'Richiesta di Offerta':
            self.partner_id = None
        else:
            self.fornitore_id = None

    @api.multi
    def create_trello_card(self):
        payload = {
            'intestazione_card': self.name,
            'id_deal': self.id,
            'nome_creatore': self.user_id.name,
            'nome_responsabile': self.user_id.name,
            'GDrive': '',
            'GGroup': '',
            'Gmail': '',
        }
        try:
            r = requests.post(self.env['ir.config_parameter'].sudo().get_param('nexapp.zap.crea_card_in_trello'),
                              data=payload)
        except:
            pass


class Settore(models.Model):
    _name = 'na.settore'

    name = fields.Char('Nome Settore')


class StatoLavoro(models.Model):
    _name = 'na.stato.lavoro'

    name = fields.Char('Nome Stato Lavoro')
