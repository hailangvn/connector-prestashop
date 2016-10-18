# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from openerp import models, fields

from ...unit.backend_adapter import GenericAdapter
from ...backend import prestashop


class PrestashopResLang(models.Model):
    _name = 'prestashop.res.lang'
    _inherit = 'prestashop.binding'
    _inherits = {'res.lang': 'openerp_id'}

    openerp_id = fields.Many2one(
        comodel_name='res.lang',
        required=True,
        ondelete='cascade',
        string='Lang',
    )
    active = fields.Boolean(
        string='Active in prestashop',
        default=False,
    )

    _sql_constraints = [
        ('prestashop_erp_uniq', 'unique(backend_id, openerp_id)',
         'A erp record with same ID on PrestaShop already exists.'),
    ]


class ResLang(models.Model):
    _inherit = 'res.lang'

    prestashop_bind_ids = fields.One2many(
        comodel_name='prestashop.res.lang',
        inverse_name='openerp_id',
        readonly=True,
        string='PrestaShop Bindings',
    )


@prestashop
class ResLangAdapter(GenericAdapter):
    _model_name = 'prestashop.res.lang'
    _prestashop_model = 'languages'