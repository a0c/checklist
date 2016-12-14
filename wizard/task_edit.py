from openerp import api, fields, models


class task_edit(models.TransientModel):
    _name = 'task.edit'

    description = fields.Text(default=lambda self: self.get_task().notes)

    def get_task(self):
        return self.env['project.task'].browse(self.env.context['active_ids'])[0]

    @api.multi
    def do_save(self):
        self.get_task().notes = self.description
