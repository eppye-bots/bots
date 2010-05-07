from django import template

register = template.Library()

@register.filter
def url2path(value):
    if value.startswith('/admin/bots/'):
        value = value[12:]
    else:
        value = value[1:]
    if value:
        if value[-1] == '/':
            value = value[:-1]
    else:
        value = 'home'
    return value

