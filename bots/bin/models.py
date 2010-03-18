from django.db import models
from datetime import datetime

'''
- database defaults are not set up by django. what is needed? ts on ta
- some unique 
- codelists for values
'''
EDITYPES = [
    ('edifact', 'edifact'),
    ('x12', 'x12'),
    ('csv', 'csv'),
    ('fixed', 'fixed'),
    ('xml', 'xml'),
    ('json', 'json'),
    ('mailbag', 'mailbag'),
    ('idoc', 'idoc'),
    ('database', 'database'),
    ('xmlnocheck', 'xmlnocheck'),
    ('jsonnocheck', 'jsonnocheck'),
    ('template', 'template'),
    ('tradacoms', 'tradacoms'),
    ('email-confirmation','email-confirmation'),
    ]
INOROUT = (
    ('in', 'in'),
    ('out', 'out'),
    )
CHANNELTYPE = (
    ('file', 'file'),
    ('smtp', 'smtp'),
    ('smtps', 'smtps'),
    ('smtpstarttls', 'smtpstarttls'),
    ('pop3', 'pop3'),
    ('pop3s', 'pop3s'),
    ('pop3apop', 'pop3apop'),
    ('ftp', 'ftp'),
    ('mimefile', 'mimefile'),
    ('intercommit', 'intercommit'),
    ('database', 'database'),
    ('communicationscript', 'communicationscript'),
    )
CONFIRMTYPE = [
    ("ask-email-MDN","ask-email-MDN"),
    ("send-email-MDN","send-email-MDN"),
    ('ask-x12-997','ask-x12-997'),
    ('send-x12-997','send-x12-997'),
    ]
RULETYPE = (
    ('all','all'),
    ('route','route'),
    ('channel','channel'),
    ('frompartner','frompartner'),
    ('topartner','topartner'),
    ('messagetype','messagetype'),
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
    idroute = models.ForeignKey('routes',null=True,blank=True,verbose_name='route')
    idchannel = models.ForeignKey('channel',null=True,blank=True,verbose_name='channel')
    editype = models.CharField(max_length=35,choices=EDITYPES,blank=True)
    messagetype = models.CharField(max_length=35,blank=True)
    class Meta:
        db_table = 'confirmrule'
        verbose_name = 'confirm rule'
class ccodetrigger(models.Model):
    ccodeid = models.CharField(primary_key=True,max_length=35,verbose_name='type code')
    def __unicode__(self):
        return self.ccodeid
    class Meta:
        db_table = 'ccodetrigger'
        verbose_name = 'user code type'
class ccode(models.Model):
    #~ id = models.IntegerField(primary_key=True)     #added 20091221
    ccodeid = models.ForeignKey(ccodetrigger,verbose_name='type code')
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
        return ''
    class Meta:
        db_table = 'ccode'
        verbose_name = 'user code'
        unique_together = (("ccodeid","leftcode","rightcode"),)
class channel(models.Model):
    idchannel = models.CharField(max_length=35,primary_key=True)
    inorout = models.CharField(max_length=35,choices=INOROUT,verbose_name='in/out')
    type = models.CharField(max_length=35,choices=CHANNELTYPE)  #use seperate in/out; keuzelijst; ook keuzelijst voor type (FILE, POP3, etc)
    charset = models.CharField(max_length=35,default=u'us-ascii')
    host = models.CharField(max_length=256,blank=True)
    port = models.PositiveIntegerField(default=0,blank=True)
    username = models.CharField(max_length=35,blank=True)
    secret = models.CharField(max_length=35,blank=True,verbose_name='password')
    starttls = models.BooleanField(default=False,verbose_name='accept all fromaddresses')       #20091027: used as 'no check on "from:" email adress'
    apop = models.BooleanField(default=False)           #not used anymore (is in 'type' now)
    remove = models.BooleanField(default=False)
    path = models.CharField(max_length=256,blank=True)  #different from host - in ftp both are used
    filename = models.CharField(max_length=35,blank=True)
    lockname = models.CharField(max_length=35,blank=True)
    syslock = models.BooleanField(default=False)
    parameters = models.CharField(max_length=70,blank=True)
    ftpaccount = models.CharField(max_length=35,blank=True)
    ftpactive = models.BooleanField(default=False)
    ftpbinary = models.BooleanField(default=False)
    askmdn = models.CharField(max_length=17,blank=True)     #not used anymore 20091019
    sendmdn = models.CharField(max_length=17,blank=True)    #not used anymore 20091019
    mdnchannel = models.CharField(max_length=35,blank=True)             #not used anymore 20091019
    archivepath = models.CharField(max_length=256,blank=True)           #added 20091028
    def __unicode__(self):
        return self.idchannel
    class Meta:
        db_table = 'channel'
class partner(models.Model):
    idpartner = models.CharField(max_length=35,primary_key=True,verbose_name='partner identification') 
    active = models.BooleanField(default=False)
    isgroup = models.BooleanField(default=False)
    name = models.CharField(max_length=256) #only used for user information
    mail = models.EmailField(max_length=256,blank=True)
    cc = models.EmailField(max_length=256,blank=True)
    mail2 = models.ManyToManyField(channel, through='chanpar',blank=True)
    group = models.ManyToManyField("self",db_table='partnergroup',blank=True,limit_choices_to = {'isgroup': True})

    def __unicode__(self):
        return self.idpartner
    class Meta:
        db_table = 'partner'
class edigroup(partner):
    class Meta:
        proxy = True
        verbose_name = 'edipartnergroup'
class edipartner(partner):
    class Meta:
        proxy = True
        
class chanpar(models.Model):
    #~ id = models.IntegerField(primary_key=True)     #added 20091221
    idpartner = models.ForeignKey(partner,verbose_name='partner')
    idchannel = models.ForeignKey(channel,verbose_name='channel')
    mail = models.EmailField(max_length=256)
    cc = models.EmailField(max_length=256,blank=True)           #added 20091111
    askmdn = models.BooleanField(default=False)     #not used anymore 20091019
    sendmdn = models.BooleanField(default=False)    #not used anymore 20091019
    class Meta:
        unique_together = (("idpartner","idchannel"),)
        db_table = 'chanpar'
        verbose_name = 'email address per channel'
        verbose_name_plural = 'email address per channel'
class translate(models.Model):
    #~ id = models.IntegerField(primary_key=True)     #added 20091221
    active = models.BooleanField(default=False)
    fromeditype = models.CharField(max_length=35,choices=EDITYPES)
    frommessagetype = models.CharField(max_length=35)
    alt = models.CharField(max_length=35,null=False,blank=True)
    frompartner = models.ForeignKey(partner,related_name='tfrompartner',null=True,blank=True)
    topartner = models.ForeignKey(partner,related_name='ttopartner',null=True,blank=True)
    tscript = models.CharField(max_length=35,verbose_name='translation script')
    toeditype = models.CharField(max_length=35,choices=EDITYPES)
    tomessagetype = models.CharField(max_length=35)
    class Meta:
        db_table = 'translate'
        verbose_name = 'translation'
class routes(models.Model):  
    #~ id = models.IntegerField(primary_key=True)     #added 20091221
    idroute = models.CharField(max_length=35,db_index=True)
    seq = models.PositiveIntegerField(default=9999)
    active = models.BooleanField(default=False)
    fromchannel = models.ForeignKey(channel,related_name='rfromchannel',null=True,blank=True,verbose_name='incoming channel')
    fromeditype = models.CharField(max_length=35,choices=EDITYPES,blank=True)
    frommessagetype = models.CharField(max_length=35,blank=True)
    tochannel = models.ForeignKey(channel,related_name='rtochannel',null=True,blank=True,verbose_name='outgoing channel')
    toeditype = models.CharField(max_length=35,choices=EDITYPES,blank=True)
    tomessagetype = models.CharField(max_length=35,blank=True)
    alt = models.CharField(max_length=35,default=u'',blank=True)
    frompartner = models.ForeignKey(partner,related_name='rfrompartner',null=True,blank=True)
    topartner = models.ForeignKey(partner,related_name='rtopartner',null=True,blank=True)
    frompartner_tochannel = models.ForeignKey(partner,related_name='rfrompartner_tochannel',null=True,blank=True)
    topartner_tochannel = models.ForeignKey(partner,related_name='rtopartner_tochannel',null=True,blank=True)
    testindicator = models.CharField(max_length=1,blank=True)
    translateind = models.BooleanField(default=True,blank=True)
    notindefaultrun = models.BooleanField(default=False,blank=True)
    class Meta:
        db_table = 'routes'
        verbose_name = 'route'
        unique_together = (("idroute","seq"),)
    def __unicode__(self):
        return self.idroute

#***********************************************************************************
#******** written by engine ********************************************************
#***********************************************************************************
class filereport(models.Model):
    #~ id = models.IntegerField(primary_key=True)     #added 20091221
    idta = models.IntegerField(db_index=True)
    reportidta = models.IntegerField(db_index=True)
    statust = models.IntegerField()
    retransmit = models.BooleanField()
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
    class Meta:
        db_table = 'filereport'
        unique_together = (("idta","reportidta"),)
class mutex(models.Model):
    mutexk = models.IntegerField(primary_key=True)
    mutexer = models.IntegerField()
    #~ mysql_engine='InnoDB'
    class Meta:
        db_table = 'mutex'
class persist(models.Model):
    #~ id = models.IntegerField(primary_key=True)     #added 20091221
    domein = models.CharField(max_length=35)
    botskey = models.CharField(max_length=35,db_index=True)
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
    ts = models.DateTimeField() #copied from ta
    type = models.CharField(max_length=35)
    status = models.BooleanField()
    class Meta:
        db_table = 'report'
#trigger for sqlite to use local time (instead of utc)
#~ CREATE TRIGGER uselocaltime  AFTER INSERT ON ta                   
     #~ BEGIN                                                                 
     #~ UPDATE  ta   SET  ts = datetime('now = models.'localtime')
     #~ WHERE idta = new.idta ;
     #~ END
class ta(models.Model):
    idta = models.IntegerField(primary_key=True)
    statust = models.IntegerField()
    status = models.IntegerField()
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
    ts = models.DateTimeField(db_index=True)
    confirmasked = models.BooleanField()                #added 20091019; confirmation asked or send
    confirmed = models.BooleanField()                   #added 20091019; is confirmation received (when asked)
    confirmtype = models.CharField(max_length=35)       #added 20091019
    confirmidta = models.IntegerField()                 #added 20091019
    envelope = models.CharField(max_length=35)          #added 20091024
    botskey = models.CharField(max_length=35)           #added 20091024
    cc = models.CharField(max_length=512)               #added 20091111
    class Meta:
        db_table = 'ta'
class uniek(models.Model):
    domein = models.CharField(max_length=35,primary_key=True)
    nummer = models.IntegerField()
    class Meta:
        db_table = 'uniek'
        verbose_name = 'counter'
    #~ mysql_engine='InnoDB'
