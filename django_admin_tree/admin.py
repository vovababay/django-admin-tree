from functools import update_wrapper
from django.contrib.admin.utils import unquote
from django.core.exceptions import (
    FieldDoesNotExist,
    FieldError,
    PermissionDenied,
    ValidationError,
)
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.text import capfirst
from django.utils.translation import gettext as _


def get_content_type_for_model(obj):
    from django.contrib.contenttypes.models import ContentType
    return ContentType.objects.get_for_model(obj, for_concrete_model=False)


class TreeParentAdminMixin:
    change_form_template = 'admin/django_admin_tree/change_form.html'

    def get_urls(self):
        from django.urls import path
        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)

            wrapper.model_admin = self
            return update_wrapper(wrapper, view)

        info = self.opts.app_label, self.opts.model_name
        return [
            path(
                "<path:object_id>/tree/",
                wrap(self.tree_view),
                name="%s_%s_tree" % info,
            ),
            *super().get_urls(),
        ]

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        print(form)
        parent_id = request.GET.get("parent_id")
        if parent_id and len(parent_id) > 0:
            form.base_fields['parent'].initial = 10043
        return form

    def tree_view(self, request, object_id, extra_context=None):

        model = self.model
        obj = self.get_object(request, unquote(object_id))
        if obj is None:
            return self._get_obj_does_not_exist_redirect(
                request, model._meta, object_id
            )

        if not self.has_view_or_change_permission(request, obj):
            raise PermissionDenied
        # rows = obj.check_cycle()
        # for i in rows:
        #     print(i)
        # print(rows.query)
        # if rows:
        #     descendants = obj.get_descendants(max_depth=1)
        # else:
        descendants = obj.get_descendants(max_depth=self.max_tree_depth)
        add_url = reverse('admin:{}_{}_add'.format(self.opts.app_label, self.opts.model_name))

        path_to_create_child = {
            descendant.id: mark_safe('<span onclick="event.stopPropagation(); showRelatedObjectPopup({'
                  f"href: '{add_url}?_popup=1&parent_id={descendant.id}', id: 'change_id_author'"
                  f'}})">Open</span>')  for descendant in descendants
        }
        # path_to_create_child.update({obj.id: change_url})
        context = {
            **self.admin_site.each_context(request),
            "title": _("Tree object: %s") % obj,
            "module_name": str(capfirst(self.opts.verbose_name_plural)),
            "object": obj,
            "opts": self.opts,
            "add_url": add_url,
            "path_to_create_child": path_to_create_child,
            'obj': obj,
            'descendants': descendants,
            **(extra_context or {}),
        }
        request.current_app = self.admin_site.name
        return TemplateResponse(
            request,
            'admin/django_admin_tree/category_tree.html',
            context,
        )

    @property
    def urls(self):
        return self.get_urls()

