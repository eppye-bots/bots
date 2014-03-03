import os
from django import template

register = template.Library()

@register.filter
def shortpath(path):
    terug = os.path.basename(path)
    if terug:
        return terug
    else:
        return '(file)'     #for soem cases there is no good filename.....
