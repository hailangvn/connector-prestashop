# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import _

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, external_to_m2o

class ShopGroupImporter(Component):
    _name = 'prestashop.shop.group.importer'
    _inherit = 'prestashop.importer'
    _apply_on = 'prestashop.shop.group'

class ShopGroupMapper(Component):
    _name = 'prestashop.shop.group.mapper'
    _inherit = 'prestashop.import.mapper'
    _apply_on = 'prestashop.shop.group'


    direct = [('name', 'name')]

    @mapping
    def name(self, record):
        name = record['name']
        if name is None:
            name = _('Undefined')
        return {'name': name}



#TODO: Check deletion as backend importer list multiple objects to import
# class ShopGroupBatchImporter(Component):
#     _name = 'prestashop.shop.group.batch.importer'
#     _inherit = 'prestashop.direct.batch.importer'
#     _apply_on = 'prestashop.shop.group'
 
#     _model_name = 'prestashop.shop.group'
