import os
from django import template

register = template.Library()

@register.filter
def shortpath(path):
    return os.path.basename(path)   #use triple point (u'\u2026') to indicate soemthing?
