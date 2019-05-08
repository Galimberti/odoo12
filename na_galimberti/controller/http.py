# -*- coding: utf-8 -*-
import logging
# import re
from odoo import http
from odoo.http import request
from datetime import datetime


_logger = logging.getLogger(__name__)


class Controller(http.Controller):

    @http.route('/zapier/receive_pdf', methods=['GET'], type='http', auth='none', cors='*')
    def receive_pdf(self, url=None, order_id=None, order_type=None):
        # try:
        if url and order_id and order_type:
            request.session.authenticate('galimberti', 'admin', 'Galpwd2018!')

            order = http.request.env[order_type].search([('id', '=', order_id)])
            if not order:
                return '{"response": "ERROR"}'

            if order_type == 'sale.order':
                body = "Stampa ordine di vendita creata con successo<br><a href='" + url + "&portrait=false'"
            elif order_type == 'purchase.order':
                body = "Stampa ordine di acquisto creata con successo<br><a href='" + url + "&portrait=false'"
            elif order_type == 'product.template':
                body = "Stampa etichetta articolo creata con successo<br><a href='" + url + "'"
            else:
                return '{"response": "ERROR"}'

            body += " target='_blank'>Clicca qui</a>"

            if order.users_sheet:
                for user_id in order.users_sheet:
                    user_id.notify_info(message=body, title='Stampa pronta!', sticky=True)

            order.stamp_gsheet = datetime.now()

            return '{"response": "OK"}'
        return '{"response": "ERROR"}'
        # except:
        #     return '{"response": "ERROR"}'
