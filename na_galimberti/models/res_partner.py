from odoo import api, fields, models, tools, SUPERUSER_ID, _, exceptions
from odoo.modules import get_module_resource
import base64


class ResPartner(models.Model):
    _inherit = "res.partner"

    codid = fields.Char(string='Codice Prodotto')
    fax = fields.Char(string='Fax')
    clientid = fields.Char(string='Codice Prodotto')
    sorgente_cliente = fields.Many2one('res.partner', string='Sorgente')
    dipendente_gali = fields.Boolean(string='Dipendente Galimberti')

    @api.onchange('sorgente_cliente')
    def onchange_sorgente_cliente(self):
        if self._origin.id:
            domain = {'sorgente_cliente': [('id', '!=', self._origin.id)]}
            return {'domain': domain}

    def change_colore_on_kanban(self):
        for record in self:
            if record.state == 'to_check':
                color = 1
            elif record.state == 'quotation':
                color = 2
            elif record.state == 'invoice':
                color = 10
            elif record.state == 'cancel':
                color = 20
            else:
                color = 0
            record.color = color

    color = fields.Integer('Color Index', compute="change_colore_on_kanban")
    state = fields.Selection([
        ('to_check', 'Da Controllare'),
        ('quotation', 'Preventivi OK'),
        ('invoice', 'Fatturazione OK'),
        ('cancel', 'Obsoleto')
    ], string='Status', readonly=False, copy=False, index=True, default='to_check')
    parent_id = fields.Many2one('res.partner', string='Azienda Principale', index=True)
    contatto_id = fields.Many2one('res.partner')
    parent_ids = fields.One2many('res.partner', 'contatto_id', string='Aziende', index=True)
    aziende_ids = fields.Many2many(
        comodel_name="res.partner",  # required
        relation="na_contatti_aziende_rel",  # optional
        column1="contatto_id",  # optional
        column2="azienda_id",  # optional
    )
    contatti_ids = fields.Many2many(
        comodel_name="res.partner",  # required
        relation="na_contatti_aziende_rel",  # optional
        column1="azienda_id",  # optional
        column2="contatto_id",  # optional
    )
    email_extra = fields.Many2many(
        comodel_name="na.res.email",  # required
        relation="na_partner_email_rel",  # optional
        column1="partner_id",  # optional
        column2="email_id",  # optional
        string='Email Extra',
    )

    def _get_image_compute(self):
        for record in self:
            record.image_original = record.get_image()

    image_original = fields.Binary("Image", attachment=True, compute='_get_image_compute')

    product_ids = fields.One2many('product.template', 'fornitore', string='Prodotti')

    @api.multi
    def open_product_list(self):
        action = self.env.ref('stock.product_template_action_product').read()[0]
        action['domain'] = [('fornitore', '=', self.id)]
        return action

    @api.multi
    def change_state(self):
        state = self.env.context['state']
        self.active = False if state == 'cancel' else True
        self.write({'state': state})

    def get_image(self, vals={}):
        image = None
        if vals:
            is_company = vals
        else:
            is_company = self.is_company
        if is_company:
            img_path = get_module_resource('base', 'static/img', 'company_image.png')
        else:
            img_path = get_module_resource('base', 'static/img', 'avatar.png')
            # colorize = True

        if img_path:
            with open(img_path, 'rb') as f:
                image = f.read()

        if image:
            return tools.image_resize_image_big(base64.b64encode(image))

    @api.model
    def create(self, vals):
        res = super(ResPartner, self).create(vals)
        # model_email = res.env['na.res.email']
        # model_email.change_partner_id(res.email_extra)

        res.image_original = res.get_image([])

        return res

    @api.multi
    def write(self, vals):
        if 'is_company' in vals:
            vals['image_original'] = self.get_image(vals['is_company'])

        res = super(ResPartner, self).write(vals)

        # model_email = self.env['na.res.email']
        # model_email.change_partner_id(self.email_extra)

        return res

    # @api.multi
    # def unlink(self):
    #     for email in self.email_extra:
    #         email.unlink()
    #     return super(ResPartner, self).unlink()


class CopyResPartner(models.Model):
    _name = "na.copiarp2"

    highriseid = fields.Char(index=True)
    companyorperson = fields.Char(index=True)
    name = fields.Char(index=True)
    firstname = fields.Char(index=True)
    lastname = fields.Char(index=True)
    company = fields.Char(index=True)
    title = fields.Char(index=True)
    background = fields.Char(index=True)
    linkedinurl = fields.Char(index=True)
    tags = fields.Char(index=True)
    dates = fields.Char(index=True)
    addressworkstreet = fields.Char(index=True)
    addressworkcity = fields.Char(index=True)
    addressworkstate = fields.Char(index=True)
    addressworkzip = fields.Char(index=True)
    addressworkcountry = fields.Char(index=True)
    addresshomestreet = fields.Char(index=True)
    addresshomecity = fields.Char(index=True)
    addresshomestate = fields.Char(index=True)
    addresshomezip = fields.Char(index=True)
    addresshomecountry = fields.Char(index=True)
    addressotherstreet = fields.Char(index=True)
    addressothercity = fields.Char(index=True)
    addressotherstate = fields.Char(index=True)
    addressotherzip = fields.Char(index=True)
    addressothercountry = fields.Char(index=True)
    companyaddressworkstreet = fields.Char(index=True)
    companyaddressworkcity = fields.Char(index=True)
    companyaddressworkstate = fields.Char(index=True)
    companyaddressworkzip = fields.Char(index=True)
    companyaddressworkcountry = fields.Char(index=True)
    companyaddresshomestreet = fields.Char(index=True)
    companyaddresshomecity = fields.Char(index=True)
    companyaddresshomestate = fields.Char(index=True)
    companyaddresshomezip = fields.Char(index=True)
    companyaddresshomecountry = fields.Char(index=True)
    companyaddressotherstreet = fields.Char(index=True)
    companyaddressothercity = fields.Char(index=True)
    companyaddressotherstate = fields.Char(index=True)
    companyaddressotherzip = fields.Char(index=True)
    companyaddressothercountry = fields.Char(index=True)
    phonenumberwork = fields.Char(index=True)
    phonenumbermobile = fields.Char(index=True)
    phonenumberfax = fields.Char(index=True)
    phonenumberpager = fields.Char(index=True)
    phonenumberhome = fields.Char(index=True)
    phonenumberskype = fields.Char(index=True)
    phonenumberother = fields.Char(index=True)
    emailaddresswork = fields.Char(index=True)
    emailaddresshome = fields.Char(index=True)
    emailaddressother = fields.Char(index=True)
    webaddresswork = fields.Char(index=True)
    webaddresspersonal = fields.Char(index=True)
    webaddressother = fields.Char(index=True)
    twitteraccountpersonal = fields.Char(index=True)
    twitteraccountbusiness = fields.Char(index=True)
    twitteraccountother = fields.Char(index=True)
    companyphonenumberwork = fields.Char(index=True)
    companyphonenumbermobile = fields.Char(index=True)
    companyphonenumberfax = fields.Char(index=True)
    companyphonenumberpager = fields.Char(index=True)
    companyphonenumberhome = fields.Char(index=True)
    companyphonenumberskype = fields.Char(index=True)
    companyphonenumberother = fields.Char(index=True)
    companyemailaddresswork = fields.Char(index=True)
    companyemailaddresshome = fields.Char(index=True)
    companyemailaddressother = fields.Char(index=True)
    companywebaddresswork = fields.Char(index=True)
    companywebaddresspersonal = fields.Char(index=True)
    companywebaddressother = fields.Char(index=True)
    companytwitteraccountpersonal = fields.Char(index=True)
    companytwitteraccountbusiness = fields.Char(index=True)
    companytwitteraccountother = fields.Char(index=True)
    instantmessengerkindwork = fields.Char(index=True)
    instantmessengerwork = fields.Char(index=True)
    instantmessengerkindpersonal = fields.Char(index=True)
    instantmessengerpersonal = fields.Char(index=True)
    instantmessengerkindother = fields.Char(index=True)
    instantmessengerother = fields.Char(index=True)
    createdat = fields.Char(index=True)
    lastupdated = fields.Char(index=True)
    subscribed = fields.Char(index=True)
    addedby = fields.Char(index=True)
    cantierein = fields.Char(index=True)
    clientiid = fields.Char(index=True)
    descrizionelavoro = fields.Char(index=True)
    fatturato12mesi = fields.Char(index=True)
    fido = fields.Char(index=True)
    linkgdrive = fields.Char(index=True)
    linktrello = fields.Char(index=True)
    nonewsletter = fields.Char(index=True)
    note = fields.Char(index=True)
    piva = fields.Char(index=True)
    placeid = fields.Char(index=True)
    propietario = fields.Char(index=True)
    settore = fields.Char(index=True)
    settore2 = fields.Char(index=True)
    tipo = fields.Char(index=True)
