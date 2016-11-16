from openerp import fields, models


class res_users(models.Model):
    _inherit = 'res.users'

    group_reload_checklists_on_assigning = fields.Boolean('Reload Checklists on Assigning',
                                                          compute='_get_group_reload_checklists_on_assigning',
                                                          inverse='_set_group_reload_checklists_on_assigning',
                                                          groups='project.group_project_manager')

    def _get_group_reload_checklists_on_assigning(self):
        for x in self:
            x.group_reload_checklists_on_assigning = x.has_group('checklist.group_reload_checklists_on_assigning')

    def _set_group_reload_checklists_on_assigning(self):
        group_reload = self.env.ref('checklist.group_reload_checklists_on_assigning')
        for x in self:
            x.groups_id = [(x.group_reload_checklists_on_assigning and 4 or 3, group_reload.id)]

    def __init__(self, pool, cr):
        """ Override of __init__ to add access rights on group_reload_checklists_on_assigning field. Access rights
        are disabled by default, but allowed on some specific fields defined in self.SELF_{READ/WRITE}ABLE_FIELDS.
        """
        init_res = super(res_users, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        self.SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        self.SELF_WRITEABLE_FIELDS.append('group_reload_checklists_on_assigning')
        # duplicate list to avoid modifying the original reference
        self.SELF_READABLE_FIELDS = list(self.SELF_READABLE_FIELDS)
        self.SELF_READABLE_FIELDS.append('group_reload_checklists_on_assigning')
        return init_res
