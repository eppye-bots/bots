import django
import models
import viewlib
django.contrib.admin.widgets.AdminSplitDateTime
HiddenInput = django.forms.widgets.HiddenInput
DEFAULT_ENTRY = ('',"---------")
editypelist=[DEFAULT_ENTRY] + sorted(models.EDITYPES)
confirmtypelist=[DEFAULT_ENTRY] + models.CONFIRMTYPE

def getroutelist():     #needed because the routeid is needed (and this is not theprimary key
    return [DEFAULT_ENTRY]+[(l,l) for l in models.routes.objects.values_list('idroute', flat=True).order_by('idroute').distinct() ]
def getinmessagetypes():
    return [DEFAULT_ENTRY]+[(l,l) for l in models.translate.objects.values_list('frommessagetype', flat=True).order_by('frommessagetype').distinct() ]
def getoutmessagetypes():
    return [DEFAULT_ENTRY]+[(l,l) for l in models.translate.objects.values_list('tomessagetype', flat=True).order_by('tomessagetype').distinct() ]
def getallmessagetypes():
    return [DEFAULT_ENTRY]+[(l,l) for l in sorted(set(list(models.translate.objects.values_list('tomessagetype', flat=True).all()) + list(models.translate.objects.values_list('frommessagetype', flat=True).all()) )) ]
def getpartners():
    return [DEFAULT_ENTRY]+[(l,l) for l in models.partner.objects.values_list('idpartner', flat=True).filter(isgroup=False,active=True).order_by('idpartner') ]
def getfromchannels():
    return [DEFAULT_ENTRY]+[(l,l) for l in models.channel.objects.values_list('idchannel', flat=True).filter(inorout='in').order_by('idchannel') ]
def gettochannels():
    return [DEFAULT_ENTRY]+[(l,l) for l in models.channel.objects.values_list('idchannel', flat=True).filter(inorout='out').order_by('idchannel') ]


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
    frompartner = django.forms.ChoiceField([],required=False)
    topartner = django.forms.ChoiceField([],required=False)
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
        self.fields['frompartner'].choices = getpartners()
        self.fields['topartner'].choices = getpartners()

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
    frompartner = django.forms.ChoiceField([],required=False)
    topartner = django.forms.ChoiceField([],required=False)
    editype = django.forms.ChoiceField(editypelist,required=False)
    messagetype = django.forms.ChoiceField(required=False)
    lastrun = django.forms.BooleanField(required=False,initial=False)
    botskey = django.forms.CharField(required=False,label='Document number',max_length=35)
    def __init__(self, *args, **kwargs):
        super(SelectDocument, self).__init__(*args, **kwargs)
        self.fields['idroute'].choices = getroutelist()
        self.fields['messagetype'].choices = getoutmessagetypes()
        self.fields['frompartner'].choices = getpartners()
        self.fields['topartner'].choices = getpartners()

class ViewDocument(View):
    template = 'bots/document.html'
    action = '/document/'
    idroute = django.forms.CharField(required=False,widget=HiddenInput())
    frompartner = django.forms.CharField(required=False,widget=HiddenInput())
    topartner = django.forms.CharField(required=False,widget=HiddenInput())
    editype = django.forms.CharField(required=False,widget=HiddenInput())
    messagetype = django.forms.CharField(required=False,widget=HiddenInput())
    lastrun = django.forms.BooleanField(required=False,initial=False,widget=HiddenInput())
    botskey = django.forms.CharField(required=False,widget=HiddenInput())

class SelectOutgoing(Select):
    template = 'bots/selectform.html'
    action = '/outgoing/'
    idroute = django.forms.ChoiceField([],required=False,initial='')
    frompartner = django.forms.ChoiceField([],required=False)
    topartner = django.forms.ChoiceField([],required=False)
    editype = django.forms.ChoiceField(editypelist,required=False)
    messagetype = django.forms.ChoiceField(required=False)
    lastrun = django.forms.BooleanField(required=False,initial=False)
    def __init__(self, *args, **kwargs):
        super(SelectOutgoing, self).__init__(*args, **kwargs)
        self.fields['idroute'].choices = getroutelist()
        self.fields['messagetype'].choices = getoutmessagetypes()
        self.fields['frompartner'].choices = getpartners()
        self.fields['topartner'].choices = getpartners()

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
    frompartner = django.forms.ChoiceField([],required=False)
    topartner = django.forms.ChoiceField([],required=False)
    fromchannel = django.forms.ChoiceField([],required=False)
    tochannel = django.forms.ChoiceField([],required=False)
    def __init__(self, *args, **kwargs):
        super(SelectConfirm, self).__init__(*args, **kwargs)
        self.fields['idroute'].choices = getroutelist()
        self.fields['messagetype'].choices = getallmessagetypes()
        self.fields['frompartner'].choices = getpartners()
        self.fields['topartner'].choices = getpartners()
        self.fields['fromchannel'].choices = getfromchannels()
        self.fields['tochannel'].choices = gettochannels()

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

