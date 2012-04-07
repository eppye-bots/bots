from django import template
from bots import botsglobal

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

# Use customised botslogo html file if configured in bots.ini
@register.filter
def botslogo_html(default_html):
    return botsglobal.ini.get('webserver','botslogo',default_html)

# Customised text next to botslogo
@register.filter
def environment_text(default_text):
    return botsglobal.ini.get('webserver','environment_text',default_text)
