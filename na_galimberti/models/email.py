from odoo import api, fields, models, tools, SUPERUSER_ID, _, exceptions


class ResEmail(models.Model):
    _name = "na.res.email"

    name = fields.Char('Email', required=True)
    partner_id_domain = fields.Integer()
    partner_id = fields.Many2many(
        comodel_name="res.partner",  # required
        relation="na_partner_email_rel",  # optional
        column1="email_id",  # optional
        column2="partner_id",  # optional
    )

    def change_partner_id(self, email_ids):
        for email_id in email_ids:
            if email_id.partner_id:
                email_id.partner_id_domain = email_id.partner_id.id
