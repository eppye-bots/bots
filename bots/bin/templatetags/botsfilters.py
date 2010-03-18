from django import template

register = template.Library()

@register.filter
def convert(value,conversiondict):
    statust = {0: 'Open',1: 'Error',2: 'OK',3: 'Done',4:'Retransmit'}
    status ={
            1:'process',
            200:'FileRecieve',
            210:'RawInfile',
            215:'Mimein',
            220:'Infile',
            280:'Mailbag',
            290:'Mailbagparsed',
            300:'Translate',
            310:'Parsed',
            320:'Splitup',
            330:'Translated',
            400:'Merged',
            500:'Outfile',
            510:'RawOutfile',
            520:'FileSend',
            }

    return locals()[conversiondict][value]

