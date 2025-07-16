from django import template

register = template.Library()

@register.filter
def get_field_label(form_fields, field_name):
    try:
        return form_fields[field_name].label
    except KeyError:
        return ""