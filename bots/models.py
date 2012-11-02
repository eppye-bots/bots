#~ from datetime import datetime
from django.db import models
from django.utils.translation import ugettext as _
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
#django is not excellent in generating db. But they have provided a way to customize the generated database using SQL. see bots/sql/*.

STATUST = [
    (0, _(u'Open')),
    (1, _(u'Error')),
    (2, _(u'Stuck')),
    (3, _(u'Done')),
    (4, _(u'Resend')),
    ]
STATUS = [
    (1,_(u'process')),
    (3,_(u'discarded')),
    (200,_(u'Received')),
    (220,_(u'Infile')),
    (310,_(u'Parsed')),
    (320,_(u'Split')),
    (330,_(u'Translated')),
    (400,_(u'Merged')),
    (500,_(u'Outfile')),
    (520,_(u'Send')),
    ]
EDITYPES = [
    ('csv', _(u'csv')),
    ('database', _(u'database (old)')),
    ('db', _(u'db')),
    ('edifact', _(u'edifact')),
    ('email-confirmation',_(u'email-confirmation')),
    ('excel',_(u'excel (only incoming)')),
    ('fixed', _(u'fixed')),
    ('idoc', _(u'idoc')),
    ('json', _(u'json')),
    ('jsonnocheck', _(u'jsonnocheck')),
    ('mailbag', _(u'mailbag')),
    ('raw', _(u'raw')),
    ('template', _(u'template (old)')),
    ('templatehtml', _(u'template-html')),
    ('tradacoms', _(u'tradacoms')),
    ('xml', _(u'xml')),
    ('xmlnocheck', _(u'xmlnocheck')),
    ('x12', _(u'x12')),
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
    ('imap4', _(u'imap4')),
    ('imap4s', _(u'imap4s')),
    ('ftp', _(u'ftp')),
    ('ftps', _(u'ftps (explicit)')),
    ('ftpis', _(u'ftps (implicit)')),
    ('sftp', _(u'sftp (ssh)')),
    ('xmlrpc', _(u'xmlrpc')),
    ('mimefile', _(u'mimefile')),
    ('communicationscript', _(u'communicationscript')),
    ('db', _(u'db')),
    ('database', _(u'database (old)')),
    )
CONFIRMTYPE = [
    ('ask-email-MDN',_(u'ask an email confirmation (MDN) when sending')),
    ('send-email-MDN',_(u'send an email confirmation (MDN) when receiving')),
    ('ask-x12-997',_(u'ask a x12 confirmation (997) when sending')),
    ('send-x12-997',_(u'send a x12 confirmation (997) when receiving')),
    ('ask-edifact-CONTRL',_(u'ask an edifact confirmation (CONTRL) when sending')),
    ('send-edifact-CONTRL',_(u'send an edifact confirmation (CONTRL) when receiving')),
    ]
RULETYPE = (
    ('all',_(u'all')),
    ('route',_(u'route')),
    ('channel',_(u'channel')),
    ('frompartner',_(u'frompartner')),
    ('topartner',_(u'topartner')),
    ('messagetype',_(u'messagetype')),
    )
ENCODE_MIME = (
    ('always',_(u'base64')),
    ('never',_(u'never')),
    ('ascii',_(u'base64 if not ascii')),
    )
EDI_AS_ATTACHMENT = (
    ('attachment',_(u'edi file as attachment')),
    ('body',_(u'edi file in body of email')),
    )
ENCODE_ZIP_IN = (
    (1,_(u'unzip always')),
    (2,_(u'unzip if zip')),
    )
ENCODE_ZIP_OUT = (
    (1,_(u'zip always')),
    )
TRANSLATETYPES = (
    (0,_(u'Nothing')),
    (1,_(u'Translate')),
    (2,_(u'Pass-through')),
    )


class StripCharField(models.CharField):
    ''' strip values before saving to database. this is not default in django #%^&*'''
    def get_db_prep_value(self, value,*args,**kwargs):
        """Returns field's value prepared for interacting with the database
        backend.

        Used by the default implementations of ``get_db_prep_save``and
        `get_db_prep_lookup```
        """
        if isinstance(value, basestring):
            return value.strip()
        else:
            return value

def multiple_email_validator(value):
    emails = value.split(',')
    for email in emails:
        try:
            validate_email(email.strip())
        except ValidationError:
            raise ValidationError(_(u'Enter valid e-mail address(es) separated by commas.'), code='invalid')

class MultipleEmailField(models.CharField):
    default_validators = [multiple_email_validator]
    description = _('One or more e-mail address(es),separated by ",".')

#***********************************************************************************
#******** written by webserver ********************************************************
#***********************************************************************************
class confirmrule(models.Model):
    #~ id = models.IntegerField(primary_key=True)
    active = models.BooleanField(default=False)
    confirmtype = StripCharField(max_length=35,choices=CONFIRMTYPE)
    ruletype = StripCharField(max_length=35,choices=RULETYPE)
    negativerule = models.BooleanField(default=False)
    frompartner = models.ForeignKey('partner',related_name='cfrompartner',null=True,on_delete=models.CASCADE,blank=True)
    topartner = models.ForeignKey('partner',related_name='ctopartner',null=True,on_delete=models.CASCADE,blank=True)
    #~ idroute = models.ForeignKey('routes',null=True,blank=True,verbose_name='route')
    idroute = StripCharField(max_length=35,null=True,blank=True,verbose_name=_(u'route'))
    idchannel = models.ForeignKey('channel',null=True,on_delete=models.CASCADE,blank=True,verbose_name=_(u'channel'))
    editype = StripCharField(max_length=35,choices=EDITYPES,blank=True)
    messagetype = StripCharField(max_length=35,blank=True)
    rsrv1 = StripCharField(max_length=35,blank=True,null=True)  #added 20100501
    rsrv2 = models.IntegerField(null=True)                        #added 20100501
    def __unicode__(self):
        return unicode(self.confirmtype) + u' ' + unicode(self.ruletype)
    class Meta:
        db_table = 'confirmrule'
        verbose_name = _(u'confirm rule')
        ordering = ['confirmtype','ruletype']
class ccodetrigger(models.Model):
    ccodeid = StripCharField(primary_key=True,max_length=35,verbose_name=_(u'type code'))
    ccodeid_desc = StripCharField(max_length=35,null=True,blank=True)
    def __unicode__(self):
        return unicode(self.ccodeid)
    class Meta:
        db_table = 'ccodetrigger'
        verbose_name = _(u'user code type')
        ordering = ['ccodeid']
class ccode(models.Model):
    #~ id = models.IntegerField(primary_key=True)     #added 20091221
    ccodeid = models.ForeignKey(ccodetrigger,on_delete=models.CASCADE,verbose_name=_(u'type code'))
    leftcode = StripCharField(max_length=35,db_index=True)
    rightcode = StripCharField(max_length=35,db_index=True)
    attr1 = StripCharField(max_length=35,blank=True)
    attr2 = StripCharField(max_length=35,blank=True)
    attr3 = StripCharField(max_length=35,blank=True)
    attr4 = StripCharField(max_length=35,blank=True)
    attr5 = StripCharField(max_length=35,blank=True)
    attr6 = StripCharField(max_length=35,blank=True)
    attr7 = StripCharField(max_length=35,blank=True)
    attr8 = StripCharField(max_length=35,blank=True)
    def __unicode__(self):
        return unicode(self.ccodeid) + u' ' + unicode(self.leftcode) + u' ' + unicode(self.rightcode)
    class Meta:
        db_table = 'ccode'
        verbose_name = _(u'user code')
        unique_together = (('ccodeid','leftcode','rightcode'),)
        ordering = ['ccodeid','leftcode']
class channel(models.Model):
    idchannel = StripCharField(max_length=35,primary_key=True)
    inorout = StripCharField(max_length=35,choices=INOROUT,verbose_name=_(u'in/out'))
    type = StripCharField(max_length=35,choices=CHANNELTYPE)        #protocol type: edifact, x12, csv, etc
    charset = StripCharField(max_length=35,default=u'us-ascii')     #20120828: not used anymore
    host = StripCharField(max_length=256,blank=True)
    port = models.PositiveIntegerField(default=0,blank=True,null=True)
    username = StripCharField(max_length=35,blank=True)
    secret = StripCharField(max_length=35,blank=True,verbose_name=_(u'password'))
    starttls = models.BooleanField(default=False,verbose_name='No check from-address',help_text=_(u"Do not check if an incoming 'from' email addresses is known."))       #20091027: used as 'no check on "from:" email address'
    apop = models.BooleanField(default=False,verbose_name='No check to-address',help_text=_(u"Do not check if an incoming 'to' email addresses is known."))       #20110104: used as 'no check on "to:" email address'
    remove = models.BooleanField(default=False,help_text=_(u"For in-channels: delete edi files after successful reading. Note: you'll want this in production, else edi files are read over and over again!"))
    path = StripCharField(max_length=256,blank=True)  #different from host - in ftp both are used
    filename = StripCharField(max_length=256,blank=True,help_text=_(u'Filename to read or write. Incoming: Wildcards allowed eg "*.edi". For outgoing it is advised to use "*" in filename (is replaced by unique counter per channel); eg "D_*.edi" gives D_1.edi, D_2.edi, etc. More info in <a target="_blank" href="http://code.google.com/p/bots/wiki/Filenames">wiki</a>.'))
    lockname = StripCharField(max_length=35,blank=True,help_text=_(u'Use directory locking: when reading or writing edi files in this directory use this file to indicate directory lock.'))
    syslock = models.BooleanField(default=False,help_text=_(u'Use system file locking for reading & writing edi files on windows, *nix.'))
    parameters = StripCharField(max_length=70,blank=True)
    ftpaccount = StripCharField(max_length=35,blank=True)
    ftpactive = models.BooleanField(default=False)
    ftpbinary = models.BooleanField(default=False)
    askmdn = StripCharField(max_length=17,blank=True,choices=ENCODE_MIME,verbose_name=_(u'mime encoding'),help_text=_(u'Should edi-files be base64-encoded in email. Using base64 for edi (default) is often a good choice.'))     #20100703: used to indicate mime-encoding
    sendmdn = StripCharField(max_length=17,blank=True,choices=EDI_AS_ATTACHMENT,verbose_name=_(u'Edi file in email as'),help_text=_(u'Should edi-files in emails be send as attchment or in body?'))      #20120922: for email/mime: edi file as attachment or in body 
    mdnchannel = StripCharField(max_length=35,blank=True)           #not used anymore 20091019
    archivepath = StripCharField(max_length=256,blank=True,verbose_name=_(u'Archive path'),help_text=_(u'Write incoming or outgoing edi files to an archive. Use absolute or relative path (relative to bots directory). Eg: "botssys/archive/mychannel".'))           #added 20091028
    desc = models.TextField(max_length=256,null=True,blank=True)
    rsrv1 = StripCharField(max_length=35,blank=True,null=True)      #added 20100501
    rsrv2 = models.IntegerField(null=True,blank=True,verbose_name=_(u'Max seconds'),help_text=_(u'Max seconds for in-communication channel. Purpose: limit incoming edi files; better read more often tan everything in one time.'))   #added 20100501. 20110906: max communication time.
    rsrv3 = models.IntegerField(null=True,blank=True)   #added 20121030.
    class Meta:
        ordering = ['idchannel']
        db_table = 'channel'
    def __unicode__(self):
        return self.idchannel
class partner(models.Model):
    idpartner = StripCharField(max_length=35,primary_key=True,verbose_name=_(u'partner identification'))
    active = models.BooleanField(default=False)
    isgroup = models.BooleanField(default=False)
    name = StripCharField(max_length=256) #only used for user information
    mail = StripCharField(max_length=256,blank=True)
    cc = MultipleEmailField(max_length=256,blank=True)
    mail2 = models.ManyToManyField(channel, through='chanpar',blank=True)
    group = models.ManyToManyField("self",db_table='partnergroup',blank=True,symmetrical=False,limit_choices_to = {'isgroup': True})
    rsrv1 = StripCharField(max_length=35,blank=True,null=True)  #added 20100501
    rsrv2 = models.IntegerField(null=True)                        #added 20100501
    class Meta:
        ordering = ['idpartner']
        db_table = 'partner'
    def __unicode__(self):
        return unicode(self.idpartner) + ' (' + unicode(self.name) + ')'
class chanpar(models.Model):
    #~ id = models.IntegerField(primary_key=True)     #added 20091221
    idpartner = models.ForeignKey(partner,on_delete=models.CASCADE,verbose_name=_(u'partner'))
    idchannel = models.ForeignKey(channel,on_delete=models.CASCADE,verbose_name=_(u'channel'))
    mail = StripCharField(max_length=256)
    cc = MultipleEmailField(max_length=256,blank=True)           #added 20091111
    askmdn = models.BooleanField(default=False)     #not used anymore 20091019
    sendmdn = models.BooleanField(default=False)    #not used anymore 20091019
    class Meta:
        unique_together = (("idpartner","idchannel"),)
        db_table = 'chanpar'
        verbose_name = _(u'email address per channel')
        verbose_name_plural = _(u'email address per channel')
    def __unicode__(self):
        return str(self.idpartner) + ' ' + str(self.idchannel) + ' ' + str(self.mail)
class translate(models.Model):
    #~ id = models.IntegerField(primary_key=True)
    active = models.BooleanField(default=False)
    fromeditype = StripCharField(max_length=35,choices=EDITYPES,help_text=_(u'Editype to translate from.'))
    frommessagetype = StripCharField(max_length=35,help_text=_(u'Messagetype to translate from.'))
    alt = StripCharField(max_length=35,null=False,blank=True,verbose_name=_(u'Alternative translation'),help_text=_(u'Do this translation only for this alternative translation.'))
    frompartner = models.ForeignKey(partner,related_name='tfrompartner',null=True,blank=True,on_delete=models.PROTECT,help_text=_(u'Do this translation only for this frompartner.'))
    topartner = models.ForeignKey(partner,related_name='ttopartner',null=True,blank=True,on_delete=models.PROTECT,help_text=_(u'Do this translation only for this topartner.'))
    tscript = StripCharField(max_length=35,help_text=_(u'User mappingscript to use for translation.'))
    toeditype = StripCharField(max_length=35,choices=EDITYPES,help_text=_(u'Editype to translate to.'))
    tomessagetype = StripCharField(max_length=35,help_text=_(u'Messagetype to translate to.'))
    desc = models.TextField(max_length=256,null=True,blank=True)
    rsrv1 = StripCharField(max_length=35,blank=True,null=True)  #added 20100501
    rsrv2 = models.IntegerField(null=True)                        #added 20100501
    class Meta:
        db_table = 'translate'
        verbose_name = _(u'translation')
        ordering = ['fromeditype','frommessagetype']
    def __unicode__(self):
        return unicode(self.fromeditype) + u' ' + unicode(self.frommessagetype) + u' ' + unicode(self.alt) + u' ' + unicode(self.frompartner) + u' ' + unicode(self.topartner)
class routes(models.Model):
    #~ id = models.IntegerField(primary_key=True)
    idroute = StripCharField(max_length=35,db_index=True,help_text=_(u'identification of route; one route can consist of multiple parts having the same "idroute".'))
    seq = models.PositiveIntegerField(default=1,help_text=_(u'for routes consisting of multiple parts, "seq" indicates the order these parts are run.'))
    active = models.BooleanField(default=False)
    fromchannel = models.ForeignKey(channel,related_name='rfromchannel',null=True,on_delete=models.SET_NULL,blank=True,verbose_name=_(u'incoming channel'),limit_choices_to = {'inorout': 'in'})
    fromeditype = StripCharField(max_length=35,choices=EDITYPES,blank=True,help_text=_(u'the editype of the incoming edi files.'))
    frommessagetype = StripCharField(max_length=35,blank=True,help_text=_(u'the messagetype of incoming edi files. For edifact: messagetype=edifact; for x12: messagetype=x12.'))
    tochannel = models.ForeignKey(channel,related_name='rtochannel',null=True,on_delete=models.SET_NULL,blank=True,verbose_name=_(u'outgoing channel'),limit_choices_to = {'inorout': 'out'})
    toeditype = StripCharField(max_length=35,choices=EDITYPES,blank=True,help_text=_(u'Only edi files with this editype to this outgoing channel.'))
    tomessagetype = StripCharField(max_length=35,blank=True,help_text=_(u'Only edi files of this messagetype to this outgoing channel.'))
    alt = StripCharField(max_length=35,default=u'',blank=True,verbose_name='Alternative translation',help_text=_(u'Only use if there is more than one "translation" for the same editype and messagetype.'))
    frompartner = models.ForeignKey(partner,related_name='rfrompartner',null=True,on_delete=models.SET_NULL,blank=True,help_text=_(u'The frompartner of the incoming edi files.'))
    topartner = models.ForeignKey(partner,related_name='rtopartner',null=True,on_delete=models.SET_NULL,blank=True,help_text=_(u'The topartner of the incoming edi files.'))
    frompartner_tochannel = models.ForeignKey(partner,related_name='rfrompartner_tochannel',null=True,on_delete=models.PROTECT,blank=True,help_text=_(u'Only edi files from this partner/partnergroup for this outgoing channel'))
    topartner_tochannel = models.ForeignKey(partner,related_name='rtopartner_tochannel',null=True,on_delete=models.PROTECT,blank=True,help_text=_(u'Only edi files to this partner/partnergroup to this channel'))
    testindicator = StripCharField(max_length=1,blank=True,help_text=_(u'Only edi files with this testindicator to this outgoing channel.'))
    translateind = models.IntegerField(default=1,choices=TRANSLATETYPES,verbose_name='translate',help_text=_(u'Indicates what to do with incoming files for this route(part).'))
    notindefaultrun = models.BooleanField(default=False,blank=True,help_text=_(u'Do not use this route in a normal run. Advanced, related to scheduling specific routes or not.'))
    desc = models.TextField(max_length=256,null=True,blank=True)
    rsrv1 = StripCharField(max_length=35,blank=True,null=True)  #added 20100501 
    rsrv2 = models.IntegerField(null=True,blank=True)           #added 20100501
    defer = models.BooleanField(default=False,blank=True,help_text=_(u'Set ready for communication, but defer actual communication (this is done in another route)'))                        #added 20100601
    zip_incoming = models.IntegerField(null=True,blank=True,choices=ENCODE_ZIP_IN,verbose_name=_(u'Incoming zip-file handling'),help_text=_(u'Received files are zipped.'))  #added 20100501 #20120828: use for zip-options
    zip_outgoing = models.IntegerField(null=True,blank=True,choices=ENCODE_ZIP_OUT,verbose_name=_(u'Outgoing zip-file handling'),help_text=_(u'Send files as zip-files.'))                        #added 20100501
    class Meta:
        db_table = 'routes'
        verbose_name = _(u'route')
        unique_together = (("idroute","seq"),)
        ordering = ['idroute','seq']
    def __unicode__(self):
        return unicode(self.idroute) + u' ' + unicode(self.seq)

#***********************************************************************************
#******** written by engine ********************************************************
#***********************************************************************************
class filereport(models.Model):
    #~ id = models.IntegerField(primary_key=True)
    idta = models.IntegerField(primary_key=True)
    reportidta = models.IntegerField()
    statust = models.IntegerField(choices=STATUST)
    retransmit = models.IntegerField()
    idroute = StripCharField(max_length=35)
    fromchannel = StripCharField(max_length=35)
    tochannel = StripCharField(max_length=35)
    frompartner = StripCharField(max_length=35)
    topartner = StripCharField(max_length=35)
    frommail = StripCharField(max_length=256)
    tomail = StripCharField(max_length=256)
    ineditype = StripCharField(max_length=35,choices=EDITYPES)
    inmessagetype = StripCharField(max_length=35)
    outeditype = StripCharField(max_length=35,choices=EDITYPES)
    outmessagetype = StripCharField(max_length=35)
    incontenttype = StripCharField(max_length=35)
    outcontenttype = StripCharField(max_length=35)
    nrmessages = models.IntegerField()
    ts = models.DateTimeField(db_index=True) #copied from ta
    infilename = StripCharField(max_length=256)
    inidta = models.IntegerField(null=True)   #not used anymore
    outfilename = StripCharField(max_length=256)
    outidta = models.IntegerField()
    divtext = StripCharField(max_length=35)
    errortext = models.TextField()
    rsrv1 = StripCharField(max_length=35,blank=True,null=True)  #added 20100501; 20120618: email subject
    rsrv2 = models.IntegerField(null=True)                        #added 20100501
    filesize = models.IntegerField(null=True)                    #added 20121030
    class Meta:
        db_table = 'filereport'
class mutex(models.Model):
    #specific SQL is used (database defaults are used)
    mutexk = models.IntegerField(primary_key=True)  #is always value '1'
    mutexer = models.IntegerField() 
    ts = models.DateTimeField()         #timestamp of mutex
    class Meta:
        db_table = 'mutex'
class persist(models.Model):
    #OK, this has gone wrong. There is no primary key here, so django generates this. But there is no ID in the custom sql.
    #Django still uses the ID in sql manager. This leads to an error in snapshot plugin. Disabled this in snapshot function; to fix this really database has to be changed.
    #specific SQL is used (database defaults are used)
    domein = StripCharField(max_length=35)
    botskey = StripCharField(max_length=35)
    content = models.TextField()
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
    ts = models.DateTimeField(db_index=True)                     #copied from (runroot)ta
    type = StripCharField(max_length=35)
    status = models.BooleanField()
    rsrv1 = StripCharField(max_length=35,blank=True,null=True)  #added 20100501
    rsrv2 = models.IntegerField(null=True)                       #added 20100501.
    filesize = models.IntegerField(null=True)                    #added 20121030: total size of messages that have been translated.
    class Meta:
        db_table = 'report'
#~ #trigger for sqlite to use local time (instead of utc). I can not add this to sqlite specific sql code, as django does not allow complex (begin ... end) sql here.
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
    script = models.IntegerField()
    idroute = StripCharField(max_length=35)
    filename = StripCharField(max_length=256)
    frompartner = StripCharField(max_length=35)
    topartner = StripCharField(max_length=35)
    fromchannel = StripCharField(max_length=35)
    tochannel = StripCharField(max_length=35)
    editype = StripCharField(max_length=35)
    messagetype = StripCharField(max_length=35)
    alt = StripCharField(max_length=35)
    divtext = StripCharField(max_length=35)             #name of translation script. is not very useful...
    merge = models.BooleanField()
    nrmessages = models.IntegerField()
    testindicator = StripCharField(max_length=10)     #0:production; 1:test. Length to 1?
    reference = StripCharField(max_length=70,db_index=True)
    frommail = StripCharField(max_length=256)
    tomail = StripCharField(max_length=256)
    charset = StripCharField(max_length=35)
    statuse = models.IntegerField()                     #obsolete 20091019 but still used by intercommit comm. module
    retransmit = models.BooleanField()                  #20070831: only retransmit, not rereceive
    contenttype = StripCharField(max_length=35)
    errortext = models.TextField()                    #20120921: unlimited length
    ts = models.DateTimeField()
    confirmasked = models.BooleanField()              #added 20091019; confirmation asked or send
    confirmed = models.BooleanField()                 #added 20091019; is confirmation received (when asked)
    confirmtype = StripCharField(max_length=35)       #added 20091019
    confirmidta = models.IntegerField()               #added 20091019
    envelope = StripCharField(max_length=35)          #added 20091024
    botskey = StripCharField(max_length=35)           #added 20091024
    cc = StripCharField(max_length=512)               #added 20091111
    rsrv1 = StripCharField(max_length=35)             #added 20100501; 20120618: email subject
    rsrv2 = models.IntegerField(null=True)            #added 20100501;
    rsrv3 = StripCharField(max_length=35)             #added 20100501
    rsrv4 = models.IntegerField(null=True)            #added 20100501; 
    rsrv5 = StripCharField(max_length=35)             #added 20121030
    filesize = models.IntegerField(null=True)         #added 20121030; 
    numberofresends = models.IntegerField(null=True)  #added 20121030; if all OK (no resend) this is 0
    class Meta:
        db_table = 'ta'
class uniek(models.Model):
    #specific SQL is used (database defaults are used)
    domein = StripCharField(max_length=35,primary_key=True)
    nummer = models.IntegerField()
    class Meta:
        db_table = 'uniek'
        verbose_name = _(u'counter')
        ordering = ['domein']
