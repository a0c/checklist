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
        'base', 'stock', 'project', 'project_issue', 'document', 'base_external_dbsource'
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/project_data.xml',
        'static/src/xml/checklist_backend.xml',
        'views/res_users.xml',
        'views/project.xml',
        'views/partner.xml',
        'wizard/workshop_quants.xml',
        'wizard/task_edit.xml',
        'wizard/create_checklist_template.xml',
        'wizard/create_onsite_checklist.xml',
        'wizard/add_tasks_to_checklist_template.xml',
        'views/migration.xml',
    ],
    'qweb': [
    ],
}
