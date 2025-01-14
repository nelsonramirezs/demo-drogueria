# coding: utf-8
###########################################################################

import base64
import odoo.addons as addons
from odoo import models, fields, api


class WhVatInstaller(models.TransientModel):

    """ wh_vat_installer
    """
    _name = 'base_withholding_iva.installer'
    _inherit = 'res.config.installer'
    _description = __doc__

    @api.model
    def default_get(self, field_list):
        """ Return information relating to the withholding regime
        """
        # NOTE: use field_list argument instead of fields for fix the pylint
        # error W0621 Redefining name 'fields' from outer scope
        data = super(WhVatInstaller, self).default_get(field_list)
        gaceta = open(addons.get_module_resource(
            'locv_withholding_iva', 'files',
            'RegimendeRetencionesdelIVA.odt'), 'rb')
        data['gaceta'] = base64.encodestring(gaceta.read())
        return data

    name = fields.Char(
        string='First Data', size=34,
        default='RegimendeRetencionesdelIVA.odt')
    gaceta = fields.Binary(
        string='Law related', readonly=True,
        help="Law related where we are referencing this module")
    description = fields.Text(
        string='Description', readonly=True,
        default="""
        With this wizard you will configure all needs for work out of the box
        with This module,
        First: Setting if The company will be withholding agent.
        Second: Create Minimal Journals.
        Third: Assign Account to work.
        Fourth: Ask if you have internet conexion and you want to connect to
        SENIAT and update all your partners information.
        """,
        help='description of the installer')


class WhIvaConfig(models.TransientModel):
    _name = 'wh_iva.config'
    _inherit = 'res.config'

    name = fields.Char(string='Name', size=64, help='name')
    wh = fields.Boolean(
        string='Are You Withholding Agent?',
        help='if is withholding agent')
    journal_purchase_vat = fields.Char(
        string="Journal Wh VAT Purchase", size=64,
        default="Journal VAT Withholding Purchase",
        help="Journal for purchase operations involving VAT Withholding")
    journal_sale_vat = fields.Char(
        string="Journal Wh VAT Sale", size=64,
        default="Journal VAT Withholding Sale",
        help="Journal for sale operations involving VAT Withholding")

    @api.model
    def _show_company_data(self):
        """ We only want to show the default company data in demo mode,
        otherwise users tend to forget to fill in the real company data in
        their production databases
        """
        return self.env['ir.model.data'].get_object(
            'base', 'module_meta_information').demo

    # @api.model
    # def default_get(self, fields_list):
    #     """ Get default company if any, and the various other fields
    #     from the company's fields
    #     """
    #     defaults = super(WhIvaConfig, self).default_get(fields_list)
    #     # Set Vauxoo logo on config Window.
    #     logo = open(addons.get_module_resource(
    #         'locv_withholding_iva', 'images', 'angelfalls.jpg'), 'rb')
    #     defaults['config_logo'] = base64.encodestring(logo.read())
    #     return defaults

    @api.model
    def _create_journal(self, name, jtype, code):
        """ Create a journal
        @param name: journal name
        @param type: journal type
        @param code: code for journal
        """
        self.env['account.journal'].create({
            'name': name,
            'type': jtype,
            'code': code,
            'view_id': 3, }
        )


    def execute(self):
        """ In this method I will configure all needs for work out of the box with
        This module,
        First: Setting if The company will be agent of retention.
        Second: Create Minimal Journals.
        Third: Assign Account to work.
        Fourth: Ask if you have internet conexion and you want to connect to
        SENIAT
        and update all your partners information.
        """
        partner = self.env.user.company_id.partner_id.id
        if self.journal_purchase_vat:
            self._create_journal(self.journal_purchase_vat,
                                 'iva_purchase', 'VATP')
        if self.journal_sale_vat:
            self._create_journal(self.journal_sale_vat,
                                 'iva_sale', 'VATS')
        if self.wh:
            partner.write({'wh_iva_agent': 1, 'wh_iva_rate': 75.00})
            print("INSTALLER LINEA 122")
        else:
            partner.write({'wh_iva_agent': 0, 'wh_iva_rate': 75.00})
            print("INSTALLER LINEA 125")
            print("SOLO PORQUEE S FINAL DEL CÓDIGO")
