from django import template

register = template.Library()

@register.filter
def convert(value,conversiondict):
    statust = {0: 'Open',1: 'Error',2: 'OK',3: 'Done',4:'Retransmit'}
    status ={
            1:'process',
            200:'FileRecieve',
            }
    return locals()[conversiondict][value]

@register.filter
def url2path(value):
    print 'title was>>>>',value
    if value.startswith('/admin/bots/'):
        value = value[12:]
    else:
        value = value[1:]
    if value:
        if value[-1] == '/':
            value = value[:-1]
    else:
        value = 'home'
    print 'title is>>>>',value
    return value

