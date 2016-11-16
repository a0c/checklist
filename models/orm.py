from openerp.osv.orm import BaseModel
from openerp.tools.safe_eval import safe_eval as eval


def _read_act_window(self, act_xml_id, context_globals=None, act_update=None, res_id=False):
    act_fields = ['name', 'view_mode', 'view_id', 'view_type', 'res_model', 'type', 'target', 'context']
    act = self.env.ref(act_xml_id).read(act_fields)[0]
    act['context'] = eval(act['context'], context_globals)
    if act_update is not None:
        act.update(act_update)
    if res_id:
        act['res_id'] = res_id
    return act

BaseModel._read_act_window = _read_act_window
