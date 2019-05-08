from odoo import api, fields, models, tools, SUPERUSER_ID, _, exceptions
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def update_reserved_qty(self, passa=False, back_record=None, old_reserved_moves=None):
        if passa:
            picking_ids = back_record
        for move in self.move_ids_without_package:
            order_line = None
            if move.purchase_line_id:
                order_line = self.env['sale.order.line'].search([
                    ('purchase_line_id', '=', move.purchase_line_id.id)])
                if order_line:
                    picking_ids = order_line.order_id.picking_ids
                    passa = True
            if passa:
                for pick in picking_ids:
                    if pick.state not in ['done', 'cancel']:
                        for sale_move in pick.move_ids_without_package:
                            if order_line:
                                if order_line.id != sale_move.sale_line_id.id:
                                    passa = False
                            if back_record:
                                if move.sale_line_id.id != sale_move.sale_line_id.id:
                                    passa = False

                            if passa:
                                # Corrispettivo di questo: sale_move.reserved_availability += move.quantity_done #
                                missing_reserved_uom_quantity = sale_move.product_uom_qty - \
                                                                sale_move.reserved_availability
                                need = sale_move.product_uom._compute_quantity(missing_reserved_uom_quantity,
                                                                               move.product_id.uom_id,
                                                                               rounding_method='HALF-UP')
                                if back_record:
                                    quantity_done = old_reserved_moves[move.id] - move.quantity_done
                                    stock_quant = self.env['stock.quant'].search([
                                        ('product_id', '=', move.product_id.id),
                                        ('location_id', '=', move.location_id.id)])
                                    stock_quant.sudo().reserved_quantity -= quantity_done
                                    # quantity_done = sale_move.sale_line_id
                                else:
                                    quantity_done = move.quantity_done
                                sale_move._update_reserved_quantity(
                                    need, quantity_done, sale_move.location_id,
                                    package_id=sale_move.package_level_id.package_id, strict=False)
                                # ------------------------------------------------------------------------------ #
                                break
                            passa = True
                        # pick.action_assign()

    @api.multi
    def action_done(self):
        old_reserved_moves = {}
        for move in self.move_ids_without_package:
            old_reserved_moves[move.id] = move.reserved_availability
        res = super(StockPicking, self).action_done()

        # todo_moves = self.mapped('move_ids_without_package').filtered(lambda self: self.state in ['done'])
        # pacco = None
        # pacco_order = None
        # num_pacchi = 1
        # for move in todo_moves:
        #     move_type = move.get_order_origin_type()
        #     confezione_prodotto = 0
        #     if move_type == 'sale':
        #         confezione_prodotto = move.product_id.product_tmpl_id.confezione_vendita.qty
        #     elif move_type == 'purchase':
        #         confezione_prodotto = move.product_id.product_tmpl_id.confezione_acquisto.qty
        #     if move.product_id.product_tmpl_id.flag_pacco:
        #         crea_pacco = True
        #         if move.code_picking == 'incoming':
        #             crea_pacco = False
        #             if move.product_id.product_tmpl_id.flag_pacco_only:
        #                 pacco_product = self.env['na.pacchi.product'].search(
        #                     [('product_id', '=', move.product_id.product_tmpl_id.id), ('flag_order', '=', False)])
        #                 if pacco_product:
        #                     pacco = pacco_product.n_pacco
        #                 else:
        #                     crea_pacco = True
        #             elif confezione_prodotto > 0:
        #                 y = confezione_prodotto
        #                 num_pacchi = 0
        #                 while y < move.quantity_done:
        #                     num_pacchi += 1
        #                     y += confezione_prodotto
        #                 if y != move.quantity_done:
        #                     num_pacchi += 1
        #                 crea_pacco = True
        #             else:
        #                 crea_pacco = True
        #             if crea_pacco:
        #                 values = {
        #                     'flag_readonly': True,
        #                 }
        #         elif move.code_picking != 'incoming' and not pacco:
        #             values = {
        #                 'flag_readonly': True,
        #                 'flag_order': True,
        #             }
        #
        #         x = 0
        #         lista_pacco_to_id = []
        #         quantita_tot = qty = move.quantity_done
        #         while x < num_pacchi:
        #             if not move.flag_no_conf:
        #                 if confezione_prodotto > 0:
        #                     if confezione_prodotto <= quantita_tot:
        #                         qty = confezione_prodotto
        #                         quantita_tot -= qty
        #                     else:
        #                         qty = quantita_tot
        #                         quantita_tot = 0
        #             else:
        #                 qty = move.quantity_done
        #                 x = num_pacchi
        #
        #             if crea_pacco:
        #                 if move.code_picking == 'incoming' or not pacco_order:
        #                     pacco = self.env['na.pacchi'].create(values)
        #                     if move.code_picking != 'incoming':
        #                         pacco_order = pacco
        #                 self.env['na.pacchi.product'].create({
        #                     'product_id': move.product_id.product_tmpl_id.id,
        #                     'lunghezza': move.lunghezza,
        #                     'larghezza': move.larghezza,
        #                     'spessore': move.spessore,
        #                     'diametro': move.diametro,
        #                     'qty': qty,
        #                     'n_pacco': pacco.id,
        #                 })
        #             else:
        #                 pacco_product.qty += qty
        #             lista_pacco_to_id.append(pacco.id)
        #             x += 1
        #         move.write({
        #             'pacco_to': [(6, 0, lista_pacco_to_id)]
        #         })
        #
        #         if move.code_picking != 'incoming':
        #             if move.pacco_from:
        #                 product_from = move.pacco_from.pacchi_product.filtered(
        #                     lambda x: x.product_id == move.product_id.product_tmpl_id)
        #                 product_from.update_qty()

        ################################################################################################################
        if self.sale_id:
            if self.sale_id.acquisto_associato:
                new_backorder = self.search([('backorder_id', '=', self.id), ('state', 'not in', ['done', 'cancel'])])
                if new_backorder:
                    new_backorder.do_unreserve()
                    self.update_reserved_qty(passa=True, back_record=new_backorder,
                                             old_reserved_moves=old_reserved_moves)
                else:
                    self.update_reserved_qty()
        else:
            self.update_reserved_qty()

        return res

    # @api.multi
    # def write(self, vals):
    #     if 'move_ids_without_package' in vals:
    #         for move in vals['move_ids_without_package']:
    #             values = move[-1]
    #             if values:
    #                 if 'quantity_done' in values or 'pacco_from' in values:
    #                     move_id = self.env['stock.move'].search([('id', '=', move[1])])
    #                     if 'pacco_from' in values:
    #                         pacco_from = self.env['na.pacchi'].search([('id', 'in', values['pacco_from'][0][-1])])
    #                     else:
    #                         pacco_from = move_id.pacco_from
    #
    #                     if 'quantity_done' in values:
    #                         quantity_done = values['quantity_done']
    #                     else:
    #                         quantity_done = move_id.quantity_done
    #
    #                     for pacco in pacco_from:
    #                         pacco_product = pacco.pacchi_product.filtered(
    #                             lambda x: x.product_id == move_id.product_id.product_tmpl_id)
    #                         if pacco_product:
    #                             if (pacco_product.qty_reserved + quantity_done) <= pacco_product.qty:
    #                                 pacco_product.qty_reserved += quantity_done
    #                             else:
    #                                 raise UserError("La quantita' richiesta non e' presente nel pacco selezionato."
    #                                                 "Si prega di cambiare il pacco di provenienza oppure la quantita'.")
    #     res = super(StockPicking, self).write(vals)
    #     return res


class StockMove(models.Model):
    _inherit = 'stock.move'

    lunghezza = fields.Char(string='Lunghezza')
    larghezza = fields.Char(string='Larghezza')
    spessore = fields.Char(string='Spessore')
    diametro = fields.Char(string='Diametro')

    def get_order_origin_type(self):
        domain = [('name', '=', self.origin)]
        if self.env['sale.order'].search(domain):
            return 'sale'
        elif self.env['purchase.order'].search(domain):
            return 'purchase'
        else:
            return False

    @api.onchange('product_id')
    def onchange_product_id(self):
        self.env['na.pacchi'].get_category_values(this=self)

    def get_domain_pacchi(self):
        domain = [(1, '=', 2)]
        if self.product_id.flag_pacco:
            lista_id = []
            for pacco_product in self.product_id.pacchi_ids:
                lista_id.append(pacco_product.n_pacco.id)
            domain = [('id', 'in', lista_id)]
        return str(domain)

    @api.onchange('product_id', 'pacco_from', 'pacco_to')
    def onchange_pacchi(self):
        domain = self.get_domain_pacchi()

        dominio = {
            "pacco_to": domain,
            "pacco_from": domain,
        }
        return {'domain': dominio}

    pacco_from = fields.Many2many('na.pacchi', 'move_pacco_from_rel', string='Pacco Provenienza')
    pacco_to = fields.Many2many('na.pacchi', 'move_pacco_to_rel', string='Pacchi Destinazione')

    code_picking = fields.Selection(related='picking_type_id.code')
    flag_pacco = fields.Boolean(related='product_id.flag_pacco')
    flag_no_conf = fields.Boolean('No Confezione')

    pacchi_ids = fields.Many2many('na.pacchi', compute='_get_ids')

    @api.multi
    def _get_ids(self):
        for s in self:
            if s.product_id and s.product_id.flag_pacco:
                lista_id = []
                for pacco in s.product_id.pacchi_ids:
                    lista_id.append(pacco.n_pacco.id)
                pacchi = self.env['na.pacchi'].search([('id', 'in', lista_id)])

                if pacchi:
                    s.pacchi_ids = pacchi
