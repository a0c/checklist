# -*- coding: utf-8 -*-
{
    'name': 'Checklists TMP',
    'version': '0.1',
    'category': 'Warehouse',
    'summary': 'Checklists TMP',
    'description': """
Checklists TMP
==============
""",
    'depends': [
        'base', 'stock', 'project'
    ],
    'data': [
        'security/security.xml',
        'data/project_data.xml',
        'static/src/xml/checklist_backend.xml',
        'views/res_users.xml',
        'views/project.xml',
        'wizard/workshop_quants.xml',
        'wizard/task_edit.xml',
        'wizard/create_checklist_template.xml',
    ],
    'qweb': [
    ],
}
