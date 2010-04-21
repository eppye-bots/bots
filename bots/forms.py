import django
import models
import viewlib
django.contrib.admin.widgets.AdminSplitDateTime
HiddenInput = django.forms.widgets.HiddenInput
DEFAULT_ENTRY = ('',"---------")
editypelist=[DEFAULT_ENTRY] + models.EDITYPES
confirmtypelist=[DEFAULT_ENTRY] + models.CONFIRMTYPE

#~ class whichrun(django.forms.ChoiceField):
    #~ def clean(self, value):
        #~ if value == '0':
            #~ return 0
        #~ elif value == '1':
            #~ return sys.maxint   #last run


def getroutelist():     #needed because the routeid is needed (and this is not theprimary key
    return [DEFAULT_ENTRY]+[(l,l) for l in sorted(set(models.routes.objects.values_list('idroute', flat=True).all())) ]
def getinmessagetypes():
    return [DEFAULT_ENTRY]+[(l,l) for l in sorted(set(models.translate.objects.values_list('frommessagetype', flat=True).all())) ]
def getoutmessagetypes():
    return [DEFAULT_ENTRY]+[(l,l) for l in sorted(set(models.translate.objects.values_list('tomessagetype', flat=True).all())) ]
def getallmessagetypes():
    return [DEFAULT_ENTRY]+[(l,l) for l in sorted(set(list(models.translate.objects.values_list('tomessagetype', flat=True).all()) + list(models.translate.objects.values_list('frommessagetype', flat=True).all()) )) ]

class Select(django.forms.Form):
    datefrom = django.forms.DateTimeField(initial=viewlib.datetimefrom)
    dateuntil = django.forms.DateTimeField(initial=viewlib.datetimeuntil)
    page = django.forms.IntegerField(required=False,initial=1,widget=HiddenInput())
    sortedby = django.forms.CharField(initial='ts',widget=HiddenInput())
    sortedasc = django.forms.BooleanField(initial=False,required=False,widget=HiddenInput())

class View(django.forms.Form):
    datefrom = django.forms.DateTimeField(required=False,initial=viewlib.datetimefrom,widget=HiddenInput())
    dateuntil = django.forms.DateTimeField(required=False,initial=viewlib.datetimeuntil,widget=HiddenInput())
    page = django.forms.IntegerField(required=False,initial=1,widget=HiddenInput())
    sortedby = django.forms.CharField(required=False,initial='ts',widget=HiddenInput())
    sortedasc = django.forms.BooleanField(required=False,initial=False,widget=HiddenInput())

class SelectReports(Select):
    template = 'bots/selectform.html'
    action = '/reports/'
    status = django.forms.ChoiceField([DEFAULT_ENTRY,('1',"Error"),('0',"Done")],required=False,initial='')

class ViewReports(View):
    template = 'bots/reports.html'
    action = '/reports/'
    status = django.forms.IntegerField(required=False,initial='',widget=HiddenInput())
    
class SelectIncoming(Select):
    template = 'bots/selectform.html'
    action = '/incoming/'
    statust = django.forms.ChoiceField([DEFAULT_ENTRY,('1',"Error"),('3',"Done")],required=False,initial='')
    idroute = django.forms.ChoiceField([],required=False,initial='')
    frompartner = django.forms.ModelChoiceField(models.partner.objects.filter(isgroup=False).all(),required=False)
    topartner = django.forms.ModelChoiceField(models.partner.objects.filter(isgroup=False).all(),required=False)
    ineditype = django.forms.ChoiceField(editypelist,required=False)
    inmessagetype = django.forms.ChoiceField([],required=False)
    outeditype = django.forms.ChoiceField(editypelist,required=False)
    outmessagetype = django.forms.ChoiceField([],required=False)
    lastrun = django.forms.BooleanField(required=False,initial=False)
    def __init__(self, *args, **kwargs):
        super(SelectIncoming, self).__init__(*args, **kwargs)
        self.fields['idroute'].choices = getroutelist()
        self.fields['inmessagetype'].choices = getinmessagetypes()
        self.fields['outmessagetype'].choices = getoutmessagetypes()

class ViewIncoming(View):
    template = 'bots/incoming.html'
    action = '/incoming/'
    statust = django.forms.IntegerField(required=False,initial='',widget=HiddenInput())
    idroute = django.forms.CharField(required=False,widget=HiddenInput())
    frompartner = django.forms.CharField(required=False,widget=HiddenInput())
    topartner = django.forms.CharField(required=False,widget=HiddenInput())
    ineditype = django.forms.CharField(required=False,widget=HiddenInput())
    inmessagetype = django.forms.CharField(required=False,widget=HiddenInput())
    outeditype = django.forms.CharField(required=False,widget=HiddenInput())
    outmessagetype = django.forms.CharField(required=False,widget=HiddenInput())
    lastrun = django.forms.BooleanField(required=False,initial=False,widget=HiddenInput())
    botskey = django.forms.CharField(required=False,widget=HiddenInput())

class SelectDocument(Select):
    template = 'bots/selectform.html'
    action = '/document/'
    idroute = django.forms.ChoiceField([],required=False,initial='')
    frompartner = django.forms.ModelChoiceField(models.partner.objects.filter(isgroup=False).all(),required=False)
    topartner = django.forms.ModelChoiceField(models.partner.objects.filter(isgroup=False).all(),required=False)
    editype = django.forms.ChoiceField(editypelist,required=False)
    messagetype = django.forms.ChoiceField(required=False)
    lastrun = django.forms.BooleanField(required=False,initial=False)
    botskey = django.forms.CharField(required=False,label='Document number',max_length=35)
    def __init__(self, *args, **kwargs):
        super(SelectDocument, self).__init__(*args, **kwargs)
        self.fields['idroute'].choices = getroutelist()
        self.fields['messagetype'].choices = getoutmessagetypes()

class ViewDocument(View):
    template = 'bots/document.html'
    action = '/document/'
    idroute = django.forms.CharField(required=False,widget=HiddenInput())
    frompartner = django.forms.CharField(required=False,widget=HiddenInput())
    topartner = django.forms.CharField(required=False,widget=HiddenInput())
    editype = django.forms.CharField(required=False,widget=HiddenInput())
    messagetype = django.forms.CharField(required=False,widget=HiddenInput())
    lastrun = django.forms.BooleanField(required=False,initial=False,widget=HiddenInput())

class SelectOutgoing(Select):
    template = 'bots/selectform.html'
    action = '/outgoing/'
    idroute = django.forms.ChoiceField([],required=False,initial='')
    frompartner = django.forms.ModelChoiceField(models.partner.objects.filter(isgroup=False).all(),required=False)
    topartner = django.forms.ModelChoiceField(models.partner.objects.filter(isgroup=False).all(),required=False)
    editype = django.forms.ChoiceField(editypelist,required=False)
    messagetype = django.forms.ChoiceField(required=False)
    lastrun = django.forms.BooleanField(required=False,initial=False)
    def __init__(self, *args, **kwargs):
        super(SelectOutgoing, self).__init__(*args, **kwargs)
        self.fields['idroute'].choices = getroutelist()
        self.fields['messagetype'].choices = getoutmessagetypes()

class ViewOutgoing(View):
    template = 'bots/outgoing.html'
    action = '/outgoing/'
    idroute = django.forms.CharField(required=False,widget=HiddenInput())
    frompartner = django.forms.CharField(required=False,widget=HiddenInput())
    topartner = django.forms.CharField(required=False,widget=HiddenInput())
    editype = django.forms.CharField(required=False,widget=HiddenInput())
    messagetype = django.forms.CharField(required=False,widget=HiddenInput())
    lastrun = django.forms.BooleanField(required=False,initial=False,widget=HiddenInput())

class SelectProcess(Select):
    template = 'bots/selectform.html'
    action = '/process/'
    idroute = django.forms.ChoiceField([],required=False,initial='')
    lastrun = django.forms.BooleanField(required=False,initial=False)
    def __init__(self, *args, **kwargs):
        super(SelectProcess, self).__init__(*args, **kwargs)
        self.fields['idroute'].choices = getroutelist()

class ViewProcess(View):
    template = 'bots/process.html'
    action = '/process/'
    idroute = django.forms.CharField(required=False,widget=HiddenInput())
    lastrun = django.forms.BooleanField(required=False,initial=False,widget=HiddenInput())

class SelectConfirm(Select):
    template = 'bots/selectform.html'
    action = '/confirm/'
    confirmtype = django.forms.ChoiceField(confirmtypelist,required=False,initial='0')
    confirmed = django.forms.ChoiceField([('0',"All runs"),('1',"Current run"),('2',"Last run")],required=False,initial='0')
    idroute = django.forms.ChoiceField([],required=False,initial='')
    editype = django.forms.ChoiceField(editypelist,required=False)
    messagetype = django.forms.ChoiceField([],required=False)
    frompartner = django.forms.ModelChoiceField(models.partner.objects.filter(isgroup=False).all(),required=False)
    topartner = django.forms.ModelChoiceField(models.partner.objects.filter(isgroup=False).all(),required=False)
    fromchannel = django.forms.ModelChoiceField(models.channel.objects.filter(inorout='in').all(),required=False)
    tochannel = django.forms.ModelChoiceField(models.channel.objects.filter(inorout='out').all(),required=False)
    def __init__(self, *args, **kwargs):
        super(SelectConfirm, self).__init__(*args, **kwargs)
        self.fields['idroute'].choices = getroutelist()
        self.fields['messagetype'].choices = getallmessagetypes()

class ViewConfirm(View):
    template = 'bots/confirm.html'
    action = '/confirm/'
    confirmtype = django.forms.CharField(required=False,widget=HiddenInput())
    confirmed = django.forms.CharField(required=False,widget=HiddenInput())
    idroute = django.forms.CharField(required=False,widget=HiddenInput())
    editype = django.forms.CharField(required=False,widget=HiddenInput())
    messagetype = django.forms.CharField(required=False,widget=HiddenInput())
    frompartner = django.forms.CharField(required=False,widget=HiddenInput())
    topartner = django.forms.CharField(required=False,widget=HiddenInput())
    fromchannel = django.forms.CharField(required=False,widget=HiddenInput())
    tochannel = django.forms.CharField(required=False,widget=HiddenInput())
    
class UploadFileForm(django.forms.Form):
    file  = django.forms.FileField(label='Plugin to read',required=True,widget=django.forms.widgets.FileInput(attrs={'size':'100'}))

