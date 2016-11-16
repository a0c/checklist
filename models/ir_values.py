from openerp import api, models


class ir_values(models.Model):
    _inherit = 'ir.values'

    def _drop_task_actions(self, action_slot, model, res):
        if model == 'project.task' and action_slot == 'client_action_multi':
            ok_to_create = not self.env.context.get('default_active', True) and \
                           self.env.context.get('form_view_ref') == 'checklist.view_task_form2_create_template'
            res = [r for r in res if r[1] != 'action_task_edit' and (r[1] != 'action_create_checklist_template' or ok_to_create)]
        return res

    @api.model
    def get_actions(self, action_slot, model, res_id=False):
        res = super(ir_values, self).get_actions(action_slot, model, res_id=res_id)
        res = self._drop_task_actions(action_slot, model, res)
        return res
