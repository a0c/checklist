import logging

from openerp import api, models

logger = logging.getLogger('[MIGRATION]')


def log(records, msg):
    if records:
        logger.info(msg % (len(records), records.ids))


class migration(models.TransientModel):
    _name = 'checklist.migration'

    @api.model
    def migrate(self):
        self.remove_duplicate_done_task_state()

    def remove_duplicate_done_task_state(self):
        state = self.env.ref('project.project_tt_deployment')
        duplicate_state = self.env.ref('checklist.project_tt_done', raise_if_not_found=False)
        if not duplicate_state:
            return
        todo_tasks = self.env['project.task'].search([('stage_id', '=', duplicate_state.id)])
        todo_tasks.write({'stage_id': state.id})
        log(todo_tasks, '%sx Tasks %s updated: stage => [Project] Done')
        # allow deleting duplicate state on module update
        xmlid = self.env['ir.model.data'].search([('module', '=', 'checklist'), ('name', '=', 'project_tt_done')])
        xmlid.noupdate = False
