# -*- coding: utf-8 -*-
##############################################################################
#
#    Prestashoperpconnect : OpenERP-PrestaShop connector
#    Copyright (C) 2013 Akretion (http://www.akretion.com/)
#    @author: Alexis de Lattre <alexis.delattre@akretion.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import openerp.addons.connector.backend as backend
from openerp.addons.connector.queue.job import (
    whitelist_unpickle_global
)
from pytz import _p


prestashop = backend.Backend('prestashop')
prestashop1500 = backend.Backend(parent=prestashop, version='1.5')


# Need to be compatible with last version of connector.
# Will be useless next version since date in import jobs does not use pytz
# anymore.
whitelist_unpickle_global(_p)
