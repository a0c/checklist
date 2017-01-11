from openerp import api, fields, models


class create_checklist_template(models.TransientModel):
    _name = 'create.checklist.template'

    name = fields.Char('Template Name', required=1)
    partner = fields.Many2one('res.partner', 'Customer')

    @api.multi
    def create_checklist_template(self):
        project = self.env['project.project'].create({'name': self.name, 'partner_id': self.partner.id,
                                                      'state': 'template', 'user_id': False, 'type_ids': [(6, 0, [])]})
        template_tasks = self.env['project.task'].browse(self.env.context.get('active_ids'))
        project.add_tasks(template_tasks)

        if self.env.context.get('open_checklist_template'):
            return self._read_act_window('checklist.open_view_workshop_jobs_all', act_update={
                'name': 'Checklist Template',
                'res_id': project.id,
                'views': [(self.env.ref('checklist.edit_project').id, 'form')],
            })
