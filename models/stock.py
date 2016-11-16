from openerp import api, fields, models


class stock_quant(models.Model):
    _name = 'stock.quant'
    _inherit = ['stock.quant', 'mail.thread']
    _order = 'in_date desc, id desc'

    def _is_kit_quant(self):
        for x in self:
            x.is_kit_quant = x == x.package_id.quant

    def _is_kit_accessory(self):
        for x in self:
            x.is_kit_accessory = x.package_id.quant and x != x.package_id.quant

    is_kit_quant = fields.Boolean(compute=_is_kit_quant)
    is_kit_accessory = fields.Boolean(compute=_is_kit_accessory)

    @api.multi
    def action_create_checklist(self):
        if not self:
            return True
        ctx = {'context': dict(self.env.context, active_ids=self.ids, active_id=self.ids[0], active_model=self._name)}
        return self._read_act_window('checklist.action_workshop_quants', act_update=ctx)

# todo: TMP DISABLED
