#~ import time
import django
import models
import viewlib
#~ import botslib
#~ import botsglobal

#~ django.contrib.admin.widgets.AdminSplitDateTime
HIDDENINPUT = django.forms.widgets.HiddenInput
DEFAULT_ENTRY = ('',"---------")
EDITYPELIST = [DEFAULT_ENTRY] + sorted(models.EDITYPES)
CONFIRMTYPELIST = [DEFAULT_ENTRY] + models.CONFIRMTYPE

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
    page = django.forms.IntegerField(required=False,initial=1,widget=HIDDENINPUT())
    sortedby = django.forms.CharField(initial='ts',widget=HIDDENINPUT())
    sortedasc = django.forms.BooleanField(initial=False,required=False,widget=HIDDENINPUT())

class View(django.forms.Form):
    datefrom = django.forms.DateTimeField(required=False,initial=viewlib.datetimefrom,widget=HIDDENINPUT())
    dateuntil = django.forms.DateTimeField(required=False,initial=viewlib.datetimeuntil,widget=HIDDENINPUT())
    page = django.forms.IntegerField(required=False,initial=1,widget=HIDDENINPUT())
    sortedby = django.forms.CharField(required=False,initial='ts',widget=HIDDENINPUT())
    sortedasc = django.forms.BooleanField(required=False,initial=False,widget=HIDDENINPUT())

class SelectReports(Select):
    template = 'bots/selectform.html'
    action = '/reports/'
    status = django.forms.ChoiceField([DEFAULT_ENTRY,('1',"Error"),('0',"Done")],required=False,initial='')

class ViewReports(View):
    template = 'bots/reports.html'
    action = '/reports/'
    status = django.forms.IntegerField(required=False,initial='',widget=HIDDENINPUT())

class SelectIncoming(Select):
    template = 'bots/selectform.html'
    action = '/incoming/'
    statust = django.forms.ChoiceField([DEFAULT_ENTRY,('1',"Error"),('3',"Done")],required=False,initial='')
    idroute = django.forms.ChoiceField([],required=False,initial='')
    fromchannel = django.forms.ChoiceField([],required=False)
    frompartner = django.forms.ChoiceField([],required=False)
    topartner = django.forms.ChoiceField([],required=False)
    ineditype = django.forms.ChoiceField(EDITYPELIST,required=False)
    inmessagetype = django.forms.ChoiceField([],required=False)
    outeditype = django.forms.ChoiceField(EDITYPELIST,required=False)
    outmessagetype = django.forms.ChoiceField([],required=False)
    lastrun = django.forms.BooleanField(required=False,initial=False)
    def __init__(self, *args, **kwargs):
        super(SelectIncoming, self).__init__(*args, **kwargs)
        self.fields['idroute'].choices = getroutelist()
        self.fields['inmessagetype'].choices = getinmessagetypes()
        self.fields['outmessagetype'].choices = getoutmessagetypes()
        self.fields['frompartner'].choices = getpartners()
        self.fields['topartner'].choices = getpartners()
        self.fields['fromchannel'].choices = getfromchannels()

class ViewIncoming(View):
    template = 'bots/incoming.html'
    action = '/incoming/'
    statust = django.forms.IntegerField(required=False,initial='',widget=HIDDENINPUT())
    idroute = django.forms.CharField(required=False,widget=HIDDENINPUT())
    frompartner = django.forms.CharField(required=False,widget=HIDDENINPUT())
    topartner = django.forms.CharField(required=False,widget=HIDDENINPUT())
    ineditype = django.forms.CharField(required=False,widget=HIDDENINPUT())
    inmessagetype = django.forms.CharField(required=False,widget=HIDDENINPUT())
    outeditype = django.forms.CharField(required=False,widget=HIDDENINPUT())
    outmessagetype = django.forms.CharField(required=False,widget=HIDDENINPUT())
    lastrun = django.forms.BooleanField(required=False,initial=False,widget=HIDDENINPUT())
    botskey = django.forms.CharField(required=False,widget=HIDDENINPUT())
    fromchannel = django.forms.CharField(required=False,widget=HIDDENINPUT())

class SelectDocument(Select):
    template = 'bots/selectform.html'
    action = '/document/'
    idroute = django.forms.ChoiceField([],required=False,initial='')
    frompartner = django.forms.ChoiceField([],required=False)
    topartner = django.forms.ChoiceField([],required=False)
    editype = django.forms.ChoiceField(EDITYPELIST,required=False)
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
    idroute = django.forms.CharField(required=False,widget=HIDDENINPUT())
    frompartner = django.forms.CharField(required=False,widget=HIDDENINPUT())
    topartner = django.forms.CharField(required=False,widget=HIDDENINPUT())
    editype = django.forms.CharField(required=False,widget=HIDDENINPUT())
    messagetype = django.forms.CharField(required=False,widget=HIDDENINPUT())
    lastrun = django.forms.BooleanField(required=False,initial=False,widget=HIDDENINPUT())
    botskey = django.forms.CharField(required=False,widget=HIDDENINPUT())

class SelectOutgoing(Select):
    template = 'bots/selectform.html'
    action = '/outgoing/'
    statust = django.forms.ChoiceField([DEFAULT_ENTRY,('1',"Error"),('3',"Done"),('4',"Resend")],required=False,initial='')
    idroute = django.forms.ChoiceField([],required=False,initial='')
    tochannel = django.forms.ChoiceField([],required=False)
    frompartner = django.forms.ChoiceField([],required=False)
    topartner = django.forms.ChoiceField([],required=False)
    editype = django.forms.ChoiceField(EDITYPELIST,required=False)
    messagetype = django.forms.ChoiceField(required=False)
    lastrun = django.forms.BooleanField(required=False,initial=False)
    def __init__(self, *args, **kwargs):
        super(SelectOutgoing, self).__init__(*args, **kwargs)
        self.fields['idroute'].choices = getroutelist()
        self.fields['messagetype'].choices = getoutmessagetypes()
        self.fields['frompartner'].choices = getpartners()
        self.fields['topartner'].choices = getpartners()
        self.fields['tochannel'].choices = gettochannels()

class ViewOutgoing(View):
    template = 'bots/outgoing.html'
    action = '/outgoing/'
    statust = django.forms.IntegerField(required=False,initial='',widget=HIDDENINPUT())
    idroute = django.forms.CharField(required=False,widget=HIDDENINPUT())
    frompartner = django.forms.CharField(required=False,widget=HIDDENINPUT())
    topartner = django.forms.CharField(required=False,widget=HIDDENINPUT())
    editype = django.forms.CharField(required=False,widget=HIDDENINPUT())
    messagetype = django.forms.CharField(required=False,widget=HIDDENINPUT())
    lastrun = django.forms.BooleanField(required=False,initial=False,widget=HIDDENINPUT())
    tochannel = django.forms.CharField(required=False,widget=HIDDENINPUT())

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
    idroute = django.forms.CharField(required=False,widget=HIDDENINPUT())
    lastrun = django.forms.BooleanField(required=False,initial=False,widget=HIDDENINPUT())

class SelectConfirm(Select):
    template = 'bots/selectform.html'
    action = '/confirm/'
    confirmtype = django.forms.ChoiceField(CONFIRMTYPELIST,required=False,initial='0')
    confirmed = django.forms.ChoiceField([('0',"All runs"),('1',"Current run"),('2',"Last run")],required=False,initial='0')
    idroute = django.forms.ChoiceField([],required=False,initial='')
    editype = django.forms.ChoiceField(EDITYPELIST,required=False)
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
    confirmtype = django.forms.CharField(required=False,widget=HIDDENINPUT())
    confirmed = django.forms.CharField(required=False,widget=HIDDENINPUT())
    idroute = django.forms.CharField(required=False,widget=HIDDENINPUT())
    editype = django.forms.CharField(required=False,widget=HIDDENINPUT())
    messagetype = django.forms.CharField(required=False,widget=HIDDENINPUT())
    frompartner = django.forms.CharField(required=False,widget=HIDDENINPUT())
    topartner = django.forms.CharField(required=False,widget=HIDDENINPUT())
    fromchannel = django.forms.CharField(required=False,widget=HIDDENINPUT())
    tochannel = django.forms.CharField(required=False,widget=HIDDENINPUT())

class UploadFileForm(django.forms.Form):
    file  = django.forms.FileField(label='Plugin to read',required=True,widget=django.forms.widgets.FileInput(attrs={'size':'100'}))

class PlugoutForm(django.forms.Form):
    databaseconfiguration = django.forms.BooleanField(required=False,initial=True,help_text='Routes, channels, translations, partners, etc.')
    umlists = django.forms.BooleanField(required=False,initial=True,label='User maintained code lists',help_text='')
    fileconfiguration = django.forms.BooleanField(required=False,initial=True,help_text='Grammars, mapping scrips, routes scripts, etc. (bots/usersys)')
    infiles = django.forms.BooleanField(required=False,initial=True,help_text='Examples edi file in bots/botssys/infile')
    charset = django.forms.BooleanField(required=False,initial=False,label='(Edifact) files with character sets',help_text='seldom needed.')
    databasetransactions = django.forms.BooleanField(required=False,initial=False,help_text='From the database: Runs, incoming files, outgoing files, documents;  only for support purposes, on request.')
    data = django.forms.BooleanField(required=False,initial=False,label='All transaction files',help_text='bots/botssys/data; only for support purposes, on request.')
    logfiles = django.forms.BooleanField(required=False,initial=False,label='Log files',help_text='bots/botssys/logging; only for support purposes, on request.')
    config = django.forms.BooleanField(required=False,initial=False,label='configuration files',help_text='bots/config; only for support purposes, on request.')
    database = django.forms.BooleanField(required=False,initial=False,label='SQLite database',help_text='Only for support purposes, on request.')

class DeleteForm(django.forms.Form):
    delbackup = django.forms.BooleanField(required=False,label='Delete backups of user scripts',initial=True,help_text='Delete backup files in usersys (purge).')
    deltransactions = django.forms.BooleanField(required=False,label='Delete transactions',initial=True,help_text='Delete runs, reports, incoming, outgoing, data files.')
    delacceptance = django.forms.BooleanField(required=False,label='Delete transactions in acceptance testing',initial=False,help_text='Delete runs, reports, incoming, outgoing, data files from acceptance testing.')
    delconfiguration = django.forms.BooleanField(required=False,label='Delete configuration',initial=False,help_text='Delete routes, channels, translations, partners etc.')
    delcodelists = django.forms.BooleanField(required=False,label='Delete user code lists',initial=False,help_text='Delete user code lists.')
    deluserscripts = django.forms.BooleanField(required=False,label='Delete all user scripts',initial=False,help_text='Delete all scripts in usersys (grammars, mappings etc) except charsets.')
    delinfile = django.forms.BooleanField(required=False,label='Delete botssys/infiles',initial=False,help_text='Delete files in botssys/infile.')
    deloutfile = django.forms.BooleanField(required=False,label='Delete botssys/outfiles',initial=False,help_text='Delete files in botssys/outfile.')
