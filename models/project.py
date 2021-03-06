from datetime import datetime
import logging

from openerp import api, fields, models
from openerp.osv import fields as fields_old
from openerp.tools.safe_eval import safe_eval as eval

from openerp.addons.checklist.models.utils import prs, fmt, diff

_logger = logging.getLogger(__name__)


def not_checklist(vals):
    return not (vals.get('quant') or vals.get('rh_job_number'))


def hours_from_string(time_string):
    parts = time_string.split(':')
    hours = parts[0] if len(parts) > 0 else 0.0
    mins = parts[1] if len(parts) > 1 else 0.0
    secs = parts[2] if len(parts) > 2 else 0.0
    return float(hours) + float(mins) / 60.0 + float(secs) / 3600.0


class project(models.Model):
    _inherit = 'project.project'

    quant = fields.Many2one('stock.quant', readonly=1)
    rh_job_number = fields.Integer('RH Job Number', readonly=1)
    rh_job_date = fields.Date('RH Job Date', readonly=1)
    contact = fields.Many2one('res.partner')
    products = fields.Many2many('product.product', 'project_product_rel', 'project_id', 'product_id', 'Models')
    template = fields.Many2one('project.project', 'Use Checklist', domain=[('state', '=', 'template')])
    template_members = fields.Many2many('res.users', compute='_template_members')
    dest_project = fields.Many2one('project.project', compute='_dest_project')
    task_count_all = fields.Integer(compute='_task_count_all')
    help_msg = fields.Text(compute='_help_msg')
    state = fields.Selection(selection_add=[('completed', 'Completed')])
    signee = fields.Char()
    signature = fields.Binary()

    def _template_members(self):
        for x in self:
            group = x.quant and 'group_checklist_workshop_user' or x.rh_job_number and 'group_checklist_mobile_user'
            if group:
                x.template_members = self.env.ref('checklist.' + group).users

    def _dest_project(self):
        for x in self:
            x.dest_project = x.template or x

    def _task_count_all(self):
        for x in self:
            x.task_count_all = len(x.tasks)

    def _help_msg(self):
        for x in self:
            if not (x.state == 'draft' and x.quant):
                continue
            if x.task_count_all == 0:
                if not x.user_id:
                    x.help_msg = 'Set Checklist (Use Checklist) and Assigned To to automatically start the Job (New => In Progress).'
                else:
                    x.help_msg = 'Set Checklist (Use Checklist) to automatically start the Job (New => In Progress).'
            else:
                if not x.user_id:
                    x.help_msg = 'Set Assigned To to automatically start the Job (New => In Progress).'

    @api.model
    def create(self, vals):
        self = self._ctx_workshop(vals)
        res = super(project, self).create(vals)
        res._update_checklists(vals)
        return res

    def _ctx_workshop(self, vals):
        if not_checklist(vals) and not self.checklists():
            return self
        return self.with_context(active_test=False, tracking_disable=True)

    @api.multi
    def checklists(self):
        return self.filtered(lambda x: x.quant or x.rh_job_number)

    def _update_checklists(self, vals):
        """ must be called after super().write()/create(), because we read user_id/template here """
        if self.env.context.get('is_updating_checklists'):
            return
        is_new_template_being_written = vals.get('template')
        is_new_user_being_written = vals.get('user_id')
        for x in self.checklists().with_context(is_updating_checklists=True):
            v = {}
            if is_new_template_being_written:
                x.copy_template_vals(v)
                x.copy_template_tasks()
                # confirm checklist on user assign
            if x.state == 'draft' and x.user_id and x.template:
                v['state'] = 'open'
            if is_new_user_being_written:
                v['tasks'] = [(1, t.id, {'user_id': x.user_id.id}) for t in x.tasks]
            if v:
                super(project, x).write(v)

    @api.multi
    def copy_template_vals(self, vals):
        template = self.template
        vals.update({
            'name': '%s %s' % (template.name or '', self.quant and '#%s' % self.quant.id or self.rh_job_number),
            'parent_id': template.parent_id.id,
            'planned_hours': template.planned_hours,
            'color': template.color,
        })

    @api.multi
    def copy_template_tasks(self):
        self.map_tasks(self.template.id, self.id)
        self.tasks.write({'reviewer_id': self._uid})

    @api.multi
    def write(self, vals):
        self = self._ctx_workshop(vals)
        res = super(project, self).write(vals)
        self._update_checklists(vals)
        return res

    @api.multi
    def unlink(self):
        for x in self.with_context(active_test=False):
            if not x.tasks.filtered(lambda t: t.stage_id.sequence):
                x.tasks.unlink()
        return super(project, self).unlink()

    @api.multi
    def action_tasks_as_list(self):
        act = self.env.ref(self.env.context.get('tasks_as_list') and
                           'checklist.action_view_workshop_job_tasks' or
                           'project.act_project_project_2_project_task_all')
        ctx = eval(act.context, {'active_id': self.id})
        ctx.update(self.env.context)
        if 'form_view_ref' in ctx:
            del ctx['form_view_ref']
        return {
            'name': 'Tasks',
            'type': 'ir.actions.act_window',
            'res_model': act.res_model,
            'view_type': act.view_type,
            'view_mode': act.view_mode,
            'views': act.views,
            'target': 'current',
            'context': ctx,
        }

    @api.multi
    def action_assign_user(self):
        assignee = self.env.context.get('assignee_id')
        if assignee:
            self.write({'user_id': assignee})

    @api.multi
    def action_complete(self):
        self.write({'state': 'completed', 'date': fmt(datetime.now())})

    def resequence_from_0(self):
        for x in self:
            tasks = x.tasks.sorted(lambda x: x.sequence)
            for seq, task in enumerate(tasks):
                task.sequence = seq

    @api.multi
    def action_add_tasks(self):
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'add.tasks.to.checklist.template',
            'name': 'Add Tasks to Checklist Template',
            'target': 'new',
            'context': {'default_project': self.id}
        }

    @api.multi
    def add_tasks(self, tasks):
        for x in self.with_context(active_test=0, tracking_disable=1):
            old_tasks = x.tasks.sorted(lambda x: x.sequence)
            start = old_tasks and old_tasks[-1].sequence + 1 or 0
            for seq, task in enumerate(tasks, start=start):
                task.copy({'project_id': x.id, 'sequence': seq, 'name': task.name, 'stage_id': task.stage_id.id})


class task(models.Model):
    _inherit = 'project.task'

    show_button_start = fields.Boolean(compute='_show_buttons')
    show_button_done = fields.Boolean(compute='_show_buttons')
    show_button_skip = fields.Boolean(compute='_show_buttons')
    next_task = fields.Many2one('project.task', compute='_next_task')
    extra_hours = fields.Char('Extra Hours', compute='_get_extra_hours', inverse='_set_extra_hours')
    is_extra = fields.Boolean(compute='_is_extra')

    def _is_template(self, cr, uid, ids, field_name, arg, context=None):
        """ take default_active from context """
        res = {}
        default_active = (context or {}).get('default_active', True)
        for task in self.browse(cr, uid, ids, context=context):
            res[task.id] = default_active
            if task.project_id:
                if task.project_id.active == False or task.project_id.state == 'template':
                    res[task.id] = False
        return res

    _columns = {
        'active': fields_old.function(_is_template, store=True, string='Not a Template Task', type='boolean', help="This field is computed automatically and have the same behavior than the boolean 'active' field: if the task is linked to a template or unactivated project, it will be hidden unless specifically asked."),
    }

    @api.model
    def _get_checklist_stages(self):
        return [
            self.env.ref('project.project_tt_deployment'),
            self.env.ref('checklist.project_tt_started'),
            self.env.ref('checklist.project_tt_unstarted'),
            self.env.ref('checklist.project_tt_skipped'),
        ]

    def _show_buttons(self):
        done, started, unstarted, skipped = self._get_checklist_stages()
        for x in self:
            # hide buttons on predefined/template tasks
            if not x.active:
                continue
            x.show_button_start = x.sequence == 0 and x.stage_id == unstarted or x.stage_id == started and x.work_ids and x.work_ids[0].hours
            x.show_button_done = x.stage_id == started and x.work_ids and not x.work_ids[0].hours
            x.show_button_skip = x.stage_id != skipped and (x.show_button_start or x.show_button_done)

    def _next_task(self):
        for x in self:
            x.next_task = next((t for t in x.project_id.tasks if t.sequence > x.sequence), False)

    def _get_extra_hours(self):
        for x in self:
            x.extra_hours = x.work_ids and x.work_ids[-1].hours or ''

    def _set_extra_hours(self):
        for x in self:
            if not (x.extra_hours and x.is_extra): continue
            try:
                extra_hours = hours_from_string(x.extra_hours)
            except:
                _logger.warn("Could not parse extra_hours '%s'" % x.extra_hours)
                continue
            if x.work_ids:
                x.work_ids[-1].hours = extra_hours
            else:
                x.work_ids = [(0, 0, {'name': 'EXTRA', 'hours': extra_hours})]

    def _is_extra(self):
        for x in self:
            x.is_extra = x.create_date > x.project_id.create_date

    @api.model
    def stage_find(self, cases, section_id, domain=[], order='sequence'):
        """ default stage computation: use Unstarted for predefined tasks, otherwise refer to template's stages """
        if not self.env.context.get('default_active', True):
            return self.env.ref('checklist.project_tt_unstarted').id
        if section_id:
            section_id = self.env['project.project'].browse(section_id).dest_project.id
        return super(task, self).stage_find(cases, section_id, domain=domain, order=order)

    def start_task(self, started=None):
        # todo: TMP DISABLED
        # self._move_quant_to_workshop()
        vals = {'work_ids': [(0, 0, {})]}
        started = started or self._get_checklist_stages()[1]
        if self.stage_id != started:
            vals['stage_id'] = started.id
        if self.user_id != self.env.user:
            vals['user_id'] = self.env.uid
        self.write(vals)

    @api.multi
    def action_start(self):
        for x in self:
            x.start_task()

    @api.multi
    def action_pause(self):
        end = datetime.now()
        for x in self.filtered(lambda x: x.work_ids and x.work_ids[0].date):
            start = prs(x.work_ids[0].date)
            x.work_ids[0].hours = diff(start, end).total_seconds() / 3600

    @api.multi
    def action_skip(self):
        skipped = self.env.ref('checklist.project_tt_skipped')
        self.with_context(stage=skipped.id).action_done()
        self.mapped('work_ids').unlink()

    @api.multi
    def action_done(self):
        done, started, _, _ = self._get_checklist_stages()
        vals = {'stage_id': self._context.get('stage', done.id)}
        if self._context.get('notes') is not None:
            vals['notes'] = self._context['notes']
        for x in self:
            vals['date_end'] = fmt(datetime.now())
            x.action_pause()
            x.write(vals)
            if x.next_task:
                x.next_task.start_task(started)
            # todo: TMP DISABLED
            # else:
                # x.project_id.action_complete()
                # x._move_quant_to_runup()
        return True

    def _move_quant_to_workshop(self):
        if self.sequence:
            return
        quant = self.project_id.quant
        location = quant.location_id
        if location != location.warehouse.wh_work_loc_id:
            quant.move_to(location.warehouse.wh_work_loc_id)

    def _move_quant_to_runup(self):
        quant = self.project_id.quant.with_context(checklist_done=True)
        quant.move_to(quant.location_id.warehouse.wh_runup_loc_id)

    @api.multi
    def unlink(self):
        projects = self.mapped('project_id')
        res = super(task, self).unlink()
        projects.resequence_from_0()
        return res


class project_task_type(models.Model):
    _inherit = 'project.task.type'

    def _add_checklist_stages_to(self, args):
        args_new = []
        for arg in args:
            if arg[:2] == ['project_ids', '=']:
                project = self.env['project.project'].browse(arg[2])
                # if checklist/template: add checklist stages
                if project.quant or project.state == 'template':
                    checklist_stages = [stage.id for stage in self.env['project.task']._get_checklist_stages()]
                    args_new.append('|')
                    args_new.append(arg)
                    args_new.append(['id', 'in', checklist_stages])
                else:
                    args_new.append(arg)
            else:
                args_new.append(arg)
        return args_new

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        args = self._add_checklist_stages_to(args)
        return super(project_task_type, self).search(args, offset=offset, limit=limit, order=order, count=count)
