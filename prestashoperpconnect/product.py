# -*- coding: utf-8 -*-
###############################################################################
#                                                                             #
#   Prestashoperpconnect for OpenERP                                          #
#   Copyright (C) 2013 Akretion                                               #
#                                                                             #
#   This program is free software: you can redistribute it and/or modify      #
#   it under the terms of the GNU Affero General Public License as            #
#   published by the Free Software Foundation, either version 3 of the        #
#   License, or (at your option) any later version.                           #
#                                                                             #
#   This program is distributed in the hope that it will be useful,           #
#   but WITHOUT ANY WARRANTY; without even the implied warranty of            #
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the             #
#   GNU Affero General Public License for more details.                       #
#                                                                             #
#   You should have received a copy of the GNU Affero General Public License  #
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.     #
#                                                                             #
###############################################################################

import datetime
import mimetypes
import json

from openerp import SUPERUSER_ID
from openerp.osv import fields, orm

from openerp.addons.product.product import check_ean

from openerp.addons.connector.queue.job import job
from openerp.addons.connector.event import on_record_write
from openerp.addons.connector.unit.synchronizer import ExportSynchronizer
from .unit.import_synchronizer import DelayedBatchImport
from .unit.import_synchronizer import PrestashopImportSynchronizer
from .unit.import_synchronizer import import_record
from openerp.addons.connector.unit.mapper import mapping

from prestapyt import PrestaShopWebServiceError

from .unit.backend_adapter import GenericAdapter, PrestaShopCRUDAdapter

from .connector import get_environment
from .unit.mapper import PrestashopImportMapper
from backend import prestashop


##########  product category ##########
@prestashop
class ProductCategoryMapper(PrestashopImportMapper):
    _model_name = 'prestashop.product.category'

    direct = [
        ('position', 'sequence'),
        ('description', 'description'),
        ('link_rewrite', 'link_rewrite'),
        ('meta_description', 'meta_description'),
        ('meta_keywords', 'meta_keywords'),
        ('meta_title', 'meta_title'),
        ('id_shop_default', 'default_shop_id'),
    ]

    @mapping
    def name(self, record):
        if record['name'] is None:
            return {'name': ''}
        return {'name': record['name']}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def parent_id(self, record):
        if record['id_parent'] == '0':
            return {}
        return {'parent_id': self.get_openerp_id(
            'prestashop.product.category',
            record['id_parent']
        )}

    @mapping
    def data_add(self, record):
        if record['date_add'] == '0000-00-00 00:00:00':
            return {'date_add': datetime.datetime.now()}
        return {'date_add': record['date_add']}

    @mapping
    def data_upd(self, record):
        if record['date_upd'] == '0000-00-00 00:00:00':
            return {'date_upd': datetime.datetime.now()}
        return {'date_upd': record['date_upd']}


# Product image connector parts
@prestashop
class ProductImageMapper(PrestashopImportMapper):
    _model_name = 'prestashop.product.image'

    direct = [
        ('content', 'file'),
    ]

    @mapping
    def product_id(self, record):
        return {'product_id': self.get_openerp_id(
            'prestashop.product.product',
            record['id_product']
        )}

    @mapping
    def name(self, record):
        return {'name': record['id_product']+'_'+record['id_image']}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def extension(self, record):
        return {"extension": mimetypes.guess_extension(record['type'])}


########  product  ########
@prestashop
class ProductMapper(PrestashopImportMapper):
    _model_name = 'prestashop.product.product'

    direct = [
        ('description', 'description_html'),
        ('description_short', 'description_short_html'),
        ('weight', 'weight'),
        ('wholesale_price', 'standard_price'),
        ('price', 'list_price'),
        ('id_shop_default', 'default_shop_id'),
        ('link_rewrite', 'link_rewrite'),
        ('reference', 'reference'),
    ]

    @mapping
    def name(self, record):
        if record['name']:
            return {'name': record['name']}
        return {'name': 'noname'}

    @mapping
    def date_add(self, record):
        if record['date_add'] == '0000-00-00 00:00:00':
            return {'date_add': datetime.datetime.now()}
        return {'date_add': record['date_add']}

    @mapping
    def date_upd(self, record):
        if record['date_upd'] == '0000-00-00 00:00:00':
            return {'date_upd': datetime.datetime.now()}
        return {'date_upd': record['date_upd']}

    def has_combinations(self, record):
        combinations = record.get('associations', {}).get(
            'combinations', {}).get('combinations', [])
        return len(combinations) != 0

    @mapping
    def attribute_set_id(self, record):
        if self.has_combinations(record) and 'attribute_set_id' in record:
            return {'attribute_set_id': record['attribute_set_id']}
        return {}

    def _product_code_exists(self, code):
        model = self.session.pool.get('product.product')
        product_ids = model.search(self.session.cr, SUPERUSER_ID, [
            ('default_code', '=', code),
            ('company_id', '=', self.backend_record.company_id.id),
        ])
        return len(product_ids) > 0

    @mapping
    def default_code(self, record):
        code = record.get('reference')
        if not code:
            code = "backend_%d_product_%s" % (
                self.backend_record.id, record['id']
            )
        if not self._product_code_exists(code):
            return {'default_code': code}
        i = 1
        current_code = '%s_%d' % (code, i)
        while self._product_code_exists(current_code):
            i += 1
            current_code = '%s_%d' % (code, i)
        return {'default_code': current_code}

    @mapping
    def active(self, record):
        return {'always_available': bool(int(record['active']))}

    @mapping
    def sale_ok(self, record):
        # if this product has combinations, we do not want to sell this product,
        # but its combinations (so sale_ok = False in that case).
        sale_ok = (record['available_for_order'] == '1'
                   and not self.has_combinations(record))
        return {'sale_ok': sale_ok}

    @mapping
    def purchase_ok(self, record):
        return {'purchase_ok': not self.has_combinations(record)}

    @mapping
    def categ_id(self, record):
        if not int(record['id_category_default']):
            return
        category_id = self.get_openerp_id(
            'prestashop.product.category',
            record['id_category_default']
        )
        if category_id is not None:
            return {'categ_id': category_id}

        categories = record['associations'].get('categories', {}).get(
            'category', [])
        if not isinstance(categories, list):
            categories = [categories]
        if not categories:
            return
        category_id = self.get_openerp_id(
            'prestashop.product.category',
            categories[0]['id']
        )
        return {'categ_id': category_id}


    @mapping
    def categ_ids(self, record):
        categories = record['associations'].get('categories', {}).get(
            'category', [])
        if not isinstance(categories, list):
            categories = [categories]
        product_categories = []
        for category in categories:
            category_id = self.get_openerp_id(
                'prestashop.product.category',
                category['id']
            )
            product_categories.append(category_id)

        return {'categ_ids': [(6, 0, product_categories)]}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def company_id(self, record):
        return {'company_id': self.backend_record.company_id.id}

    @mapping
    def ean13(self, record):
        if record['ean13'] in ['', '0']:
            return {}
        if check_ean(record['ean13']):
            return {'ean13': record['ean13']}
        return {}

    @mapping
    def taxes_id(self, record):
        if record['id_tax_rules_group'] == '0':
            return {}
        tax_group_id = self.get_openerp_id(
            'prestashop.account.tax.group',
            record['id_tax_rules_group']
        )
        tax_group_model = self.session.pool.get('account.tax.group')
        tax_ids = tax_group_model.read(
            self.session.cr,
            self.session.uid,
            tax_group_id,
            ['tax_ids']
        )
        return {"taxes_id": [(6, 0, tax_ids['tax_ids'])]}

    @mapping
    def type(self, record):
        # If the product has combinations, this main product is not a real
        # product. So it is set to a 'service' kind of product. Should better be
        # a 'virtual' product... but it does not exist...
        # The same if the product is a virtual one in prestashop.
        if ((record['type']['value'] and record['type']['value'] == 'virtual')
                or self.has_combinations(record)):
            return {"type": 'service'}
        return {"type": 'product'}


@prestashop
class ProductAdapter(GenericAdapter):
    _model_name = 'prestashop.product.product'
    _prestashop_model = 'products'
    _export_node_name = 'product'

    def update_inventory(self, id, attributes):
        api = self.connect()
        if attributes is None:
            attributes = {}
        return api.edit('stock_availables', attributes)


@prestashop
class ProductInventoryExport(ExportSynchronizer):
    _model_name = ['prestashop.product.product']

    def get_filter(self, product):
        binder = self.get_binder_for_model()
        prestashop_id = binder.to_backend(product.id)
        return {
            'filter[id_product]': prestashop_id,
            'filter[id_product_attribute]': 0
        }

    def run(self, binding_id, fields):
        """ Export the product inventory to Prestashop """
        product = self.session.browse(self.model._name, binding_id)
        adapter = self.get_connector_unit_for_model(
            GenericAdapter, '_import_stock_available'
        )
        filter = self.get_filter(product)
        response = adapter.search(filter)
        #assert len(response) == 1, 'Found %d stocks' % len(response)
        for stock_id in response:
            stock = adapter.read(stock_id)
            stock['quantity'] = int(product.quantity)
            adapter.write(stock_id, stock)


@prestashop
class ProductInventoryBatchImport(DelayedBatchImport):
    _model_name = ['_import_stock_available']

    def run(self, filters=None, **kwargs):
        if filters is None:
            filters = {}
        filters['display'] = '[id_product,id_product_attribute]'
        return super(ProductInventoryBatchImport, self).run(filters, **kwargs)

    def _run_page(self, filters, **kwargs):
        records = self.backend_adapter.get(filters)
        for record in records['stock_availables']['stock_available']:
            self._import_record(record, **kwargs)
        return records['stock_availables']['stock_available']

    def _import_record(self, record, **kwargs):
        """ Delay the import of the records"""
        import_record.delay(
            self.session,
            '_import_stock_available',
            self.backend_record.id,
            record,
            **kwargs
        )


@prestashop
class ProductInventoryImport(PrestashopImportSynchronizer):
    _model_name = ['_import_stock_available']

    def _get_quantity(self, record):
        filters = {
            'filter[id_product]': record['id_product'],
            'filter[id_product_attribute]': record['id_product_attribute'],
            'display': '[quantity]',
        }
        quantities = self.backend_adapter.get(filters)
        all_qty = 0
        quantities = quantities['stock_availables']['stock_available']
        if isinstance(quantities, dict):
            quantities = [quantities]
        for quantity in quantities:
            all_qty += int(quantity['quantity'])
        return all_qty

    def _get_product(self, record):
        if record['id_product_attribute'] == '0':
            binder = self.get_binder_for_model('prestashop.product.product')
            return binder.to_openerp(record['id_product'], unwrap=True)
        binder = self.get_binder_for_model('prestashop.product.combination')
        return binder.to_openerp(record['id_product_attribute'], unwrap=True)

    def run(self, record):
        self._check_dependency(record['id_product'], 'prestashop.product.product')
        if record['id_product_attribute'] != '0':
            self._check_dependency(record['id_product_attribute'], 'prestashop.product.combination')

        qty = self._get_quantity(record)
        if qty < 0:
            qty = 0
        product_id = self._get_product(record)

        product_qty_obj = self.session.pool['stock.change.product.qty']
        vals = product_qty_obj.default_get(
            self.session.cr, self.session.uid, ['location_id'], {}
        )
        vals['product_id'] = product_id
        vals['new_quantity'] = qty
        
        product_qty_id = self.session.create("stock.change.product.qty", vals)
        context = {'active_id': product_id}
        product_qty_obj.change_product_qty(
            self.session.cr,
            self.session.uid,
            [product_qty_id],
            context=context
        )


@prestashop
class ProductInventoryAdapter(GenericAdapter):
    _model_name = '_import_stock_available'
    _prestashop_model = 'stock_availables'
    _export_node_name = 'stock_available'

    def get(self, options=None):
        api = self.connect()
        return api.get(self._prestashop_model, options=options)



# fields which should not trigger an export of the products
# but an export of their inventory
INVENTORY_FIELDS = ('quantity',)


@on_record_write(model_names=[
    'prestashop.product.product',
    'prestashop.product.combination'
])
def prestashop_product_stock_updated(session, model_name, record_id,
                                     fields=None):
    if session.context.get('connector_no_export'):
        return
    inventory_fields = list(set(fields).intersection(INVENTORY_FIELDS))
    if inventory_fields:
        export_inventory.delay(session, model_name,
                               record_id, fields=inventory_fields,
                               priority=20)


@job
def export_inventory(session, model_name, record_id, fields=None):
    """ Export the inventory configuration and quantity of a product. """
    product = session.browse(model_name, record_id)
    backend_id = product.backend_id.id
    env = get_environment(session, model_name, backend_id)
    inventory_exporter = env.get_connector_unit(ProductInventoryExport)
    return inventory_exporter.run(record_id, fields)

@job
def import_inventory(session, backend_id):
    env = get_environment(session, '_import_stock_available', backend_id)
    inventory_importer = env.get_connector_unit(ProductInventoryBatchImport)
    return inventory_importer.run()
