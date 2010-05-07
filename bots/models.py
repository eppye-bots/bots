from datetime import datetime
from django.db import models
from django.utils.translation import ugettext as _
'''
django is not excellent in generating db. But they have provided a way to customize the generated database using SQL. I love this! see bots/sql/*.
'''

STATUST = [
    (0, _(u'Open')),
    (1, _(u'Error')),
    (2, _(u'Stuck')),
    (3, _(u'Done')),
    ]
RETRANSMIT = [
    (0, '---'),
    (1, _(u'Rereceive')),
    #~ (2, _(u'Retry')),
    #~ (3, _(u'RetryComm.')),
    ]
STATUS = [
    (1,_(u'process')),
    (200,_(u'FileRecieve')),
    (210,_(u'RawInfile')),
    (215,_(u'Mimein')),
    (220,_(u'Infile')),
    (280,_(u'Mailbag')),
    (290,_(u'Mailbagparsed')),
    (300,_(u'Translate')),
    (310,_(u'Parsed')),
    (320,_(u'Splitup')),
    (330,_(u'Translated')),
    (400,_(u'Merged')),
    (500,_(u'Outfile')),
    (510,_(u'RawOutfile')),
    (520,_(u'FileSend')),
    ]
EDITYPES = [
    ('edifact', _(u'edifact')),
    ('x12', _(u'x12')),
    ('csv', _(u'csv')),
    ('fixed', _(u'fixed')),
    ('xml', _(u'xml')),
    ('json', _(u'json')),
    ('mailbag', _(u'mailbag')),
    ('idoc', _(u'idoc')),
    ('database', _(u'database')),
    ('xmlnocheck', _(u'xmlnocheck')),
    ('jsonnocheck', _(u'jsonnocheck')),
    ('template', _(u'template')),
    ('tradacoms', _(u'tradacoms')),
    ('email-confirmation',_(u'email-confirmation')),
    ]
INOROUT = (
    ('in', _(u'in')),
    ('out', _(u'out')),
    )
CHANNELTYPE = (
    ('file', _(u'file')),
    ('smtp', _(u'smtp')),
    ('smtps', _(u'smtps')),
    ('smtpstarttls', _(u'smtpstarttls')),
    ('pop3', _(u'pop3')),
    ('pop3s', _(u'pop3s')),
    ('pop3apop', _(u'pop3apop')),
    ('ftp', _(u'ftp')),
    ('mimefile', _(u'mimefile')),
    ('intercommit', _(u'intercommit')),
    ('database', _(u'database')),
    ('communicationscript', _(u'communicationscript')),
    )
CONFIRMTYPE = [
    ('ask-email-MDN',_(u'ask-email-MDN')),
    ('send-email-MDN',_(u'send-email-MDN')),
    ('ask-x12-997',_(u'ask-x12-997')),
    ('send-x12-997',_(u'send-x12-997')),
    ]
RULETYPE = (
    ('all',_(u'all')),
    ('route',_(u'route')),
    ('channel',_(u'channel')),
    ('frompartner',_(u'frompartner')),
    ('topartner',_(u'topartner')),
    ('messagetype',_(u'messagetype')),
    )

#***********************************************************************************
#******** written by webserver ********************************************************
#***********************************************************************************
class confirmrule(models.Model):
    #~ id = models.IntegerField(primary_key=True)
    active = models.BooleanField(default=False)
    confirmtype = models.CharField(max_length=35,choices=CONFIRMTYPE)
    ruletype = models.CharField(max_length=35,choices=RULETYPE)
    negativerule = models.BooleanField(default=False)
    frompartner = models.ForeignKey('partner',related_name='cfrompartner',null=True,blank=True)
    topartner = models.ForeignKey('partner',related_name='ctopartner',null=True,blank=True)
    #~ idroute = models.ForeignKey('routes',null=True,blank=True,verbose_name='route')
    idroute = models.CharField(max_length=35,null=True,blank=True,verbose_name=_(u'route'))
    idchannel = models.ForeignKey('channel',null=True,blank=True,verbose_name=_(u'channel'))
    editype = models.CharField(max_length=35,choices=EDITYPES,blank=True)
    messagetype = models.CharField(max_length=35,blank=True)
    rsrv1 = models.CharField(max_length=35,blank=True,null=True)  #added 20100501
    rsrv2 = models.IntegerField(null=True)                        #added 20100501
    def __unicode__(self):
        return self.confirmtype + ' ' + self.ruletype
    class Meta:
        db_table = 'confirmrule'
        verbose_name = _(u'confirm rule')
class ccodetrigger(models.Model):
    ccodeid = models.CharField(primary_key=True,max_length=35,verbose_name=_(u'type code'))
    ccodeid_desc = models.CharField(max_length=35,null=True,blank=True)
    def __unicode__(self):
        return self.ccodeid
    class Meta:
        db_table = 'ccodetrigger'
        verbose_name = _(u'user code type')
class ccode(models.Model):
    #~ id = models.IntegerField(primary_key=True)     #added 20091221
    ccodeid = models.ForeignKey(ccodetrigger,verbose_name=_(u'type code'))
    leftcode = models.CharField(max_length=35,db_index=True)
    rightcode = models.CharField(max_length=35,db_index=True)
    attr1 = models.CharField(max_length=35,blank=True)
    attr2 = models.CharField(max_length=35,blank=True)
    attr3 = models.CharField(max_length=35,blank=True)
    attr4 = models.CharField(max_length=35,blank=True)
    attr5 = models.CharField(max_length=35,blank=True)
    attr6 = models.CharField(max_length=35,blank=True)
    attr7 = models.CharField(max_length=35,blank=True)
    attr8 = models.CharField(max_length=35,blank=True)
    def __unicode__(self):
        return self.ccodeid + ' ' + self.leftcode + ' ' + self.rightcode
    class Meta:
        db_table = 'ccode'
        verbose_name = _(u'user code')
        unique_together = (('ccodeid','leftcode','rightcode'),)
class channel(models.Model):
    idchannel = models.CharField(max_length=35,primary_key=True)
    inorout = models.CharField(max_length=35,choices=INOROUT,verbose_name=_(u'in/out'))
    type = models.CharField(max_length=35,choices=CHANNELTYPE)  #use seperate in/out; keuzelijst; ook keuzelijst voor type (FILE, POP3, etc)
    charset = models.CharField(max_length=35,default=u'us-ascii')
    host = models.CharField(max_length=256,blank=True)
    port = models.PositiveIntegerField(default=0,blank=True)
    username = models.CharField(max_length=35,blank=True)
    secret = models.CharField(max_length=35,blank=True,verbose_name=_(u'password'))
    starttls = models.BooleanField(default=False,verbose_name='Skip checking from-addresses',help_text=_(u'Do not check if an incoming email addresses exist in bots.'))       #20091027: used as 'no check on "from:" email adress'
    apop = models.BooleanField(default=False)           #not used anymore (is in 'type' now)
    remove = models.BooleanField(default=False,help_text=_(u'For in-channels: remove the edi files after succesful reading. Note: in production you do want to remove the edi files, else these are read over and over again!'))
    path = models.CharField(max_length=256,blank=True)  #different from host - in ftp both are used
    filename = models.CharField(max_length=35,blank=True,help_text=_(u'For "type" ftp and file; read or write this filename. Wildcards allowed, eg "*.edi". Note for out-channels: if no wildcard is used, all edi message are written to one file.'))
    lockname = models.CharField(max_length=35,blank=True,help_text=_(u'When reading or writing edi files in this directory use this file to indicate a directory lock.'))
    syslock = models.BooleanField(default=False,help_text=_(u'Use system file locking for reading & writing edi files on windows, *nix.'))
    parameters = models.CharField(max_length=70,blank=True)
    ftpaccount = models.CharField(max_length=35,blank=True)
    ftpactive = models.BooleanField(default=False)
    ftpbinary = models.BooleanField(default=False)
    askmdn = models.CharField(max_length=17,blank=True)     #not used anymore 20091019
    sendmdn = models.CharField(max_length=17,blank=True)    #not used anymore 20091019
    mdnchannel = models.CharField(max_length=35,blank=True)             #not used anymore 20091019
    archivepath = models.CharField(max_length=256,blank=True,verbose_name=_(u'Archive path'),help_text=_(u'Write incoming or outgoing edi files to an archive. Use absolute or relative path; relative path is relative to bots directory. Eg: "botssys/archive/mychannel".'))           #added 20091028
    desc = models.TextField(max_length=256,null=True,blank=True)
    rsrv1 = models.CharField(max_length=35,blank=True,null=True)  #added 20100501
    rsrv2 = models.IntegerField(null=True)                        #added 20100501
    def __unicode__(self):
        return self.idchannel
    class Meta:
        db_table = 'channel'
class partner(models.Model):
    idpartner = models.CharField(max_length=35,primary_key=True,verbose_name=_(u'partner identification'))
    active = models.BooleanField(default=False)
    isgroup = models.BooleanField(default=False)
    name = models.CharField(max_length=256) #only used for user information
    mail = models.EmailField(max_length=256,blank=True)
    cc = models.EmailField(max_length=256,blank=True)
    mail2 = models.ManyToManyField(channel, through='chanpar',blank=True)
    group = models.ManyToManyField("self",db_table='partnergroup',blank=True,symmetrical=False,limit_choices_to = {'isgroup': True})
    rsrv1 = models.CharField(max_length=35,blank=True,null=True)  #added 20100501
    rsrv2 = models.IntegerField(null=True)                        #added 20100501
    def __unicode__(self):
        return self.idpartner
    class Meta:
        db_table = 'partner'
        
class chanpar(models.Model):
    #~ id = models.IntegerField(primary_key=True)     #added 20091221
    idpartner = models.ForeignKey(partner,verbose_name=_(u'partner'))
    idchannel = models.ForeignKey(channel,verbose_name=_(u'channel'))
    mail = models.EmailField(max_length=256)
    cc = models.EmailField(max_length=256,blank=True)           #added 20091111
    askmdn = models.BooleanField(default=False)     #not used anymore 20091019
    sendmdn = models.BooleanField(default=False)    #not used anymore 20091019
    class Meta:
        unique_together = (("idpartner","idchannel"),)
        db_table = 'chanpar'
        verbose_name = _(u'email address per channel')
        verbose_name_plural = _(u'email address per channel')
    def __unicode__(self):
        return self.idpartner + ' ' + self.idchannel + ' ' + self.mail
class translate(models.Model):
    #~ id = models.IntegerField(primary_key=True)
    active = models.BooleanField(default=False)
    fromeditype = models.CharField(max_length=35,choices=EDITYPES,help_text=_(u'Editype to translate from.'))
    frommessagetype = models.CharField(max_length=35,help_text=_(u'Messagetype to translate from.'))
    alt = models.CharField(max_length=35,null=False,blank=True,verbose_name=_(u'Alternative translation'),help_text=_(u'Do this translation only for this alternative translation.'))
    frompartner = models.ForeignKey(partner,related_name='tfrompartner',null=True,blank=True,help_text=_(u'Do this translation only for this frompartner.'))
    topartner = models.ForeignKey(partner,related_name='ttopartner',null=True,blank=True,help_text=_(u'Do this translation only for this topartner.'))
    tscript = models.CharField(max_length=35,help_text=_(u'User mapping script to use for translation.'))
    toeditype = models.CharField(max_length=35,choices=EDITYPES,help_text=_(u'Editype to translate to.'))
    tomessagetype = models.CharField(max_length=35,help_text=_(u'Messagetype to translate to.'))
    desc = models.TextField(max_length=256,null=True,blank=True)
    rsrv1 = models.CharField(max_length=35,blank=True,null=True)  #added 20100501
    rsrv2 = models.IntegerField(null=True)                        #added 20100501
    class Meta:
        db_table = 'translate'
        verbose_name = _(u'translation')
    def __unicode__(self):
        return self.fromeditype + ' ' + self.frommessagetype + ' ' + self.alt + ' ' + self.frompartner + ' ' + self.topartner
class routes(models.Model):  
    #~ id = models.IntegerField(primary_key=True)
    idroute = models.CharField(max_length=35,db_index=True,help_text=_(u'identification of route; one route can consist of multiple parts having the same "idroute".'))
    seq = models.PositiveIntegerField(default=1,help_text=_(u'for routes consisting of multiple parts, "seq" indicates the order these parts are run.'))
    active = models.BooleanField(default=False)
    fromchannel = models.ForeignKey(channel,related_name='rfromchannel',null=True,blank=True,verbose_name=_(u'incoming channel'),limit_choices_to = {'inorout': 'in'})
    fromeditype = models.CharField(max_length=35,choices=EDITYPES,blank=True,help_text=_(u'the editype of the incoming edi files.'))
    frommessagetype = models.CharField(max_length=35,blank=True,help_text=_(u'the messagetype of incoming edi files. For edifact: messagetype=edifact; for x12: messagetype=x12.'))
    tochannel = models.ForeignKey(channel,related_name='rtochannel',null=True,blank=True,verbose_name=_(u'outgoing channel'),limit_choices_to = {'inorout': 'out'})
    toeditype = models.CharField(max_length=35,choices=EDITYPES,blank=True,help_text=_(u'Only edi files with this editype to this outgoing channel.'))
    tomessagetype = models.CharField(max_length=35,blank=True,help_text=_(u'Only edi files of this messagetype to this outgoing channel.'))
    alt = models.CharField(max_length=35,default=u'',blank=True,verbose_name='Alternative translation',help_text=_(u'Only use if there is more than one "translation" for the same editype and messagetype. Advanced use, seldom needed.'))
    frompartner = models.ForeignKey(partner,related_name='rfrompartner',null=True,blank=True,help_text=_(u'The frompartner of the incoming edi files. Seldom needed.'))
    topartner = models.ForeignKey(partner,related_name='rtopartner',null=True,blank=True,help_text=_(u'The topartner of the incoming edi files. Seldom needed.'))
    frompartner_tochannel = models.ForeignKey(partner,related_name='rfrompartner_tochannel',null=True,blank=True,help_text=_(u'Only edi files from this partner/partnergroup for this outgoing channel'))
    topartner_tochannel = models.ForeignKey(partner,related_name='rtopartner_tochannel',null=True,blank=True,help_text=_(u'Only edi files to this partner/partnergroup to this channel'))
    testindicator = models.CharField(max_length=1,blank=True,help_text=_(u'Only edi files with this testindicator to this outgoing channel.'))
    translateind = models.BooleanField(default=True,blank=True,verbose_name='translate',help_text=_(u'Do a translation in this route.'))
    notindefaultrun = models.BooleanField(default=False,blank=True,help_text=_(u'Do not use this route in a normal run. Advanced, related to scheduling specific routes or not.'))
    desc = models.TextField(max_length=256,null=True,blank=True)
    rsrv1 = models.CharField(max_length=35,blank=True,null=True)  #added 20100501
    rsrv2 = models.IntegerField(null=True)                        #added 20100501
    class Meta:
        db_table = 'routes'
        verbose_name = _(u'route')
        unique_together = (("idroute","seq"),)
    def __unicode__(self):
        return self.idroute + ' ' + self.seq

#***********************************************************************************
#******** written by engine ********************************************************
#***********************************************************************************
class filereport(models.Model):
    #~ id = models.IntegerField(primary_key=True)
    idta = models.IntegerField(db_index=True)
    reportidta = models.IntegerField(db_index=True)
    statust = models.IntegerField(choices=STATUST)
    retransmit = models.IntegerField(choices=RETRANSMIT)
    idroute = models.CharField(max_length=35)
    fromchannel = models.CharField(max_length=35)
    tochannel = models.CharField(max_length=35)
    frompartner = models.CharField(max_length=35)
    topartner = models.CharField(max_length=35)
    frommail = models.CharField(max_length=256)
    tomail = models.CharField(max_length=256)
    ineditype = models.CharField(max_length=35,choices=EDITYPES)
    inmessagetype = models.CharField(max_length=35)
    outeditype = models.CharField(max_length=35,choices=EDITYPES)
    outmessagetype = models.CharField(max_length=35)
    incontenttype = models.CharField(max_length=35)
    outcontenttype = models.CharField(max_length=35)
    nrmessages = models.IntegerField()
    ts = models.DateTimeField(db_index=True) #copied from ta
    infilename = models.CharField(max_length=256)
    inidta = models.IntegerField(null=True)   #not used anymore
    outfilename = models.CharField(max_length=256)
    outidta = models.IntegerField()
    divtext = models.CharField(max_length=35)
    errortext = models.CharField(max_length=2048)
    rsrv1 = models.CharField(max_length=35,blank=True,null=True)  #added 20100501
    rsrv2 = models.IntegerField(null=True)                        #added 20100501
    class Meta:
        db_table = 'filereport'
        unique_together = (("idta","reportidta"),)
class mutex(models.Model):
    #specific SQL is used (database defaults are used)
    mutexk = models.IntegerField(primary_key=True)
    mutexer = models.IntegerField()
    ts = models.DateTimeField()
    class Meta:
        db_table = 'mutex'
class persist(models.Model):
    #specific SQL is used (database defaults are used)
    domein = models.CharField(max_length=35)
    botskey = models.CharField(max_length=35)
    content = models.CharField(max_length=1024) 
    ts = models.DateTimeField()
    class Meta:
        db_table = 'persist'
        unique_together = (("domein","botskey"),)
class report(models.Model):
    idta = models.IntegerField(primary_key=True)    #rename to reportidta
    lastreceived = models.IntegerField()
    lastdone = models.IntegerField()
    lastopen = models.IntegerField()
    lastok = models.IntegerField()
    lasterror = models.IntegerField()
    send = models.IntegerField()
    processerrors = models.IntegerField()
    ts = models.DateTimeField()                     #copied from (runroot)ta
    type = models.CharField(max_length=35)
    status = models.BooleanField()
    rsrv1 = models.CharField(max_length=35,blank=True,null=True)  #added 20100501
    rsrv2 = models.IntegerField(null=True)                       ##added 20100501
    class Meta:
        db_table = 'report'
#~ #trigger for sqlite to use local time (instead of utc)
#~ CREATE TRIGGER uselocaltime  AFTER INSERT ON ta
#~ BEGIN
#~ UPDATE ta
#~ SET ts = datetime('now','localtime') 
#~ WHERE idta = new.idta ;
#~ END;
class ta(models.Model):
    #specific SQL is used (database defaults are used)
    idta = models.AutoField(primary_key=True)
    statust = models.IntegerField(choices=STATUST)
    status = models.IntegerField(choices=STATUS)
    parent = models.IntegerField(db_index=True)
    child = models.IntegerField()
    script = models.IntegerField(db_index=True)
    idroute = models.CharField(max_length=35)
    filename = models.CharField(max_length=256)
    frompartner = models.CharField(max_length=35)
    topartner = models.CharField(max_length=35)
    fromchannel = models.CharField(max_length=35)
    tochannel = models.CharField(max_length=35)
    editype = models.CharField(max_length=35)
    messagetype = models.CharField(max_length=35)
    alt = models.CharField(max_length=35)
    divtext = models.CharField(max_length=35)
    merge = models.BooleanField()
    nrmessages = models.IntegerField()
    testindicator = models.CharField(max_length=10)     #0:production; 1:test. Length to 1?
    reference = models.CharField(max_length=70)
    frommail = models.CharField(max_length=256)
    tomail = models.CharField(max_length=256)
    charset = models.CharField(max_length=35)
    statuse = models.IntegerField()                     #obsolete 20091019 but still used by intercommit comm. module
    retransmit = models.BooleanField()                  #20070831: only retransmit, not rerecieve
    contenttype = models.CharField(max_length=35)
    errortext = models.CharField(max_length=2048)
    ts = models.DateTimeField()
    confirmasked = models.BooleanField()                #added 20091019; confirmation asked or send
    confirmed = models.BooleanField()                   #added 20091019; is confirmation received (when asked)
    confirmtype = models.CharField(max_length=35)       #added 20091019
    confirmidta = models.IntegerField()                 #added 20091019
    envelope = models.CharField(max_length=35)          #added 20091024
    botskey = models.CharField(max_length=35)           #added 20091024
    cc = models.CharField(max_length=512)               #added 20091111
    rsrv1 = models.CharField(max_length=35)             #added 20100501
    rsrv2 = models.IntegerField(null=True)              #added 20100501
    rsrv3 = models.CharField(max_length=35)             #added 20100501
    rsrv4 = models.IntegerField(null=True)              #added 20100501
    class Meta:
        db_table = 'ta'
class uniek(models.Model):
    #specific SQL is used (database defaults are used)
    domein = models.CharField(max_length=35,primary_key=True)
    nummer = models.IntegerField()
    class Meta:
        db_table = 'uniek'
        verbose_name = _(u'counter')
