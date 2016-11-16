from openerp import api, fields, models


class workshop_quants(models.TransientModel):
    _name = 'workshop.quants'

    def get_quants(self):
        return self.env['stock.quant'].browse(self.env.context['active_ids'])

    def _default_quant(self):
        return self.env.context['active_ids'][0]

    def _default_checklist(self):
        quant = self.get_quants()[0]
        templates = self.env['project.project'].search([('state', '=', 'template'), ('partner_id', '=', quant.owner_id.id)])
        res = templates.filtered(lambda x: quant.product_id in x.products) or templates
        return res and res[0] or False

    quant = fields.Many2one('stock.quant', default=_default_quant, readonly=True)
    checklist = fields.Many2one('project.project', domain=[('state', '=', 'template')], default=_default_checklist)
    user = fields.Many2one('res.users', 'Assign To')

    @api.multi
    def create_checklist(self):
        assert self.env.context.get('active_model') == 'stock.quant', 'Context broken when creating workshop checklist'

        quants = self.get_quants()
        q = quants[0]
        if not self.env.context.get('skip_quant'):
            self.env['project.project'].create({
                'quant': q.id, 'partner_id': q.owner_id.id, 'user_id': self.user.id, 'template': self.checklist.id,
                'alias_model': 'project.task', 'state': 'draft', 'name': '#%s' % q.id,
                'type_ids': [(6, 0, [])],  # prevent default types
            })
        rest_quants = quants - q
        return rest_quants.action_create_checklist()
