from openerp import api, fields, models


class res_partner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _get_several_parents(self, parent_id):
        parent = self.browse(parent_id)
        several_parents = self.search([('name', '=', parent.name)])
        return len(several_parents) > 1 and several_parents

    def _hint_several_msg(self, parent_id):
        return parent_id and self._get_several_parents(parent_id) and 'Several Companies found. Pick one!' or False

    def _hint_several(self):
        for x in self:
            x.hint_several = self._hint_several_msg(x.parent_id.id)

    def _default_hint_several(self):
        return self._hint_several_msg(self._context.get('default_parent_id'))

    hint_several = fields.Html(compute=_hint_several, default=_default_hint_several)

    def _as_company_contact(self, name):
        """ Split names like 'XXX, YYY' into Company and Contact. Create Company if doesn't exist. """
        if ',' in name:
            company, contact = [x.strip() for x in name.split(',', 1)]
            comp = company and next((x for x in self.name_search(company)), False)
            parent = comp and comp[0] or company and not self._context.get('no_create_company') and \
                     self.with_context(default_name=company, default_is_company=1).create({}).id
            if parent:
                default_type = self._context.get('default_type', 'delivery')
                self = self.with_context(default_parent_id=parent, default_name=contact, default_type=default_type)
        if 'default_is_company' not in self._context:
            self = self.with_context(default_is_company=not bool(self._context.get('default_parent_id')))
        return self

    @api.model
    def default_get(self, fields_list):
        name = self._context.get('default_name', '')
        self = self._as_company_contact(name)
        return super(res_partner, self).default_get(fields_list)

    @api.model
    def name_create(self, name):
        self = self._as_company_contact(name)
        contact = self._context.get('default_name', name)
        assert contact, 'Name should be specified'
        return super(res_partner, self).name_create(contact)

    def _apply_several_parents_domain(self, cr, uid, res, parent_id, context):
        if parent_id:
            several_parents = self._get_several_parents(cr, uid, parent_id, context=context)
            if several_parents:
                res.setdefault('domain', {})['parent_id'] = [('id', 'in', several_parents.ids)]

    def onchange_address(self, cr, uid, ids, use_parent_address, parent_id, context=None):
        res = super(res_partner, self).onchange_address(cr, uid, ids, use_parent_address, parent_id, context=context)
        self._apply_several_parents_domain(cr, uid, res, parent_id, context)
        return res
