from openerp import api, fields, models
from openerp.exceptions import Warning

# from openerp.addons.checklist.models.utils import QUANT_OWNERS


def o(line):
    return line or ''


class create_onsite_checklist(models.TransientModel):
    _name = 'create.onsite.checklist'

    quant = fields.Many2one('stock.quant')
    checklist = fields.Many2one('project.project', domain="[('state','=','template')]", required=1)
    user = fields.Many2one('res.users', 'Assign To')

    rh_job_number = fields.Char('RH Job Number', required=1)
    rh_job_date = fields.Date('RH Job Date', default=fields.Date.context_today, required=1)
    product = fields.Many2one('product.product', 'Model')
    customer = fields.Many2one('res.partner')  # domain=QUANT_OWNERS

    description = fields.Text()  # info1 + info2

    destination = fields.Many2one('res.partner', required=1)
    dest_name = fields.Char('Name *', help="Type here to auto-complete Destination")
    dest_street = fields.Char('Street')
    dest_street2 = fields.Char('Street2')
    dest_zip = fields.Char('ZIP')
    dest_city = fields.Char('City')
    dest_state = fields.Many2one('res.country.state', 'State')
    dest_country = fields.Many2one('res.country', 'Country')
    found_name = fields.Char('Name', related='destination.name')
    found_street = fields.Char('Street', related='destination.street')
    found_street2 = fields.Char('Street2', related='destination.street2')
    found_zip = fields.Char('ZIP', related='destination.zip')
    found_city = fields.Char('City', related='destination.city')
    found_state = fields.Many2one('res.country.state', 'State', related='destination.state_id')
    found_country = fields.Many2one('res.country', 'Country', related='destination.country_id')
    hint_several = fields.Html(readonly=1)
    hint_mismatch = fields.Html(readonly=1)
    hint_new = fields.Html(readonly=1)

    contact = fields.Many2one('res.partner')
    cont_name = fields.Char('Name *', help="Type here to auto-complete Contact")
    cont_phone = fields.Char('Phone')
    found_cont_name = fields.Char('Name', related='contact.name')
    found_cont_phone = fields.Char('Phone', related='contact.phone')
    hint_several_cont = fields.Html(readonly=1)
    hint_mismatch_cont = fields.Html(readonly=1)
    hint_new_cont = fields.Html(readonly=1)

    @api.onchange('quant')
    def onchange_quant(self):
        if self.quant:
            self.customer = self.quant.owner_id
            self.product = self.quant.product_id

    @api.onchange('customer', 'product')
    def onchange_customer_product(self):
        dom = [('state', '=', 'template')]
        if self.customer:
            dom.append(('partner_id', '=', self.customer.id))
        if self.product:
            dom.append(('products', 'in', [self.product.id]))
        if len(dom) > 1:
            templates = self.env['project.project'].search(dom)
            if templates:
                self.checklist = templates[0]
        return {'domain': {'checklist': dom}}

    @api.onchange('rh_job_date')
    def onchange_rh_date(self):
        """ if we would listen to rh_job_date right from onchange_rh_job method, onchange_rh_job would be called twice
        after self.rh_job_date is set at the end of it. hence we use a separate method + context flag in view. """
        if self._context.get('load_from_rh'):
            self.onchange_rh_job()

    @api.onchange('rh_job_number')
    def onchange_rh_job(self):
        if not self.rh_job_number: return
        db = self.env['base.external.dbsource'].search([('name', '=', 'rockhopper')])
        if not db:
            raise Warning("External Database Source named 'rockhopper' not found. "
                          "Configure it in Settings > Database Structure > Database Sources.")
        job_id = int(self.rh_job_number)
        job_date = self.rh_job_date
        sql_getdate = '''SELECT job_date, caller, phone
            FROM job WHERE id = %s AND job_date BETWEEN DATE_SUB(%s, INTERVAL 180 DAY) AND %s
            ORDER BY job_date DESC
            LIMIT 1'''
        res = db.execute(sql_getdate, sqlparams=(job_id, job_date, job_date))
        if not res: return
        job_date = res[0][0]
        caller, phone = res[0][1], res[0][2]
        sql_getdest = '''SELECT s.name, s.address1, s.address2, sb.name, sb.zone, sb.state, sb.postcode, s.info1, s.info2
            FROM stop s JOIN suburb sb ON s.suburb_id = sb.code
            WHERE s.job_id = %s AND s.job_date = %s AND s.stop_number = 2
            LIMIT 1
        '''
        res = db.execute(sql_getdest, sqlparams=(job_id, job_date))
        if not res: return
        countries = [self.env.ref('base.au').id, self.env.ref('base.nz').id]
        self.dest_name = res[0][0]
        self.dest_street = res[0][1]
        self.dest_street2 = res[0][2]
        self.dest_city = '%s, %s' % (res[0][3], res[0][4])
        if res[0][5]:
            self.dest_state = self.dest_state.search([('code', '=', res[0][5]), ('country_id', 'in', countries)])
            if self.dest_state:
                self.dest_country = self.dest_state.country_id
        self.dest_zip = res[0][6]
        self.description = '\n'.join(filter(None, [res[0][7], res[0][8]]))
        self.cont_name = caller
        self.cont_phone = phone
        self.rh_job_date = job_date

    @api.onchange('dest_name')
    def onchange_dest_name(self):
        if self.dest_name:
            dest = [x[0] for x in self.destination.name_search(self.dest_name)]
            self.destination = dest and dest[0] or False
            if len(dest) > 1:
                self.hint_several = 'Several Destinations found. Pick one!'
                return {'domain': {'destination': [('id', 'in', dest)]}}
            if not self.destination:
                self.hint_new = self._hint_new('Destination', self.dest_name)
        self.hint_several = False
        return {'domain': {'destination': []}}

    def _hint_new(self, what, from_name):
        hint_new = ['<b>%s</b> not found.',
                    '<i class="fa fa-lightbulb-o"/> Try typing words from <b>%s</b> here.',
                    '<i class="fa fa-lightbulb-o"/> To create a new ' + what + ', copy-paste <b>%s</b> here and '
                    'choose <i>Create "<b>%s</b>"</i> or <i>Create and Edit</i>.']
        args = [from_name] * 4
        if ',' in from_name:
            hint_new.pop(1); args.pop(1)  # don't Try typing words from ...
            several_companies = self.env['res.partner'].with_context(no_create_company=1). \
                _as_company_contact(from_name)._default_hint_several()
            if several_companies:
                hint_new.pop(1); args.pop(1); args.pop(1)  # don't Create ...
                hint_new.append('<i class="fa fa-exclamation-triangle"/> Several <b>%s</b> companies found.')
                hint_new.append('<i class="fa fa-lightbulb-o"/> To create new ' + what + ' and <u>choose the right '
                                'company</u> for it, copy-paste <b>%s</b> here and choose <i>Create and Edit</i>.')
                args.append(from_name.split(',')[0].strip())
                args.append(from_name)
        return '<br/>'.join(hint_new) % tuple(args)

    @api.onchange('destination')
    def onchange_destination(self):
        if 'default_street' in self._context:
            self.hint_several = False
        if self.destination:
            self.hint_new = False
            if self.cont_name:
                self.cont_name = self._full_cont_name()

    def _full_cont_name(self):
        if ',' in self.cont_name:
            return self.cont_name
        return '%s, %s' % ((self.destination.parent_id or self.destination).name, self.cont_name)

    @api.onchange('cont_name', 'destination')
    def onchange_cont_name(self):
        if self.cont_name and self.destination:
            full_cont_name = self._full_cont_name()
            cont = [x[0] for x in self.contact.name_search(full_cont_name)]
            self.contact = cont and cont[0] or False
            if len(cont) > 1:
                self.hint_several_cont = 'Several Contacts found. Pick one!'
                return {'domain': {'contact': [('id', 'in', cont)]}}
            if not self.contact:
                self.hint_new_cont = self._hint_new('Contact', full_cont_name)
        self.hint_several_cont = False
        return {'domain': {'contact': []}}

    @api.onchange('contact')
    def onchange_contact(self):
        if 'default_phone' in self._context:
            self.hint_several_cont = False
        if self.contact:
            self.hint_new_cont = False

    @api.multi
    def create_checklist(self):
        self.env['project.project'].create({
            'rh_job_number': int(self.rh_job_number), 'rh_job_date': self.rh_job_date, 'partner_id': self.destination.id,
            'user_id': self.user.id, 'template': self.checklist.id, 'alias_model': 'project.task', 'state': 'draft',
            'contact': self.contact.id, 'description': self.description,
            'name': self.rh_job_number, 'type_ids': [(6, 0, [])],  # prevent default types
        })

    @api.onchange('dest_street', 'dest_street2', 'dest_city', 'dest_state', 'dest_country', 'dest_zip', 'destination',
                  'found_street', 'found_street2', 'found_city', 'found_state', 'found_country', 'found_zip')
    def onchange_address(self):
        self.hint_mismatch = False
        if not self.destination:
            return
        match = o(self.found_street) == o(self.dest_street) and o(self.found_street2) == o(self.dest_street2) \
                    and o(self.found_city) == o(self.dest_city) and o(self.found_zip) == o(self.dest_zip) \
                    and self.found_state == self.dest_state and self.found_country == self.dest_country
        if not match:
            self.hint_mismatch = \
                'Address details don\'t match in <b>RH</b> and <b>Odoo</b>.<br/>' \
                'You might need to:<br/>' \
                '<i class="fa fa-lightbulb-o"/> Update Odoo data (on the right) with RH data.<br/>' \
                '<i class="fa fa-lightbulb-o"/> Create new Destination: click on Destination field, hit Down, choose ' \
                '<i>Create "<b>%s</b>"</i> or <i>Create and Edit</i>.' % self.dest_name

    @api.onchange('cont_phone', 'contact', 'found_cont_phone')
    def onchange_contact_data(self):
        self.hint_mismatch_cont = False
        if not self.contact:
            return
        match = o(self.found_cont_phone) == o(self.cont_phone)
        if not match:
            self.hint_mismatch_cont = \
                'Contact details don\'t match in <b>RH</b> and <b>Odoo</b>.<br/>' \
                'You might need to:<br/>' \
                '<i class="fa fa-lightbulb-o"/> Update Odoo data (on the right) with RH data.<br/>' \
                '<i class="fa fa-lightbulb-o"/> Create new Contact: click on Contact field, hit Down, choose ' \
                '<i>Create "<b>%s</b>"</i> or <i>Create and Edit</i>.' % self.cont_name
