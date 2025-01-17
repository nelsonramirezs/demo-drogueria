# coding: utf-8
##############################################################################
import time

from odoo import api
from odoo import fields, models
from odoo import exceptions
from odoo.tools.translate import _
from odoo.addons import decimal_precision as dp


class IslrWhDoc(models.Model):


    def name_get(self):
        if not len(self.ids):
            return []
        res = []
        for item in self.browse():
            if item.number and item.state == 'done':
                res.append((item.id, '%s (%s)' % (item.number, item.name)))
            else:
                res.append((item.id, '%s' % (item.name)))
        return res
    @api.model
    def _get_type(self):
        """ Return type of invoice or returns in_invoice
        """
        if self._context is None:
            self.context = {}
        inv_type = self._context.get('type', 'in_invoice')
        return inv_type

    '''@api.model
    def _get_journal(self):

        """ Return a iva journal depending of invoice type
        """
        
        partner_id = self._context.get('uid')
        partner = self.env['res.partner'].search([('id', '=', partner_id)])
        purchase_journal_id = partner.purchase_journal_id.id
        res = self.env['account.journal'].search([('id', '=', purchase_journal_id)])
        return res'''

    @api.model
    def _get_journal(self,partner_id=None):
        #Return a islr journal depending on the type of bill

        #if self._context is None:
        #    self.context = {}
        #journal_obj = self.env['account.journal']
        #user_obj = self.env['res.users']
        #company_id = user_obj.browse(self._uid).company_id.id
        filtro = partner_id
        if not partner_id:

            #partner_id = self.env['res.partner'].search([('id', '=', self._context.get('uid'))])
            company = self.env.user.sudo().company_id
            filtro = company.partner_id
        if self._context.get('type') in ('out_invoice', 'out_refund'):
            res = filtro.sale_islr_journal_id
                #journal_obj.search([('type', '=', 'islr_sale'),
                 #                     ('company_id', '=', company_id)], limit=1)
        else:
            res = filtro.purchase_islr_journal_id
                #journal_obj.search([(
                #'type', '=', 'islr_purchase')], limit=1)
        if res:
            return res
        else:
            raise exceptions.except_orm(
                _('Configuration Incomplete.'),
                _("No se encuentra un diario para ejecutar la retención ISLR"
                  " automáticamente, cree uno en vendedor/proveedor > "
                  "contabilidad > Diario de retencion ISLR"))
            return False


        '''context = dict(self._context or {})
        type_inv = context.get('type', 'in_invoice')
        type2journal = {'out_invoice': 'islr_sale',
                        'in_invoice': 'islr_purchase'}
        journal_obj = self.env['account.journal']
        user = self.env['res.users'].browse()
        company_id = context.get('company_id', user.company_id.id)
        domain = [('company_id', '=', company_id)]
        domain += [('type', '=', type2journal.get(
            type_inv, 'islr_purchase'))]
        res = journal_obj.search(domain, limit=1)
        return res and res[0] or False'''

    @api.model
    def _get_currency(self):
        """ Return the currency of the current company
        """
        user = self.env['res.users'].browse(self._uid)
        if user.company_id:
            return user.company_id.currency_id.id
        else:
            return self.env['res.currency'].search(
                 [('rate', '=', 1.0)])[0]


    def _get_amount_total(self):
        """ Return the cumulative amount of each line
        """
        res = {}
        for rete in self.browse():
            res[rete.id] = 0.0
            for line in rete.concept_ids:
                res[rete.id] += line.amount
        return res

    def _get_company(self):
        res_company = self.env['res.company'].search([('id', '=', self.company_id.id)])
        return res_company
    # @api.onchange('date_ret')

    def retencion_seq_get(self):
        #TODO REVISAR ESTA SECUENCIA SALTA UN NUMERO
        local_number = self.env['ir.sequence'].next_by_code('islr.wh.doc')
        if local_number and self.date_ret:
            account_month = self.date_ret.split('-')[1]
            if not account_month == local_number[4:6]:
                local_number = local_number[:4] + account_month + local_number[6:]
        return local_number

    _name = "islr.wh.doc"
    _order = 'date_ret desc, number desc'
    _description = 'Document Income Withholding'
    _rec_name = 'name'

    amount_total_signed = fields.Many2one('account.move', string='campo')
    desc = fields.Char(
        'Descripcion', size=50,
        help="Descripción del vale")
    name = fields.Char(
            'Numero de Comprobante', size=64,
            required=True,
            help="Número de Comprobante de Retención")
    # code = fields.Char(
    #         string='Codigo', size=32,
    #         default=lambda s: s.retencion_seq_get(),
    #         help="referencia del vale2222")
    number = fields.Char(
            'Número de Retención', size=32, help="referencia del vale")
    number_comprobante = fields.Char(
            'Número de Comprobante de Retención', size=32, help="Número de Comprobante de Retención")

    type = fields.Selection([
            ('out_invoice', 'Factura del cliente'),
            ('in_invoice', 'Factura del proveedor'),
            ('in_refund', 'Reembolso de la factura del proveedor'),
            ('out_refund', 'Reembolso de la factura del cliente'),
            ], string='Tipo', readonly=True,
            default=lambda s: s._get_type(),
            help="Tipo de referencia")
    state = fields.Selection([
            ('draft', 'Borrador'),
            ('confirmed', 'Confirmado'),
            ('done', 'Realizado'),
            ('cancel', 'Cancelado')
            ], string='Estado', readonly=True, default='draft',
            help="estado del vale")
    date_ret = fields.Date(
            'Fecha de contabilidad', readonly=True,
            states={'draft': [('readonly', False)]},
            help="Mantener vacío para usar la fecha actual")
    date_uid = fields.Date(
            'Fecha de retención', readonly=True,
            states={'draft': [('readonly', False)]}, help="Fecha del vale")
   # period_id = fields.Many2one(
    #        'account.period', 'Period', readonly=True,
     #       states={'draft': [('readonly', False)]},
      #      help="Period when the accounts entries were done")
    account_id = fields.Many2one(
            'account.account', 'Cuenta', # required=True,
            readonly=True,
            states={'draft': [('readonly', False)]},
            help="Cuenta por cobrar o cuenta por pagar de socio")
    partner_id = fields.Many2one(
            'res.partner', 'Compañia', readonly=True, required=True,
            states={'draft': [('readonly', False)]},
            help="Socio objeto de retención")
    currency_id = fields.Many2one(
            'res.currency', 'Moneda', required=True, readonly=True,
            states={'draft': [('readonly', False)]},
            default=lambda s: s._get_currency(),
            help="Moneda en la que se realiza la transacción")
    journal_id= fields.Many2one(
            'account.journal', 'Diario', required=True, readonly=True,
            states={'draft': [('readonly', False)]},
            default=lambda s: s._get_journal(),
            help="Diario donde se registran los asientos contables")
    company_id = fields.Many2one(
            'res.company', 'Compañia', required=True,
            default=lambda s: s._get_company(),
            help="Compañia")
    amount_total_ret = fields.Float(
            compute='_get_amount_total', store=True, string='Monto total',
            digits=dp.get_precision('Withhold ISLR'),
            help="Importe total retenido")
    concept_ids = fields.One2many(
            'islr.wh.doc.line', 'islr_wh_doc_id', 'Concepto de retención de ingresos',
            readonly=True, states={'draft': [('readonly', False)]},
            help='Concepto de retención de ingresos')
    invoice_ids = fields.One2many(
            'islr.wh.doc.invoices', 'islr_wh_doc_id', 'Facturas retenidas',
            readonly=True, states={'draft': [('readonly', False)]},
            help='Facturas a retener')
    islr_wh_doc_id = fields.One2many(
            'account.move', 'islr_wh_doc_id', 'Facturas',
            states={'draft': [('readonly', False)]},
            help='Se refiere al documento de retención de ingresos del impuesto generado en la factura')
    user_id = fields.Many2one(
            'res.users', 'Salesman', readonly=True,
            states={'draft': [('readonly', False)]},
            default=lambda s: s._uid,
            help="Vendor user")
    automatic_income_wh = fields.Boolean(
            string='Retención Automática de Ingresos',
            default=False,
            help='Cuando todo el proceso se verifique automáticamente, y si todo está bien, se configurará como hecho')

    #invoice_id= fields.Many2one('islr.wh.doc.invoices', string='Factura')



    def name_get(self, ):
        res = []
        for item in self:
            if item.number and item.state == 'done':
                res.append((item.id, '%s (%s)' % (item.number, item.name)))
            else:
                res.append((item.id, '%s' % (item.name)))
        return res


    @api.model
    def _check_partner(self):
        """ Determine if a given partner is a Income Withholding Agent
        """
        #context = self._context or {}
        rp_obj = self.env['res.partner']
        #obj = self.browse()
        if self.type in ('out_invoice', 'out_refund') and \
                rp_obj._find_accounting_partner(
                    self.partner_id).islr_withholding_agent:
            return True
        if self.type in ('in_invoice', 'in_refund') and \
                rp_obj._find_accounting_partner(
                    self.company_id.partner_id).islr_withholding_agent:
            return True
        return False

    _constraints = [
        (_check_partner,
         'Error! El socio debe ser un agente de retención de ingresos.',
         ['partner_id']),
    ]

    def check_income_wh(self):
        """ Check invoices to be retained and have
        their fair share of taxes.
        """
        context = self._context or {}
        context = self._context or {}
        ids = isinstance(int) and [self.ids] or self.ids
        obj = self.browse()
        res = {}
        # Checks for available invoices to Withhold
        if not obj.invoice_ids:
            raise exceptions.except_orm(
                _('Facturas faltantes !!!'),
                _('¡Necesita agregar facturas para retener impuestos sobre la renta!'))

        for wh_line in obj.invoice_ids:
            # Checks for xml_id elements when withholding to supplier
            # Otherwise just checks for withholding concepts if any
            if not (wh_line.islr_xml_id or wh_line.iwdl_ids):
                res[wh_line.id] = (wh_line.invoice_id.name,
                                   wh_line.invoice_id.supplier_invoice_number)
        if res:
            note = _('Las siguientes facturas aún no se han retenido:\n\n')
            for i in res:
                note += '* %s, %s, %s\n' % res[i]
            note += _('\n Por favor, cargue los impuestos a retener e intente nuevamente')
            raise exceptions.except_orm(_(
                '¡Facturas con impuestos retenidos faltantes!'), note)
        return True

    def check_auto_wh(self):
        """ Tell us if the process already checked and everything was fine.
        """
        context = self._context or {}
        ids = isinstance(self.ids, (int)) and [self.ids] or self.ids
        obj = self.browse()
        return self.automatic_income_wh or False

    def check_auto_wh_by_type(self):
        """ Tell us if the process already checked and everything was
        fine in case of a in_invoice or in_refund
        """
        context = self._context or {}
        ids = isinstance(self.ids,(int)) and [self.ids] or self.ids
        brw = self.browse()
        if brw.type in ('out_invoice', 'out_refund'):
            return False
        return brw.automatic_income_wh or False

    @api.model
    def compute_amount_wh(self, islr_wh_doc_id):
        """ Calculate the total withholding each invoice
        associated with this document
        """
        context = self._context or {}
        ids = isinstance(islr_wh_doc_id, (int)) and [islr_wh_doc_id] \
              or isinstance(islr_wh_doc_id, (list)) and islr_wh_doc_id \
              or self.ids
        iwdi_obj = self.env['islr.wh.doc.invoices']
        iwdl_obj = self.env['islr.wh.doc.line']
        #inv_obj = self.env['account.move']
        #inv_brw = inv_obj.browse
        if isinstance(ids[0], int):
            iwd_brw = self.browse(ids)
        else:
            iwd_brw = islr_wh_doc_id[0]
        #if not self.date_uid or inv_obj.date_invoice:
        #    raise exceptions.except_orm(
        #       _('Missing Date !'), _("Please Fill Voucher Date"))

        '''
        period_ids = self.env('account.period').search(
            [('date_start', '<=', iwd_brw.date_uid),
                      ('date_stop', '>=', iwd_brw.date_uid)])
    
        if len(period_ids):
            period_id = period_ids[0]
        else:
            raise exceptions.except_orm(
                _('Warning !'),
                _("Not found a fiscal period to date: '%s' please check!") % (
                    iwd_brw.date_uid or time.strftime('%Y-%m-%d')))
        iwd_brw.write({'period_id': period_id})
        '''
        # TODO Searching & Unlinking for concept lines from the current withholding
        #iwdl_ids = iwdl_obj.search([('islr_wh_doc_id', '=', islr_wh_doc_id)])
        #if iwdl_ids:
        #    iwdl_ids.unlink()

        for iwdi_brw in iwd_brw.invoice_ids:
            iwdi_brw.load_taxes(iwdi_brw)
            calculated_values = iwdi_obj.get_amount_all(iwdi_brw)
            pruee = calculated_values.get(iwdi_brw.id)
            iwdi_brw.amount_islr_ret =  pruee.get('amount_islr_ret')
            iwdi_brw.base_ret = pruee.get('base_ret')
            iwdi_brw.currency_amount_islr_ret = pruee.get('currency_amount_islr_ret')
            iwdi_brw.currency_base_ret = pruee.get('currency_base_ret')
            iwdl_ids = iwdl_obj.search([('islr_wh_doc_id', '=', iwd_brw.id)])
            total_amount = 0.0
            for iwdl_id in iwdl_ids:
                #iwdl_id.amount = calculated_values.get('amount', 0.0)
                total_amount += iwdl_id.amount
            iwd_brw.amount_total_ret = total_amount
        return True


    def validate(self,*args):
        if args[0] in ['in_invoice', 'in_refund'] and args[1] and args[2]:
            return True
        return False


    def action_done(self):
        """ Call the functions in charge of preparing the document
        to pass the state done
        """
        context = self._context or {}
        ids = isinstance(self.ids, (int)) and [self.ids] or self.ids
        self.action_number()
        self.action_move_create()
        self.write({'state': 'done'})
        for a in self.invoice_ids:
           a.invoice_id.status = 'pro'

        #ACTUALIZA EL MONTO EN LA FACTURA
        iwdl = self.env['islr.wh.doc.line'].search([('islr_wh_doc_id','=',self.id)])
        #iwdl.invoice_id.residual = iwdl.invoice_id.residual - self.amount_total_ret
        #iwdl.invoice_id.residual_company_signed = iwdl.invoice_id.residual_company_signed - self.amount_total_ret

        #guarda el l atabla account_invoice el campo islr_wh_doc_id
        #inv_obj = self.env['account.move'].search([('id','=',iwdl.invoice_id.id)])
        #inv_obj.write({'islr_wh_doc_id': self.id})
        #iwdl.invoice_id.islr_wh_doc_id = iwdl.invoice_id.id
        return True

    def action_process(self):
        # TODO: ERASE THE REGARDING NODE IN THE WORKFLOW
        # METHOD HAVE BEEN LEFT FOR BACKWARD COMPATIBILITY
        return True

    def action_cancel_process(self):
        """ Delete all withholding lines and reverses the process of islr
        """
        #if not self._context:
        #    context = {}
        line_obj = self.env['islr.wh.doc.line']
        doc_inv_obj = self.env['islr.wh.doc.invoices']
        inv_obj = self.env['account.move']
        inv_line_obj = self.env['account.move.line']
        xml_obj = self.env['islr.xml.wh.line']
        wh_doc_id = self.ids

        # DELETED XML LINES
        islr_lines = line_obj.search([
                                     ('islr_wh_doc_id', '=', wh_doc_id)])
        for islr_line in islr_lines:
            xml_lines = islr_line and xml_obj.search(
                 [('islr_wh_doc_line_id', 'in', [islr_line.id])])
            if xml_lines:
                xml_lines.unlink()

        wh_line_list = line_obj.search( [
                                       ('islr_wh_doc_id', '=', wh_doc_id)])
        wh_line_list.unlink()

        doc_inv_list = doc_inv_obj.search( [
                                          ('islr_wh_doc_id', '=', wh_doc_id)])
        doc_inv_list.unlink()

        inv_list = inv_obj.search( [
                                  ('islr_wh_doc_id', '=', wh_doc_id)])
        inv_list.write({'status': 'no_pro'})
        inv_list.write({'islr_wh_doc_id': False})

        #inv_line_list = inv_line_obj.search(
        #    [('invoice_id', 'in', inv_list)])
        inv_line_obj.write({'apply_wh': False})

        return True

    @api.onchange('partner_id','inv_type')
    def onchange_partner_id(self):
        """ Unlink all taxes when change the partner in the document.
        @param type: invoice type
        @param partner_id: partner id was changed
        """
        context = self._context or {}
        acc_id = False
        res_wh_lines = []
        rp_obj = self.env['res.partner']
        inv_obj = self.env['account.move']

        # Unlink previous iwdi
        iwdi_obj = self.env['islr.wh.doc.invoices']
        iwdi_ids = self._ids and iwdi_obj.search(
            [('islr_wh_doc_id', '=', self._ids[0])])
        if iwdi_ids:
            iwdi_ids.unlink()
            self.iwdi_ids = []

        # Unlink previous line
        iwdl_obj = self.env['islr.wh.doc.line']
        iwdl_ids = self._ids and iwdl_obj.search(
            [('islr_wh_doc_id', '=', self._ids[0])])
        if iwdl_ids:
            iwdl_ids.unlink()
            self.iwdl_ids = []

        if self.partner_id:
            acc_part_id = rp_obj._find_accounting_partner(rp_obj.browse(
                 self.partner_id.id))
            args = [('state', '=', 'open'),
                    ('islr_wh_doc_id', '=', False),
                    '|',
                    ('partner_id', '=', acc_part_id.id),
                    ('partner_id', 'child_of', acc_part_id.id),
                    ]
            if self.type in ('out_invoice', 'out_refund'):
                acc_id = acc_part_id.property_account_receivable_id and \
                    acc_part_id.property_account_receivable_id.id
                args += [('type', 'in', ('out_invoice', 'out_refund'))]
            else:
                acc_id = acc_part_id.property_account_payable_id and \
                    acc_part_id.property_account_payable_id.id
                args += [('type', 'in', ('in_invoice', 'in_refund'))]

            inv_ids = inv_obj.search(args)
            inv_ids = iwdi_obj._withholdable_invoices(inv_ids)

            for invoice in inv_ids:
            #for inv_brw in inv_obj.browse(inv_ids[0].id):
                res_wh_lines += [{'invoice_id': invoice}]

        #values = {
        #    'account_id': acc_id,
        #    'invoice_ids': res_wh_lines}
        #self.write(values)
        self.account_id = acc_id
        self.invoice_ids = res_wh_lines

    @api.onchange('date_ret','date_uid')
    def on_change_date_ret(self):
        res = {}
        if self.date_ret:
            if not self.date_uid:
                res.update({'date_uid': self.date_ret})
      #      obj_per = self.env('account.period')
         #   per_id = obj_per.find( date_ret)
         #   res.update({'period_id': per_id and per_id[0]})
        return {'value': res}

    @api.model_create_multi
    def create(self,vals):
        """ When you create a new document, this function is responsible
        for generating the sequence code for the field
        """
        if not self._context:
           context = {}
     #   code = self.env['ir.sequence'].get('islr.wh.doc')
        #code = vals.get('name', False)
 #       vals[0]['code'] = code
        #name = vals['invoice_ids'][2]['invoice_id']
        #vals['name'] =name
        return super(IslrWhDoc, self).create(vals)


    def action_confirm(self):
        """ This checking if the provider allows retention is
        automatically verified and checked
        """
        context = self._context or {}
        ids = isinstance(self.ids, (int)) and [self.ids] or self.ids
        check_auto_wh = self.browse(
             ids[0]).company_id.automatic_income_wh
        return self.write(
            {'state': 'confirmed', 'automatic_income_wh': check_auto_wh})

    def _get_sequence_code(self):
        # metodo que crea la secuencia del número de control, si no esta creada crea una con el
        # nombre: 'l10n_nro_control

        self.invoice_ids.invoice_id.ensure_one()
        SEQUENCE_CODE = 'number_comprobante_islr'
        company_id = self._get_company()
        IrSequence = self.env['ir.sequence'].with_context(force_company=company_id.id)
        number = IrSequence.next_by_code(SEQUENCE_CODE)
        return number

    def action_number(self, *args):
        """ Is responsible for generating a numero for the document
        if it does not have one
        """
       # context = self._context or {}
        #obj_ret = self.browse()
        if self.type == 'in_invoice':
            number = self.name
            #
            # self.env.cr.execute(
            # 'SELECT id, number '
            # 'FROM islr_wh_doc '
            # 'WHERE id IN (' + ','.join([str(item) for item in self.ids]) + ')')

            for (iwd_id, number) in self._cr.fetchall():
                if not self.number:
                    number = self._get_sequence_code()
                    if not number:
                        raise exceptions.except_orm(
                            _("Error Configuracion"),
                            _('Sin secuencia configurada para retención de ingresos del proveedor'))

                    self.write({'number': number})
        #
        #
        else:
            # self.env.cr.execute(
            #     'SELECT id, number '
            #     'FROM islr_wh_doc '
            #     'WHERE id IN (' + ','.join([str(item) for item in self.ids]) + ')')

            for (iwd_id, number) in self._cr.fetchall():
                if not number:
                    number = self.env['ir.sequence'].get(
                        'islr.wh.doc.%s' % self.type)
                    if not number:
                        raise exceptions.except_orm(
                            _("Falta la configuración!"),
                            _('Sin secuencia configurada para ingresos del proveedor'
                              ' Retenciones'))
            # self.env.cr.execute('UPDATE islr_wh_doc SET number=%s '
            #                     'WHERE id=%s', (number, iwd_id))
        return True


    def action_cancel(self):
        """ The operation is canceled and not allows automatic retention
        """
        #context = self._context or {}
        # if self.browse(cr,uid,ids)[0].type=='in_invoice':
        # return True
        self.get_reconciled_move()
        self.cancel_move()
        self.action_cancel_process()

        self.env['islr.wh.doc'].write(
            {'state': 'cancel', 'automatic_income_wh': False})
        return True


    def get_reconciled_move(self):
        iwdi_obj = self.env['islr.wh.doc.invoices']
        iwdi_brw = iwdi_obj.search([('islr_wh_doc_id', '=', self.id)])

        dominio = [('move_id', '=', iwdi_brw.move_id.id),
                   ('reconciled', '=', True)]
        obj_move_line = self.env['account.move.line'].search(dominio)

        if obj_move_line:
            raise exceptions.ValidationError(
                (
                'El Comprobante ya tiene una aplicacion en la factura %s, debe desconciliar el comprobante para poder cancelar') % iwdi_brw.invoice_id.number)
        else:
            return True


    def cancel_move(self):
        """ Retention cancel documents
        """
        iwdi_obj = self.env['islr.wh.doc.invoices']
        iwdi_brw = iwdi_obj.search([('islr_wh_doc_id', '=', self.id)])


        for ret in self:
            if ret.state == 'done':
                for ret_line in iwdi_brw.move_id:
                    ref_move = ret_line._reverse_moves([{'date': self.date_ret
                                              }], True)
                    ref_move.write({'ref': 'Reversión de ' + str(ret_line.name) + ' para la ' + str(self.invoice_ids.invoice_id.display_name)})
            # second, set the withholding as cancelled
            ret.write({'state': 'cancel'})
        return True

        # account_move_obj = self.env['account.move']
        # for ret in self.browse():
        #     if ret.state == 'done':
        #         for ret_line in ret.invoice_ids:
        #             if ret_line.move_id:
        #                 account_move_obj.button_cancel(
        #                      [ret_line.move_id.id])
        #             ret_line.write({'move_id': False})
        #             if ret_line.move_id:
        #                 #account_move_obj.unlink([ret_line.move_id.id])
        #                 ret_line.move_id.unlink()
        #self.write({'state': 'cancel'})
        #return


    def action_cancel_draft(self):
        """ Back to draft status
        """
        ids = isinstance(self.ids, (int)) and [self.ids] or self.ids
        self.write({'state': 'draft'})
    #    for iwd_id in ids:
            # Deleting the existing instance of workflow for islr withholding
        #    self.delete_workflow( [iwd_id])
      #      self.create_workflow( [iwd_id])
        return True

    @api.model
    def converted_amount(self, line, amount):
        f_xc = self.env['l10n.ut'].sxc(
        line.invoice_id.company_id.currency_id.id,
        line.invoice_id.currency_id.id,
        line.islr_wh_doc_id.date_uid)
        return f_xc(amount)
        
    def action_move_create(self):
        """ Build account moves related to withholding invoice
        """
        context = self._context or {}
        ids = isinstance(self.ids, (int)) and [self.ids] or self.ids
        ixwl_obj = self.env['islr.xml.wh.line']
        ret = self.browse(ids)
        self = self.with_context({'income_wh': True})
        acc_id = ret.account_id.id
        acc_id_2 = ret.account_id
        if not ret.date_uid:
            self.write({
                       'date_uid': time.strftime('%Y-%m-%d')})

        ret.refresh()
        if ret.type in ('in_invoice', 'in_refund'):
            self.write({
                'date_ret': ret.date_uid})
        else:
            if not ret.date_ret:
                self.write({
                    'date_ret': time.strftime('%Y-%m-%d')})

        # Reload the browse because there have been changes into it
        ret = self.browse(ids)

     #   period_id = ret.period_id and ret.period_id.id or False
        journal_id = ret.journal_id.id

        '''
        if not period_id:
            period_ids = self.env('account.period').search(

                [('date_start', '<=',
                  ret.date_ret or time.strftime('%Y-%m-%d')),
                 ('date_stop', '>=',
                  ret.date_ret or time.strftime('%Y-%m-%d'))])
            if len(period_ids):
                period_id = period_ids[0]
            else:
                raise exceptions.except_orm(
                    _('Warning !'),
                    _("Not found a fiscal period to date: '%s' please check!")
                    % (ret.date_ret or time.strftime('%Y-%m-%d')))
        '''
        ut_obj = self.env['l10n.ut']
        for line in ret.invoice_ids:
            if ret.type in ('in_invoice', 'in_refund'):
                name = 'COMP. RET. ISLR ' + ret.name + \
                    ' Doc. ' + (line.invoice_id.supplier_invoice_number or '')
            else:
                name = 'COMP. RET. ISLR ' + ret.number + \
                    ' Doc. ' + (line.invoice_id.display_name or '')
            writeoff_account_id = False
            writeoff_journal_id = False
            #amount = line.amount_islr_ret
            amount = self.amount_total_ret
            ret_move = line.invoice_id.ret_and_reconcile(
                amount, acc_id_2, journal_id, writeoff_account_id,
                 writeoff_journal_id, ret.date_ret, name,
                line.iwdl_ids, 'wh_islr')

            if (line.invoice_id.currency_id.id !=
                    line.invoice_id.company_id.currency_id.id):
                #move_obj = self.env['account.move']
                move_line_obj = self.env['account.move.line']
                line_ids = move_line_obj.search([('move_id','=',ret_move.id)])
                for ml in line_ids:
                    ml.write({'currency_id': line.invoice_id.currency_id.id})
                    if ml.credit:
                        ml.write({
                            'amount_currency': ret.converted_amount(line, ml.credit) * -1})
                    elif ml.debit:
                        ml.write({
                            'amount_currency':ret.converted_amount(line, ml.debit)})
            ret_move.post()
            #make the withholding line point to that move
            #rl = {
            #    'move_id': ret_move['move_id'],
            #}
            #lines = [(op,id,values)] #escribir en un one2many
            #lines = [(1, line.id, rl)]
            self.write({
                       'invoice_ids': line})
        xml_ids_obj = self.env['islr.xml.wh.line']
        for line in ret.concept_ids:
            #xml_ids_obj += [xml.id for xml in line.xml_ids]
            xml_ids_obj = xml_ids_obj.search([('islr_wh_doc_line_id', '=', line.id)])
            #xml_ids_obj.write({'date_ret': time.strftime('%Y-%m-%d')})
            xml_ids_obj.write({'date_ret': self.date_ret})

        #self.write( ids, {'period_id': period_id}, context=context)
        # guarda en el la tabla islr.wh.doc.invoices
        iwdi_obj = self.env['islr.wh.doc.invoices'].search([('islr_wh_doc_id', '=', self.id)])
        if not iwdi_obj:
            raise exceptions.except_orm(
                _('Advertencia!'),
                _('Por favor recuerde seleccionar las facturas a retener'))
        iwdi_obj.write({'move_id': ret_move.id})

        return {'move_id': ret_move}

        return True

    def wh_and_reconcile(self, invoice_id, pay_amount,
                         pay_account_id, pay_journal_id,
                         writeoff_acc_id,
                         writeoff_journal_id, name=''):
        """ retain, reconcile and create corresponding journal items
        @param invoice_id: invoice to retain and reconcile
        @param pay_amount: amount payable on the invoice
        @param pay_account_id: payment account
        @param period_id: period for the journal items
        @param pay_journal_id: payment journal
        @param writeoff_acc_id: account for reconciliation
        @param writeoff_period_id: period for reconciliation
        @param writeoff_journal_id: journal for reconciliation
        @param name: withholding voucher name
        """
        inv_obj = self.env['account.move']
        rp_obj = self.env['res.partner']
        ret = self.browse()[0]
        if self._context is None:
            context = {}
        # TODO check if we can use different period for payment and the
        # writeoff line
        # assert len(invoice_ids)==1, "Can only pay one invoice at a time"
        invoice = inv_obj.browse(invoice_id)
        acc_part_id = rp_obj._find_accounting_partner(invoice.partner_id)
        src_account_id = invoice.account_id.id
        # Take the seq as name for move
        types = {'out_invoice': -1, 'in_invoice':
                 1, 'out_refund': 1, 'in_refund': -1,'entry':1}
        direction = types[invoice.type]

        date = ret.date_ret

        l1 = {
            'debit': direction * pay_amount > 0 and direction * pay_amount,
            'credit': direction * pay_amount < 0 and - direction * pay_amount,
            'account_id': src_account_id,
            'partner_id': acc_part_id.id,
            'ref': invoice.number,
            'date': date,
            'currency_id': False,
        }
        l2 = {
            'debit': direction * pay_amount < 0 and - direction * pay_amount,
            'credit': direction * pay_amount > 0 and direction * pay_amount,
            'account_id': pay_account_id,
            'partner_id': acc_part_id.id,
            'ref': invoice.number,
            'date': date,
            'currency_id': False,
        }
        if not name:
            if invoice.type in ['in_invoice', 'in_refund']:
                name = 'COMP. RET. ISLR ' + ret.number + \
                    ' Doc. ' + (invoice.supplier_invoice_number or '')
            else:
                name = 'COMP. RET. ISLR ' + ret.number + \
                    ' Doc. ' + (invoice.number or '')

        l1['name'] = name
        l2['name'] = name

        lines = [(0, 0, l1), (0, 0, l2)]
        move = {'ref': invoice.number,
                'line_ids': lines,
                'journal_id': pay_journal_id,
                'date': date}
        move_id = self.env['account.move'].create(move)

        self.env['account.move'].post([move_id])

        line_ids = []
        total = 0.0
        line = self.env['account.move.line']
        self.env.cr.execute('select id from account_move_line where move_id in (' + str(
            move_id) + ',' + str(invoice.move_id.id) + ')')
        lines = line.browse( [item[0] for item in self._cr.fetchall()])
        for aml_brw in lines + invoice.payment_ids:
            if aml_brw.account_id.id == src_account_id:
                line_ids.append(aml_brw.id)
                total += (aml_brw.debit or 0.0) - (aml_brw.credit or 0.0)
        if ((not round(total, self.env['decimal.precision'].precision_get(
                 'Withhold ISLR'))) or writeoff_acc_id):
            self.env['account.move.line'].reconcile(
                 line_ids, 'manual', writeoff_acc_id,
                 writeoff_journal_id,)
        else:
            self.env['account.move.line'].reconcile_partial(
                line_ids, 'manual' )

        # Update the stored value (fields.function), so we write to trigger
        # recompute
        self.env['account.move'].write(
              {})


    def unlink(self):
        """ Overwrite the unlink method to throw an exception if the
        withholding is not in cancel state."""
        context = self._context or {}
        for islr_brw in self.browse():
            if islr_brw.state != 'cancel':
                raise exceptions.except_orm(
                    _("Procedimiento inválido !!"),
                    _("El documento de retención debe estar en estado Cancelado "
                      " para ser eliminado"))
            else:
                #super(IslrWhDoc, self).unlink(islr_brw.id)
                super(IslrWhDoc, self).unlink()
        return True


    def _dummy_cancel_check(self):
        '''
        This will be the method that another developer should use to create new
        check on Withholding Document
        Make super to this method and create your own cases
        '''
        return True


    def _check_xml_wh_lines(self):
        """Check if this ISLR WH DOC is being used in a XML ISLR DOC"""
        context = self._context or {}
        ids = isinstance(self.ids, (int)) and [self.ids] or self.ids
        ixwd_ids = []
        ixwd_obj = self.env['islr.xml.wh.doc']
        for iwd_brw in self.browse(ids):
            for iwdi_brw in iwd_brw.invoice_ids:
                for ixwl_brw in iwdi_brw.islr_xml_id:
                    if (ixwl_brw.islr_xml_wh_doc and
                            ixwl_brw.islr_xml_wh_doc.state != 'draft'):
                        ixwd_ids += [ixwl_brw.islr_xml_wh_doc.id]

        if not ixwd_ids:
            return True

        note = _('El siguiente ISLR XML DOC debe establecerse en Borrador antes de '
                 'Cancelar este documento\n\n')
        for ixwd_brw in ixwd_obj.browse( ixwd_ids):
            note += '%s\n' % ixwd_brw.name
        raise exceptions.except_orm(_("Procedimiento inválido !!"), note)


    def cancel_check(self):
        '''
        Unique method to check if we can cancel the Withholding Document
        '''
        context = self._context or {}
        ids = isinstance(self.ids, (int)) and [self.ids] or self.ids

        if not self._check_xml_wh_lines():
            return False
        if not self._dummy_cancel_check():
            return False
        return True


class AccountInvoice(models.Model):
    _inherit = 'account.move'


    def _get_inv_from_iwdi(self):

        #Returns a list of invoices which are recorded in VAT Withholding Docs

        context = self._context or {}
        ids = isinstance(self.ids, (int)) and [self.ids] or self.ids
        iwdi_obj = self.env['islr.wh.doc.invoices']
        iwdi_brws = iwdi_obj.browse(ids)
        return [i.invoice_id.id for i in iwdi_brws if i.invoice_id]


    def _get_inv_from_iwd(self):
        #Returns a list of invoices which are recorded in VAT Withholding Docs
        res = []
        context = self._context or {}
        ids = isinstance(self.ids, (int)) and [self.ids] or self.ids
        iwd_obj = self.env['islr.wh.doc']
        iwd_brws = iwd_obj.browse (ids)
        for iwd_brw in iwd_brws:
            for iwdl_brw in iwd_brw.invoice_ids:
                if iwdl_brw.invoice_id:
                    res.append(iwdl_brw.invoice_id.id)
        return res


    #@api.depends('islr_wh_doc_id.invoices_ids')
    def _fnct_get_wh_income_id(self):
        context = self._context or {}
        ids = isinstance(self.ids, (int)) and [self.ids] or self.ids
        iwdi_obj = self.env['islr.wh.doc.invoices']
        iwdi_ids = iwdi_obj.search([('invoice_id', 'in', ids)],)

        iwdi_brws = iwdi_obj.browse(iwdi_ids.id)
        res = {}.fromkeys(ids, False)
        for i in iwdi_brws:
            if i.invoice_id:
                res[i.invoice_id.id] = i.islr_wh_doc_id.id or False
        return res


    islr_wh_doc_id=fields.Many2one(
            'islr.wh.doc', string='Documento de retención de ingresos',
            help="Documentación de la retención de ingresos del impuesto generado a partir de esta factura")





    # def copy(self):
    #     """ Initialized id by duplicating
    #     """
    #     # NOTE: use ids argument instead of id for fix the pylint error W0622.
    #     # Redefining built-in 'id'
    #     if self.default is None:
    #         default = {}
    #     default = self.default.copy()
    #     default.update({'islr_wh_doc_id': 0})
    #
    #     return super(AccountInvoice, self).copy(default)


class IslrWhDocInvoices(models.Model):
    _name = "islr.wh.doc.invoices"
    _description = 'Document and Invoice Withheld Income'

    def convert_amount_to_invoice_currency(self, amount):
        self.ensure_one()
        ut_obj = self.env['l10n.ut']
        f_xc = ut_obj.sxc(
            self.invoice_id.company_id.currency_id.id,
            self.invoice_id.currency_id.id,
            self.islr_wh_doc_id.date_uid
	)
        return f_xc(amount)
	
    def convert_amount_to_company_currency(self, wh_line, amount):
        self.ensure_one()
        ut_obj = self.env['l10n.ut']
        f_xc = ut_obj.sxc(
            wh_line.invoice_id.currency_id.id,
            wh_line.invoice_id.company_id.currency_id.id,
            wh_line.invoice_id.date
	)
        return f_xc(amount)                 

    @api.depends('islr_wh_doc_id.amount_total_ret')
    def _amount_all(self):
        """ Return all amount relating to the invoices lines
        """
        res = {}
        for ret_line in self.browse(self.id):
            res[ret_line.id] = {
                'amount_islr_ret': 0.0,
                'base_ret': 0.0,
                'currency_amount_islr_ret': 0.0,
                'currency_base_ret': 0.0,
            }
            #for line in ret_line.iwdl_ids:
            #    res[ret_line.id]['amount_islr_ret'] += line.amount
            #    res[ret_line.id]['base_ret'] += line.base_amount
            #    res[ret_line.id]['currency_amount_islr_ret'] += \
            #        f_xc(line.amount)
            #    res[ret_line.id]['currency_base_ret'] += f_xc(line.base_amount)
            iwdl_local = self.env['islr.wh.doc.line'].search([('islr_wh_doc_id', '=', ret_line.islr_wh_doc_id.id)])
            for line in iwdl_local:
                res[ret_line.id]['amount_islr_ret'] += (line.base_amount * line.retencion_islr / 100) - line.subtract
                res[ret_line.id]['base_ret'] += line.base_amount
                res[ret_line.id]['currency_amount_islr_ret'] += \
                    ret_line.convert_amount_to_invoice_currency(line.base_amount * line.retencion_islr / 100)
                res[ret_line.id]['currency_base_ret'] += ret_line.convert_amount_to_invoice_currency(line.base_amount)
        return res



    islr_wh_doc_id= fields.Many2one(
            'islr.wh.doc', 'Retener documento', ondelete='cascade',
            help="Retención de documentos del impuesto sobre la renta generado por esta factura")
    invoice_id= fields.Many2one(
            'account.move', 'Factura', help="Factura retenida")
    supplier_invoice_number=fields.Char(related='invoice_id.supplier_invoice_number',
            string='Proveedor inv. #', size=64, store=False, readonly=True)
    islr_xml_id= fields.One2many(
            'islr.xml.wh.line', 'islr_wh_doc_inv_id', 'Retención de ISLR')
    #TODO revisar proceso de calculo de valores. Se crearan campos tradicionales
    #amount_islr_ret= fields.Float(compute='_amount_all', method=True, digits=(16, 2), string='Withheld Amount',
    #        multi='all', help="Amount withheld from the base amount")
    #base_ret = fields.Float(compute='_amount_all', method=True, digits=(16, 2), string='Base Amount',
    #        multi='all',
    #        help="Monto a partir del cual se calculará una retención")
    #currency_amount_islr_ret = fields.Float(compute='_amount_all', method=True, digits=(16, 2),
    #                                        string='Moneda retenida Monto retenido', multi='all',
    #                                        help="Amount withheld from the base amount")
    #currency_base_ret = fields.Float(compute='_amount_all', method=True, digits=(16, 2),
    #                                 string='Monto base en moneda extranjera', multi='all',
    #                                 help="Monto a partir del cual se calculará una retención")
    amount_islr_ret= fields.Float(string='Cantidad retenida', digits=(16, 2), help="Monto retenido del monto base")
    base_ret = fields.Float(string='Cantidad base', digits=(16, 2), help="Monto a partir del cual se calculará una retención")
    currency_amount_islr_ret = fields.Float(string='Moneda retenida Monto retenido', digits=(16, 2),
                                            help="Monto retenido del monto base")
    currency_base_ret = fields.Float(string='Monto base en moneda extranjera', digits=(16, 2),
                                     help="Monto a partir del cual se calculará una retención")
    iwdl_ids= fields.One2many(
            'islr.wh.doc.line', 'iwdi_id', 'Conceptos de retención',
            help='Conceptos de retención de esta factura retenida')
    move_id = fields.Many2one(
            'account.move', 'Entrada de diario', ondelete='restrict',
            readonly=True, help="Bono contable")

    _rec_rame = 'invoice_id'

    def get_amount_all(self, iwdi_brw):
        """ Return all amount relating to the invoices lines
        """
        res = {}
        ut_obj = self.env['l10n.ut']
        for ret_line in self.browse(iwdi_brw.id):
            res[ret_line.id] = {
                'amount_islr_ret': 0.0,
                'base_ret': 0.0,
                'currency_amount_islr_ret': 0.0,
                'currency_base_ret': 0.0,
            }
            iwdl_local = self.env['islr.wh.doc.line'].search([('islr_wh_doc_id', '=', ret_line.islr_wh_doc_id.id)])
            for line in iwdl_local:
                res[ret_line.id]['amount_islr_ret'] += (line.base_amount * line.retencion_islr / 100) - line.subtract
                res[ret_line.id]['base_ret'] += line.base_amount
                res[ret_line.id]['currency_amount_islr_ret'] += \
                    ret_line.convert_amount_to_invoice_currency(line.base_amount * line.retencion_islr / 100)
                res[ret_line.id]['currency_base_ret'] += ret_line.convert_amount_to_invoice_currency(line.base_amount)
                res[ret_line.id]['iwdl_ids'] = line.concept_id
                res['amount'] = res[ret_line.id].get('amount_islr_ret', 0.0)
        return res

    def _check_invoice(self):
        """ Determine if the given invoices are in Open State
        """
        self.context = self._context or {}
        ids = isinstance(self.ids, (int)) and [self.ids] or self.ids
        for iwdi_brw in self.browse(ids):
            if iwdi_brw.invoice_id.state != 'open':
                return False
        return True

    _constraints = [
        (_check_invoice, 'Error! The invoice must be in Open State.',
         ['invoice_id']),
    ]
    @api.model
    def _get_concepts(self, inv_id):
        """ Get a list of withholdable concepts (concept_id) from the invoice lines
        """
        context = self._context or {}
        ids = isinstance(inv_id, (int)) and [inv_id] or (isinstance(inv_id, (list)) and inv_id) or [inv_id.id]
        inv_obj = self.env['account.move']
        concept_set = set()
        #TODO VERIFICAR SI PARA CLEINTES TIENE EL MISMO COPORTAMIENTO PARA ELIMINAR ESTA LINEA
        #for i in inv_id:

        inv_brw = inv_obj.browse(ids)
        for ail in inv_brw.invoice_line_ids:
            if ail.concept_id and ail.concept_id.withholdable:
                concept_set.add(ail.concept_id.id)
        return list(concept_set)

    def _withholdable_invoices(self, inv_ids):
        """ Given a list of invoices return only those
        where there are withholdable concepts
        """
        context = self._context or {}
        #ids = isinstance(inv_ids, (int)) and [inv_ids] or inv_ids
        res_ids = []
        for iwdi_id in inv_ids:
            iwdi_id = self._get_concepts(iwdi_id) and iwdi_id
            if iwdi_id:
                res_ids += [iwdi_id]
        return res_ids


    @api.model
    def _get_wh(self, iwdl_id, concept_id):
        """ Return a dictionary containing all the values of the retention of an
        invoice line.
        @param concept_id: Withholding reason
        """
        # TODO: Change the signature of this method
        # This record already has the concept_id built-in
        #context = self._context or {}
        #ids = isinstance(self.ids, (int)) and [self.ids] or self.ids
        ixwl_obj = self.env['islr.xml.wh.line']
        iwdl_obj = self.env['islr.wh.doc.line']
        #iwdl_brw = iwdl_obj.browse(iwdl_id)
        residual_ut = 0.0
        subtract_write_ut = 0.0

        ut_date = iwdl_id.islr_wh_doc_id.date_uid
        ut_obj = self.env['l10n.ut']
        money2ut = ut_obj.compute
        ut2money = ut_obj.compute_ut_to_money

        vendor, buyer, wh_agent = self._get_partners(iwdl_id.invoice_id)
        self.wh_agent = wh_agent
        apply_income = not vendor.islr_exempt
        residence = self._get_residence(vendor, buyer)
        #TODO revisar donde se configura este parametro
        nature = self._get_nature(vendor)
        #nature = False

        concept_id = iwdl_id.concept_id.id
        # rate_base,rate_minimum,rate_wh_perc,rate_subtract,rate_code,rate_id,
        # rate_name
        # Add a Key in context to store date of ret fot U.T. value
        # determination
        # TODO: Future me, this context update need to be checked with the
        # other date in the withholding in order to take into account the
        # Retención de ingresos del cliente.
        #context.update({
        #    'wh_islr_date_ret':
        #    iwdl_brw.islr_wh_doc_id.date_uid or
        #    iwdl_brw.islr_wh_doc_id.date_ret or False
        #})
        base = 0
        wh_concept = 0.0

        # Using a clousure to make this call shorter
        #PROVEEDORES
        if iwdl_id.invoice_id.type in ('in_invoice', 'in_refund'):
            for line in iwdl_id.xml_ids:
                base += self.convert_amount_to_company_currency(iwdl_id, line.account_invoice_line_id.price_subtotal)

            # rate_base, rate_minimum, rate_wh_perc, rate_subtract, rate_code,
            # rate_id, rate_name, rate2 = self._get_rate(
            #    cr, uid, ail_brw.concept_id.id, residence, nature, base=base,
            #    inv_brw=ail_brw.move_id, context=context)
            rate_tuple = self._get_rate(concept_id, residence, nature, base=base,
                inv_brw=iwdl_id.invoice_id)

            if rate_tuple[7]:
                apply_income = True
                residual_ut = (
                    (rate_tuple[0] / 100.0) * (rate_tuple[2] / 100.0) *
                    rate_tuple[7]['cumulative_base_ut'])
                residual_ut -= rate_tuple[7]['cumulative_tax_ut']
                residual_ut -= rate_tuple[7]['subtrahend']
            else:
                apply_income = (apply_income and
                                base >= rate_tuple[0] * rate_tuple[1] / 100.0)
            wh = 0.0
            subtract = apply_income and rate_tuple[3] or 0.0
            subtract_write = 0.0
            sb_concept = subtract
            for line in iwdl_id.xml_ids:
                base_line = self.convert_amount_to_company_currency(iwdl_id, line.account_invoice_line_id.price_subtotal)
                base_line_ut = money2ut(base_line, ut_date)
                values = {}
                if apply_income and not rate_tuple[7]:
                    wh_calc = ((rate_tuple[0] / 100.0) *
                               (rate_tuple[2] / 100.0) * base_line)
                    if subtract >= wh_calc:
                        wh = 0.0
                        subtract -= wh_calc
                    else:
                        wh = wh_calc - subtract
                        subtract_write = subtract
                        subtract = 0.0
                    values = {
                        'wh': wh,
                        'raw_tax_ut': money2ut(wh, ut_date),
                        'sustract': subtract or subtract_write,
                    }
                elif apply_income and rate_tuple[7]:
                    tax_line_ut = (base_line_ut * (rate_tuple[0] / 100.0) *
                                   (rate_tuple[2] / 100.0))
                    if residual_ut >= tax_line_ut:
                        wh_ut = 0.0
                        residual_ut -= tax_line_ut
                    else:
                        wh_ut = tax_line_ut + residual_ut
                        subtract_write_ut = residual_ut
                        residual_ut = 0.0
                    wh = ut2money(wh_ut, ut_date)
                    values = {
                        'wh': wh,
                        'raw_tax_ut': wh_ut,
                        'sustract': ut2money(
                            residual_ut or subtract_write_ut,
                            ut_date),
                    }
                type_person = ''
                if nature == False and residence == True:
                    type_person = 'PJDO'
                elif nature == False and residence == False:
                    type_person = 'PJND'
                if nature == True and residence == True:
                    type_person = 'PNRE'
                if nature == True and residence == False:
                    type_person = 'PNNR'
                name_rates = self.env['islr.rates'].write({
                                                        'name': type_person
                                                         })
                values.update({
                    'base': base_line * (rate_tuple[0] / 100.0),
                    'raw_base_ut': base_line_ut,
                    'rate_id': rate_tuple[5],
                    'porcent_rete': rate_tuple[2],
                    'concept_code': rate_tuple[4],
                })
                #ixwl_obj.write(line.id, values)
                line.write(values)
                wh_concept += wh
        else:   #CLIENTES
            for line in iwdl_id.invoice_id.invoice_line_ids:
                if line.concept_id.id == concept_id:
                    base += self.convert_amount_to_company_currency(iwdl_id, line.price_subtotal)

            rate_tuple = self._get_rate(concept_id, residence, nature, base=0.0,
                inv_brw=iwdl_id.invoice_id)

            if rate_tuple[7]:
                apply_income = True
            else:
                apply_income = (apply_income and
                                base >= rate_tuple[0] * rate_tuple[1] / 100.0)
            sb_concept = apply_income and rate_tuple[3] or 0.0
            if apply_income:
                wh_concept = ((rate_tuple[0] / 100.0) *
                              rate_tuple[2] * base / 100.0)
                wh_concept -= sb_concept
        values = {
            'amount': wh_concept,
            'raw_tax_ut': money2ut(wh_concept, ut_date),
            'subtract': sb_concept,
            'base_amount': base * (rate_tuple[0] / 100.0),
            'raw_base_ut': money2ut(base, ut_date),
            'retencion_islr': rate_tuple[2],
            # 'islr_rates_id': rate_tuple[5],
        }
        iwdl_id.write(values)
        return True


    def load_taxes(self, ids):
        """ Load taxes to the current invoice,
        and if already loaded, it recalculates and load.
        """
        #context = self._context or {}
        #ids = isinstance(ids, (int)) and [ids] or ids
        ids = isinstance(ids, (int)) and [ids] or (isinstance(ids, (list)) and ids) or [ids.id]
        ixwl_obj = self.env['islr.xml.wh.line']
        iwdl_obj = self.env['islr.wh.doc.line']
        ail_obj = self.env['account.move.line']
        ret_line = self.browse(ids)
        lines = []
        xmls = {}

        if not ret_line.invoice_id:
            return True

        concept_list = self._get_concepts(ret_line.invoice_id)

        if ret_line.invoice_id.type in ('in_invoice', 'in_refund'):
            # Searching & Unlinking for xml lines from the current invoice
            xml_lines = ixwl_obj.search([(
                'islr_wh_doc_inv_id', '=', ret_line.id)])
            if xml_lines:
                xml_lines.unlink()

            # Creating xml lines from the current invoices again
            ilids = self.env['account.move.line'].search([('move_id','=',ret_line.invoice_id.id)])
            #ail_brws = [
            #    i for i in ilids
            #    if i.concept_id and i.concept_id.withholdable]
            for i in ilids:
                values = self._get_xml_lines(i)
                values.update({'islr_wh_doc_inv_id': ret_line.id, })
                #TODO VALIDACION QUE ESTA DE MAS PORQUE SE ESTA COLOCANDO UN VALOR POR DEFECTO
                if not values.get('invoice_number'):
                    raise exceptions.except_orm(
                        _("Error en proceso humano"),
                        _("Complete el número de factura para continuar, sin "
                          " este número será imposible de calcular "
                          "la Retencion"))
                # Vuelve a crear las lineas
                xml_id = ixwl_obj.create(values)
                # Write back the new xml_id into the account_invoice_line
                ail_vals = {'wh_xml_id': xml_id.id}
                i.write(ail_vals)
                lines.append(xml_id)
                # Keeps a log of the rate & percentage for a concept
                if xmls.get(i.concept_id.id):
                    xmls[i.concept_id.id] += [xml_id.id]
                else:
                    xmls[i.concept_id.id] = [xml_id.id]

            # Searching & Unlinking for concept lines from the current invoice
            iwdl_ids = iwdl_obj.search( [(
                'invoice_id', '=', ret_line.invoice_id.id)])
            if iwdl_ids:
                iwdl_ids.unlink()
                iwdl_ids = []
            # Creating concept lines for the current invoice
            for concept_id in concept_list:
                iwdl_id = iwdl_obj.create(
                     {'islr_wh_doc_id': ret_line.islr_wh_doc_id.id,
                              'concept_id': concept_id,
                              'invoice_id': ret_line.invoice_id.id,
                              'xml_ids': [(6, 0, xmls.get(concept_id, False))],
                              'iwdi_id': ret_line.id})
                self._get_wh( iwdl_id, concept_id,)
        else:
            # Searching & Unlinking for concept lines from the current
            # withholding
            iwdl_ids = iwdl_obj.search(
               [('iwdi_id', '=', ret_line.id)])
            if iwdl_ids:
                iwdl_ids.unlink()
                iwdl_ids = []

            for concept_id in concept_list:
                iwdl_id = iwdl_obj.create(
                     {
                        'islr_wh_doc_id': ret_line.islr_wh_doc_id.id,
                        'concept_id': concept_id,
                        'invoice_id': ret_line.invoice_id.id},)
                iwdl_ids += iwdl_id
                self._get_wh(iwdl_id, concept_id)
                iwdl_id.write({'iwdi_id': ids[0]})
            #self.write({'iwdl_ids': [(6, 0, iwdl_ids)]})
        #values = self.get_amount_all()
        #self.write(values)
        return True

    def _get_partners(self, invoice_id):
        """ Is obtained: the seller's id, the buyer's id
        invoice and boolean field that determines whether the buyer is
        retention agent.
        """
        rp_obj = self.env['res.partner']
        inv_part_id = rp_obj._find_accounting_partner(invoice_id.partner_id)
        comp_part_id = rp_obj._find_accounting_partner(invoice_id.company_id.partner_id)
        if invoice_id.type in ('in_invoice', 'in_refund'):
            vendor = inv_part_id
            buyer = comp_part_id
        else:
            buyer = inv_part_id
            vendor = comp_part_id
        return (vendor, buyer, buyer.islr_withholding_agent)

    def _get_residence(self,vendor, buyer):
        """It determines whether the tax form buyer address is the same
        that the seller, then in order to obtain the associated rate.
        Returns True if a person is resident. Returns
        False if is not resident.
        """

        vendor_address = self._get_country_fiscal(vendor)
        buyer_address = self._get_country_fiscal(buyer)
        if vendor_address and buyer_address:
            if self.invoice_id.type in ('in_invoice', 'in_refund'):
                if (vendor.company_type== 'person' and vendor.people_type_individual == 'pnre') \
                    or (vendor.company_type == 'company' and vendor.people_type_company == 'pjdo'):
                    return True
                elif (vendor.company_type== 'person' and vendor.people_type_individual == 'pnnr') \
                    or (vendor.company_type == 'company' and vendor.people_type_company == 'pjnd') :
                    return False
            else:
                if (buyer.company_type== 'person' and buyer.people_type_individual == 'pnre') \
                    or (buyer.company_type == 'company' and buyer.people_type_company == 'pjdo'):
                    return True
                elif (buyer.company_type== 'person' and buyer.people_type_individual == 'pnnr') \
                    or (buyer.company_type == 'company' and buyer.people_type_company == 'pjnd') :
                    return False
        return False

    def _get_nature(self, partner_id):
        """ It obtained the nature of the seller from VAT, returns
        True if natural person, and False if is legal.
        """
        rp_obj = self.env['res.partner']
        acc_part_id = rp_obj._find_accounting_partner(partner_id)
        # if not acc_part_id.:
        #     raise exceptions.except_orm(
        #         _('Accion Invalida!'),
        #         _("Imposible retención de ingresos, porque el socio '%s' no esta"
        #           " asociado a ningun tipo de persona") % (acc_part_id.name))
        # else:
        if acc_part_id.company_type == 'person' :
            return True
        else:
            return False

    def _get_rate(self,concept_id, residence, nature, base=0.0,
                  inv_brw=None):
        """ Rate is obtained from the concept of retention, provided
        if there is one associated with the specifications:
        The vendor's nature matches a rate.
        The vendor's residence matches a rate.
        """
        context = self._context or {}
        iwdl_obj = self.env['islr.wh.doc.line']
        ut_obj = self.env['l10n.ut']
        iwhd_obj = self.env["islr.wh.historical.data"]
        money2ut = ut_obj.compute
        ut2money = ut_obj.compute_ut_to_money
        islr_rate_obj = self.env['islr.rates']
        islr_rate_args = [('concept_id', '=', concept_id),
                          ('nature', '=', nature),
                          ('residence', '=', residence), ]
        order = 'minimum desc'

        date_ret = inv_brw and inv_brw.islr_wh_doc_id.date_uid or \
            time.strftime('%Y-%m-%d')

        concept_brw = self.env['islr.wh.concept'].browse(concept_id)

        # First looking records for ISLR rate1
        rate2 = False
        islr_rate_ids = islr_rate_obj.search(
            islr_rate_args + [('rate2', '=', rate2)], order=order)

        # Now looking for ISLR rate2
        if not islr_rate_ids:
            rate2 = True
            islr_rate_ids = islr_rate_obj.search(
                islr_rate_args + [('rate2', '=', rate2)], order=order)

        msg_nature = nature and 'Natural' or u'Jurídica'
        msg_residence = residence and 'Domiciliada' or 'No Domiciliada'
        msg = _(u'No hay tarifas disponibles para "Persona %s %s" en el concepto: "%s"') % (
            msg_nature, msg_residence, concept_brw.name)
        if not islr_rate_ids:
            raise exceptions.except_orm(_('Falta la configuración'), msg)

        if not rate2:
            #rate_brw = islr_rate_obj.browse(islr_rate_ids[0])
            rate_brw_minimum = ut2money(
                islr_rate_ids.minimum, date_ret)
            rate_brw_subtract = ut2money(
                islr_rate_ids.subtract, date_ret)
        else:
            rate2 = {
                'cumulative_base_ut': 0.0,
                'cumulative_tax_ut': 0.0,
            }
            base_ut = money2ut( base, date_ret)
            iwdl_ids = iwdl_obj.search(

                [('partner_id', '=', inv_brw.partner_id.id),
                 ('concept_id', '=', concept_id),
                 ('invoice_id', '!=', inv_brw.id)]) # need to exclude this
                                                    # invoice from computation
                 #('fiscalyear_id', '=',inv_brw.islr_wh_doc_id.fiscalyear_id.id)]

            # Previous amount Tax Unit for this partner in this fiscalyear with
            # this concept
            for iwdl_brw in iwdl_obj.browse(iwdl_ids):
                base_ut += iwdl_brw.raw_base_ut
                rate2['cumulative_base_ut'] += iwdl_brw.raw_base_ut
                rate2['cumulative_tax_ut'] += iwdl_brw.raw_tax_ut
            iwhd_ids = iwhd_obj.search(

                [('partner_id', '=', inv_brw.partner_id.id),
                 ('concept_id', '=', concept_id),
                 ('fiscalyear_id', '=',
                  inv_brw.islr_wh_doc_id.fiscalyear_id.id)])
            for iwhd_brw in iwhd_obj.browse( iwhd_ids):
                base_ut += iwhd_brw.raw_base_ut
                rate2['cumulative_base_ut'] += iwhd_brw.raw_base_ut
                rate2['cumulative_tax_ut'] += iwhd_brw.raw_tax_ut
            found_rate = False
            for rate_brw in islr_rate_obj.browse(
                     islr_rate_ids):
                # Get the invoice_lines that have the same concept_id than the
                # rate_brw which is here Having the lines the subtotal for each
                # lines can be got and with that it will be possible to which
                # rate to grab,
                # MULTICURRENCY WARNING: Values from the invoice_lines must be
                # translate to VEF and then to UT this way computing in a
                # proper way the amount values
                if rate_brw.minimum > base_ut * rate_brw.base / 100.0:
                    continue
                rate_brw_minimum = ut2money(
                     rate_brw.minimum, date_ret)
                rate_brw_subtract = ut2money(
                     rate_brw.subtract, date_ret)
                found_rate = True
                rate2['subtrahend'] = rate_brw.subtract
                break
            if not found_rate:
                msg += _(' Para unidades impositivas mayores que cero')
                raise exceptions.except_orm(_('Falta la configuración'), msg)
        return (islr_rate_ids.base, rate_brw_minimum, islr_rate_ids.wh_perc,
                rate_brw_subtract, islr_rate_ids.code, islr_rate_ids.id, islr_rate_ids.name,
                rate2)

    def _get_country_fiscal(self, partner_id):
        """ Get the country of the partner
        @param partner_id: partner id whom consult your country
        """
        # TODO: THIS METHOD SHOULD BE IMPROVED
        # DUE TO OPENER HAS CHANGED THE WAY PARTNER
        # ARE USED FOR ACCOUNT_MOVE
        context = self._context or {}
        rp_obj = self.env['res.partner']
        acc_part_id = rp_obj._find_accounting_partner(partner_id)
        if not acc_part_id.country_id:
            raise exceptions.except_orm(
                _('Acción no válida !'),
                _("Retención de ingresos imposible, porque el socio '%s'"
                  "no ha definido el pais en la dirección!") % (
                      acc_part_id.name))
        else:
            return acc_part_id.country_id.id

    def _get_xml_lines(self, ail_brw):
        """ Extract information from the document to generate xml lines
        @param ail_brw: invoice of the document
        """
        context = self._context or {}
        rp_obj = self.env['res.partner']
        acc_part_id = rp_obj._find_accounting_partner(
            ail_brw.move_id.partner_id)
        vendor, buyer, wh_agent = self._get_partners(
             ail_brw.move_id)
        #TODO VERIFICAR SI EL RIF DEL VENDEDOR (PROVEEDOR) DEBE SER BLIGATORIO PARA GENERAR EL XML
        #if not vendor.vat:
        #    raise exceptions.except_orm(
        #        _('Missing RIF number!!!'),
        #        _('Vendor has not RIF number. This value is required for procesing withholding!!!'))

        #TODO EVALUAR SI ESTOS CAMPOS SON REQUERIDOS EN EL XML
        #self.buyer = buyer
        #self.wh_agent = wh_agent
        if vendor.vat :
            vendor = vendor.vat.replace("-","")
        else:
            vendor = str()
        if not ail_brw.concept_id:
            raise exceptions.except_orm(_('¡La factura no ha retenido conceptos!'))
        return {
            'account_invoice_id': ail_brw.move_id.id,
            'islr_wh_doc_line_id': False,
            'islr_xml_wh_doc': False,
            'wh': 0.0,  # To be updated later
            'base': 0.0,  # To be updated later
              # We review the definition because it is in
                                 # NOT NULL

            'invoice_number': ail_brw.move_id.supplier_invoice_number,

            'partner_id': acc_part_id.id,  # Warning Depends if is a customer
                                           # or supplier
            'concept_id': ail_brw.concept_id.id,
            'partner_vat': vendor[0:12] if vendor else str(),  # Warning Depends if is a
                                              # customer or supplier
            'porcent_rete': 0.0,  # To be updated later

            'control_number': ail_brw.move_id.nro_ctrl,
            'account_invoice_line_id': ail_brw.id,
            'concept_code': '000',# To be updated later
            'type': 'invoice'
        }


class IslrWhDocLine(models.Model):
    _name = "islr.wh.doc.line"
    _description = 'Lines of Document Income Withholding'
    
    def convert_amount_to_invoice_currency(self, amount):
        self.ensure_one()
        ut_obj = self.env['l10n.ut']
        f_xc = ut_obj.sxc(
	    self.invoice_id.company_id.currency_id.id,
            self.invoice_id.currency_id.id,
	    self.islr_wh_doc_id.date_uid
        )
        return f_xc(amount)
	
    def convert_amount_to_company_currency(self, amount):
        self.ensure_one()
        ut_obj = self.env['l10n.ut']
        f_xc = ut_obj.sxc(
            self.invoice_id.currency_id.id,
            self.invoice_id.company_id.currency_id.id,
            self.islr_wh_doc_id.date_uid
        )
        return f_xc(amount)

    #@api.depends('amount', 'raw_tax_ut', 'subtract',  'base_amount',
    #             'raw_base_ut', 'retencion_islr')
    def _amount_all(self):
        """ Return all amount relating to the invoices lines
        """
        res = {}
        ut_obj = self.env['l10n.ut']
        for iwdl_brw in self.browse(self.ids):
            res[iwdl_brw.id] = {
                'amount': (iwdl_brw.base_amount * (iwdl_brw.retencion_islr / 100.0)) or 0.0,
                'currency_amount': 0.0,
                'currency_base_amount': 0.0,
            }
            for xml_brw in iwdl_brw.xml_ids:
                res[iwdl_brw.id]['amount'] = xml_brw.wh
            res[iwdl_brw.id]['currency_amount'] = iwdl_brw.convert_amount_to_invoice_currency(
                res[iwdl_brw.id]['amount'])
            res[iwdl_brw.id]['currency_base_amount'] = iwdl_brw.convert_amount_to_invoice_currency(
                iwdl_brw.base_amount)
        #pass
        #return res


    def _retention_rate(self):
        """ Return the retention rate of each line
        """
        res = {}
        for ret_line in self.browse(self.ids):
            if ret_line.invoice_id:
                pass
            else:
                res[ret_line.id] = 0.0
        return res

    name = fields.Char(
            'Descripción', size=64, help="Description of the voucher line")
    invoice_id = fields.Many2one(
            'account.move', 'Factura', ondelete='set null',
            help="Factura para Retener")
    #amount= fields.Float(compute='_amount_all', method=True, digits=(16, 2), string='Withheld Amount',
    #        multi='all', help="Amount withheld from the base amount")
    amount = fields.Float(string='Cantidad retenida', digits=(16, 2), help="Monto retenido del monto base")
    currency_amount= fields.Float(compute='_amount_all', method=True, digits=(16, 2),
            string='Moneda retenida Monto retenido', multi='all',
            help="Monto retenido del monto base")
    base_amount= fields.Float(
            'Cantidad base', digits=dp.get_precision('Withhold ISLR'),
            help="Cantidad base")
    currency_base_amount= fields.Float(compute='_amount_all', method=True, digits=(16, 2),
            string='Monto base en moneda extranjera', multi='all',
            help="Monto retenido del monto base")
    raw_base_ut= fields.Float(
            'Cantidad de UT', digits=dp.get_precision('Withhold ISLR'),
            help="Cantidad de UT")
    raw_tax_ut= fields.Float(
            'Impuesto retenido de UT',
            digits=dp.get_precision('Withhold ISLR'),
            help="Impuesto retenido de UT")
    subtract = fields.Float(
            'Sustraer', digits=dp.get_precision('Withhold ISLR'),
            help="Sustraer")
    islr_wh_doc_id = fields.Many2one(
            'islr.wh.doc', 'Retener documento', ondelete='cascade',
            help="Retención de documentos del impuesto sobre la renta generado por esta factura")
    concept_id = fields.Many2one(
            'islr.wh.concept', 'Concepto de retención',
            help="Concepto de retención asociado a esta tasa")
    retencion_islr = fields.Float(
            'Tasa de retención',
            digits=dp.get_precision('Withhold ISLR'),
            help="Tasa de retención")
    retention_rate = fields.Float(compute=_retention_rate, method=True, string='Tasa de retención',
             help="Withhold rate has been applied to the invoice",
             digits=dp.get_precision('Withhold ISLR'))
    xml_ids = fields.One2many(
            'islr.xml.wh.line', 'islr_wh_doc_line_id', 'XML Lines',
            help='ID de línea de factura de retención XML')
    iwdi_id = fields.Many2one(
            'islr.wh.doc.invoices', 'Factura retenida', ondelete='cascade',
            help="Facturas retenidas")
    partner_id = fields.Many2one('res.partner', related='islr_wh_doc_id.partner_id', string='Partner', store=True)
    fiscalyear_id = fields.Many2one( 'account.fiscalyear', string='Fiscalyear',store=True)


class IslrWhHistoricalData(models.Model):
    _name = "islr.wh.historical.data"
    _description = 'Lines of Document Income Withholding'


    partner_id = fields.Many2one(
            'res.partner', 'Partner', readonly=False, required=True,
            help="Partner for this historical data")
    fiscalyear_id = fields.Many2one(
            'account.fiscalyear', 'Fiscal Year', readonly=False, required=True,
            help="Fiscal Year to applicable to this cumulation")
    concept_id = fields.Many2one(
            'islr.wh.concept', 'Entrada de diario', required=True,
            help="Concepto de retención asociado a estos datos históricos")
    raw_base_ut = fields.Float(
            'Cantidad acumulada de UT', required=True,
            digits=dp.get_precision('Withhold ISLR'),
            help="Cantidad de UT")
    raw_tax_ut = fields.Float(
            'Impuesto retenido de UT acumulado', required=True,
            digits=dp.get_precision('Withhold ISLR'),
            help="Impuesto retenido de UT")

