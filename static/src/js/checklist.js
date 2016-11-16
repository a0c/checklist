openerp.checklist = function (instance) {
    instance.web_kanban.KanbanGroup.include({
        compute_cards_auto_height: function() {
            if (!this.view.group_by) {
                this._super();
            } else {
                // each card with its own height
                _.each(this.records, function(r) {
                    var $e = r.$el.children(':first:not(.oe_kanban_no_auto_height)').css('min-height', 0);
                    if ($e.length) {
                        $e.css('min-height', Math.max(0, $e.outerHeight()));
                    }
                });
            }
        },
    });
    openerp.web_kanban.KanbanView.include({
        project_display_members_names: function() {
            /*
             * Set members' names in list of Assign To button.
             * In kanban views, many2many fields only return a list of ids.
             * We can implement return value of m2m fields like [(1,"Administrator"),...].
             */
            var self = this;
            self._super.apply(self, arguments);

            var members_ids = [];
            // Collect members ids
            self.$el.find('a[data-member_id]').each(function() {
                members_ids.push($(this).data('member_id'));
            });
            // Find their matching names
            var dataset = new openerp.web.DataSetSearch(self, 'res.users', self.session.context, [['id', 'in', _.uniq(members_ids)]]);
            dataset.read_slice(['id', 'name']).done(function(result) {
                _.each(result, function(v, k) {
                    // Set the proper value in the DOM
                    self.$el.find('a[data-member_id=' + v.id + '] span').html(v.name);
                });
            });
        },
    });
    instance.web_kanban.KanbanRecord.include({
        do_action_object: function ($action) {
            var button_attrs = $action.data();
            var reload_page = button_attrs.reload_on_button;
            this.view.do_execute_action(button_attrs, this.view.dataset, this.id, reload_page ? this.view.do_reload : this.do_reload_w_member_names);
        },
        // copy/override of do_reload() that also calls project_display_members_names()
        do_reload_w_member_names: function() {
            var self = this;
            this.view.dataset.read_ids([this.id], this.view.fields_keys.concat(['__last_update'])).done(function(records) {
                _.each(self.sub_widgets, function(el) {
                    el.destroy();
                });
                self.sub_widgets = [];
                if (records.length) {
                    self.set_record(records[0]);
                    self.renderElement();
                    self.init_content();
                    self.group.compute_cards_auto_height();
                    self.view.postprocess_m2m_tags();
                    if (self.view.dataset.model === 'project.project') {
                        self.view.project_display_members_names();
                    }
                } else {
                    self.destroy();
                }
            });
        },
    });
};
