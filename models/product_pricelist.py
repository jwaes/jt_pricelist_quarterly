import logging
from odoo import api, fields, models
from odoo.tools import date_utils
from datetime import datetime
from pytz import timezone, UTC
from odoo.exceptions import ValidationError
import math

_logger = logging.getLogger(__name__)
class Pricelist(models.Model):
    _inherit = "product.pricelist"

    description = fields.Html('Description', default='', translate=True, help="This description gets printed on the pricelist publications")

    description_internal = fields.Text('Description internal', help="This is for internal use only, describe for who this pricelist is intended, what discounts can be applied")

    def write(self, vals):
        res =  super().write(vals)
        _logger.info("writing ... ")
        _logger.info(vals)
        _logger.info("====")
        for item in self.item_ids:
            item._calculate_daterange()
        return res


class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    daterange_type = fields.Selection([
        ('default', 'Default'),
        ('quarter', 'Quarter'),
    ], string='Daterange type', default="default")

    def _get_default_q_year(self):
        value = fields.Datetime.now().year
        return int(value)

    def _get_default_q(self):
        value = fields.Datetime.now().month / 3
        value = math.ceil(value)
        return int(value)

    daterange_q = fields.Integer(string='Q', default=_get_default_q)
    daterange_q_year = fields.Integer('YYYY', default=_get_default_q_year)

    quarter = fields.Char(compute='_compute_quarter', string='Quarter')
    
    @api.depends('daterange_q', 'daterange_q_year', 'daterange_type')
    def _compute_quarter(self):
        for rec in self:
            if rec.daterange_type == 'quarter':
                rec.quarter = '%sQ%s' % (rec.daterange_q_year, rec.daterange_q)
            else:
                rec.quarter = None

    @api.constrains('daterange_q_year','daterange_q')
    def _check_value(self):
        for rec in self:
            if rec.daterange_q_year > 3000 or rec.daterange_q_year < 2000:
                raise ValidationError(_('Enter a valid year'))
            if rec.daterange_q > 4 or rec.daterange_q < 1:
                raise ValidationError(_('Enter a valid quarter'))            

    @api.onchange('daterange_q')
    def _onchange_daterange_q(self):
        for rec in self:
            rec._calculate_daterange()


    @api.onchange('daterange_q_year')
    def _onchange_daterange_q_year(self):
        for rec in self:
            if rec.daterange_q_year:
                rec._calculate_daterange()

    @api.onchange('daterange_type')
    def _onchange_daterange_type(self):
        for rec in self:
            if rec.daterange_type == 'quarter':
                rec._calculate_daterange()            

    @api.depends('date_start', 'date_end')
    def _calculate_daterange(self):
        for rec in self:
            rec._check_value()
            if rec.daterange_type == 'quarter':        
                month = ((rec.daterange_q - 1) * 3) + 1
                tz = timezone(self.env.user.tz or 'UTC')
                starter_date = datetime(year=rec.daterange_q_year, month=month, day=1, hour=0, minute=0, second=0)
                ending_date = date_utils.end_of(starter_date, "quarter").replace(hour=23, minute=59, second=59)

                starter_date_utc = tz.localize(starter_date).astimezone(UTC)
                ending_date_utc = tz.localize(ending_date).astimezone(UTC)

                rec.date_end = ending_date_utc.replace(tzinfo=None)
                rec.date_start = starter_date_utc.replace(tzinfo=None)
                _logger.info("setting start and end dates")
            else:
                rec.daterange_q = rec._get_default_q()
                rec.daterange_q_year = rec._get_default_q_year()
                _logger.info("re-setting start and end dates")
