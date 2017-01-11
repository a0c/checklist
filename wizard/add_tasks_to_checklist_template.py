from openerp import api, models, fields


class add_tasks_to_checklist_template(models.TransientModel):
    _name = 'add.tasks.to.checklist.template'

    project = fields.Many2one('project.project', readonly=1)
    tasks = fields.Many2many('project.task', domain=[('active', '=', False), ('project_id', '=', False)])

    @api.multi
    def add_tasks(self):
        if not self.project:
            raise api.Warning('Project not specified')
        self.project.add_tasks(self.tasks)
