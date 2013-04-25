import os
from django import template
#~ from bots import botsglobal

register = template.Library()

# Sets the minimum selectable date in datetimepicker widget
@register.filter
def shortpath(path):
    if len(path) <= 25:
        return path
    elif os.path.isabs(path):
        return path[:1] + u'\u2026' + path[-23:]
    else:
        return path[:6] + u'\u2026' + path[-18:]
