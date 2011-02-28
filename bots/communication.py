import os
import posixpath
try:
    import cPickle as pickle
except:
    import pickle
import time
import email
import email.Utils
#~ import email.Header
import email.Generator
import email.Message
#~ import email.Charset
try:
    import email.encoders as emailencoders
except:
    import email.Encoders as emailencoders #for python 2.4
import glob
import shutil
import fnmatch
import codecs
if os.name == 'nt':
    import msvcrt
elif os.name == 'posix':
    import fcntl
try:
    import json as simplejson
except ImportError:
    import simplejson
import smtplib
import poplib
import ftplib
import xmlrpclib
from django.utils.translation import ugettext as _
#Bots modules
import botslib
import botsglobal
import inmessage
import outmessage
from botsconfig import *

@botslib.log_session
def run(idchannel,idroute=''):
    '''run a communication session (dispatcher for communication functions).'''
    for channeldict in botslib.query('''SELECT *
                                FROM channel
                                WHERE idchannel=%(idchannel)s''',
                                {'idchannel':idchannel}):
        botsglobal.logger.debug(u'start communication channel "%s" type %s %s.',channeldict['idchannel'],channeldict['type'],channeldict['inorout'])
        botsglobal.logger.debug(u'(try) to read user communicationscript channel "%s".',channeldict['idchannel'])
        #update communication/run process with idchannel
        ta_run = botslib.OldTransaction(botslib._Transaction.processlist[-1])
        if channeldict['inorout'] == 'in':
            ta_run.update(fromchannel=channeldict['idchannel'])
        else:
            ta_run.update(tochannel=channeldict['idchannel'])
            
        try:
            userscript,scriptname = botslib.botsimport('communicationscripts',channeldict['idchannel'])
        except ImportError:
            userscript = scriptname = None
        if hasattr(userscript,'UserCommunicationClass'):
            classtocall = getattr(userscript,'UserCommunicationClass')
        else:
            classtocall = globals()[channeldict['type']]
        classtocall(channeldict,idroute,userscript,scriptname) #call the class for this type of channel
        botsglobal.logger.debug(u'finished communication channel "%s" type %s %s.',channeldict['idchannel'],channeldict['type'],channeldict['inorout'])
        break   #there can only be one channel; this break takes care that if found, the 'else'-clause is skipped
    else:
        raise botslib.CommunicationError(_(u'Channel "$idchannel" is unknown.'),idchannel=idchannel)


class _comsession(object):
    ''' Abstract class for communication-session. Use only subclasses.
        Subclasses are called by dispatcher function 'run'
        Often 'idroute' is passed as a parameter. This is ONLY because of the @botslib.log_session-wrapper!
        use self.idroute!!
    '''
    def __init__(self,channeldict,idroute,userscript,scriptname):
        ''' All communication is performed in init.'''
        self.channeldict=channeldict
        self.idroute=idroute
        self.userscript=userscript
        self.scriptname=scriptname
        if self.channeldict['inorout']=='out':
            #routes can have the same outchannel.
            #the different outchannels can be 'direct' or deffered (in route)
            nroffiles = self.precommunicate(FILEOUT,RAWOUT)
            if self.countoutfiles() > 0: #for out-comm: send if something to send
                self.connect()
                self.outcommunicate()
                self.disconnect()
                self.archive()
        else:   #incommunication
            if botsglobal.incommunicate: #for in-communication: only communicate for new run
                self.connect()
                self.incommunicate()
                self.disconnect()
            self.postcommunicate(RAWIN,FILEIN)
            self.archive()

    def archive(self):
        '''archive received or send files; archive only if receive is correct.'''
        if not self.channeldict['archivepath']:
            return
        if self.channeldict['inorout'] == 'in':
            status = FILEIN
            statust = OK
            channel = 'fromchannel'
        else:
            status = FILEOUT
            statust = DONE
            channel = 'tochannel'
           
        if self.userscript and hasattr(self.userscript,'archivepath'):
            archivepath = botslib.runscript(self.userscript,self.scriptname,'archivepath',channeldict=self.channeldict)
        else:
            archivepath = botslib.join(self.channeldict['archivepath'],time.strftime('%Y%m%d'))
        botslib.dirshouldbethere(archivepath)
        for row in botslib.query('''SELECT filename,idta
                                    FROM  ta
                                    WHERE idta>%(rootidta)s
                                    AND   status=%(status)s
                                    AND   statust=%(statust)s
                                    AND   ''' + channel + '''=%(idchannel)s
                                    AND   idroute=%(idroute)s
                                    ''',
                                    {'idchannel':self.channeldict['idchannel'],'status':status,
                                    'statust':statust,'idroute':self.idroute,'rootidta':botslib.get_minta4query()}):
            absfilename = botslib.abspathdata(row['filename'])
            if self.userscript and hasattr(self.userscript,'archivename'):
                archivename = botslib.runscript(self.userscript,self.scriptname,'archivename',channeldict=self.channeldict,idta=row['idta'],filename=absfilename)
                shutil.copy(absfilename,botslib.join(archivepath,archivename))
            else:
                shutil.copy(absfilename,archivepath)

    def countoutfiles(self):
        ''' counts the number of edifiles to be transmitted.'''
        for row in botslib.query('''SELECT COUNT(*) as count
                                    FROM  ta
                                    WHERE idta>%(rootidta)s
                                    AND   status=%(status)s
                                    AND   statust=%(statust)s
                                    AND   tochannel=%(tochannel)s
                                    ''',
                                    {'idroute':self.idroute,'status':RAWOUT,'statust':OK,
                                    'tochannel':self.channeldict['idchannel'],'rootidta':botslib.get_minta4query()}):
            return row['count']


    @botslib.log_session
    def postcommunicate(self,fromstatus,tostatus):
        ''' transfer communication-file from status RAWIN to FILEIN '''
        return botslib.addinfo(change={'status':tostatus},where={'status':fromstatus,'fromchannel':self.channeldict['idchannel'],'idroute':self.idroute})

    @botslib.log_session
    def precommunicate(self,fromstatus,tostatus):
        ''' transfer communication-file from status FILEOUT to RAWOUT'''
        return botslib.addinfo(change={'status':tostatus},where={'status':fromstatus,'tochannel':self.channeldict['idchannel']})

    def file2mime(self,fromstatus,tostatus):
        ''' transfer communication-file from status FILEOUT to RAWOUT and convert to mime.
            1 part/file always in 1 mail.
        '''
        counter = 0 #count the number of correct processed files
        #select files with right statust, status and channel.
        for row in botslib.query('''SELECT idta,filename,frompartner,topartner,charset,contenttype,editype
                                    FROM  ta
                                    WHERE idta>%(rootidta)s
                                    AND   status=%(status)s
                                    AND   statust=%(statust)s
                                    AND   tochannel=%(idchannel)s
                                    ''',
                                    {'idchannel':self.channeldict['idchannel'],'status':fromstatus,
                                    'statust':OK,'idroute':self.idroute,'rootidta':botslib.get_minta4query()}):
            try:
                ta_from = botslib.OldTransaction(row['idta'])
                ta_to = ta_from.copyta(status=tostatus)
                confirmtype = u''
                confirmasked = False
                charset = row['charset']
                
                if row['editype'] == 'email-confirmation': #outgoing MDN: message is already assembled
                    outfilename = row['filename']
                else:
                    #assemble message: 
                    message = email.Message.Message()
                    message.epilogue = ''	# Make sure message ends in a newline
                    #******generate headers*******************************
                    #~ message.set_type(contenttype)                               #contenttype is set in grammar.syntax
                    frommail,ccfrom = self.idpartner2mailaddress(row['frompartner'])    #lookup email address for partnerID
                    message.add_header('From', frommail)
                    tomail,ccto = self.idpartner2mailaddress(row['topartner'])          #lookup email address for partnerID
                    message.add_header('To',tomail)
                    if ccto:
                        message.add_header('CC',ccto)
                    reference=email.Utils.make_msgid(str(ta_to.idta))    #use transaction idta in message id.
                    message.add_header('Message-ID',reference)
                    ta_to.update(frommail=frommail,tomail=tomail,cc=ccto,reference=reference)   #update now (in order to use corect&updated ta_to in user script)
                    ta_to.synall()  #get all parameters of ta_to from database; ta_to is send to user script
                    
                    message.add_header("Date",email.Utils.formatdate(localtime=True))
                    #should a MDN be asked?
                    if botslib.checkconfirmrules('ask-email-MDN',idroute=self.idroute,idchannel=self.channeldict['idchannel'],
                                                                frompartner=row['frompartner'],topartner=row['topartner']):
                        message.add_header("Disposition-Notification-To",frommail)
                        confirmtype = u'ask-email-MDN'
                        confirmasked = True
                    #set subject
                    subject=str(row['idta'])
                    content = botslib.readdata(row['filename'])     #get attachment from data file
                    if self.userscript and hasattr(self.userscript,'subject'):
                        subject = botslib.runscript(self.userscript,self.scriptname,'subject',channeldict=self.channeldict,ta=ta_to,subjectstring=subject,content=content)
                    message.add_header('Subject',subject)
                    #set attachmentname; first generate default attachmentname
                    unique = str(botslib.unique(self.channeldict['idchannel'])) #create unique part for filename
                    if self.channeldict['filename']:
                        attachmentfilename = self.channeldict['filename'].replace('*',unique) #filename is filename in channel where '*' is replaced by idta
                    else:
                        attachmentfilename = unique
                    #user script for attachmentname
                    if self.userscript and hasattr(self.userscript,'filename'):
                        attachmentfilename = botslib.runscript(self.userscript,self.scriptname,'filename',channeldict=self.channeldict,ta=ta_to,filename=attachmentfilename)
                    if attachmentfilename:  #if None or empty string: not an attachment
                        message.add_header("Content-Disposition",'attachment',filename=attachmentfilename)
                    #end set attachmentname
                    charset = self.convertcodecformime(row['charset'])
                    message.add_header('Content-Type',row['contenttype'].lower(),charset=charset)          #contenttype is set in grammar.syntax
                    #*******set attachment/payload*************************
                    #~ content = botslib.readdata(contentfilename,charset)     #get attachment (the data file); read is using the right charset
                    #~ message.set_payload(content.encode(charset),str(charset))   #encode engain....basically just cheing the charset?.....str(charset) is because email-lib in python 2.4 wants this....
                    message.set_payload(content)   #do not use charset; this lead to unwanted encodings...bots always uses base64
                    if self.channeldict['askmdn'] == 'never':
                        emailencoders.encode_7or8bit(message)
                    elif self.channeldict['askmdn'] == 'ascii' and charset=='us-ascii':
                        pass
                    else:
                    #~ elif self.channeldict['askmdn'] in ['always',''] or (self.channeldict['askmdn'] == 'ascii' and charset!='us-ascii'):
                        emailencoders.encode_base64(message)
                    #*******write email to file***************************
                    outfilename = str(ta_to.idta)
                    outfile = botslib.opendata(outfilename, 'wb')
                    g = email.Generator.Generator(outfile, mangle_from_=False, maxheaderlen=78)
                    g.flatten(message,unixfrom=False)
                    outfile.close()
            except:
                txt=botslib.txtexc()
                ta_to.update(statust=ERROR,errortext=txt)
            else:
                counter += 1
                ta_from.update(statust=DONE)
                ta_to.update(statust=OK,filename=outfilename,confirmtype=confirmtype,confirmasked=confirmasked,charset=charset)
        return counter

    def mime2file(self,fromstatus,tostatus):
        ''' transfer communcation-file from RAWIN to FILEIN, convert from Mime to file.
            process mime-files:
            -   extract information (eg sender-address)
            -   do emailtransport-handling: generate MDN, process MDN
            -   save 'attachments' as files
            -   generate MDN if asked and OK from bots-configuration
        '''
        whitelist_multipart=['multipart/mixed','multipart/digest','multipart/signed','multipart/report','message/rfc822']
        whitelist_major=['text','application']
        blacklist_contenttype=['text/html','text/enriched','text/rtf','text/richtext','application/postscript']
        def savemime(msg):
            ''' save contents of email as seperate files.
                is a nested function.
                3x filtering:
                -   whitelist of multipart-contenttype
                -   whitelist of body-contentmajor
                -   blacklist of body-contentytpe
            '''
            nrmimesaved = 0
            if msg.is_multipart():
                if contenttype in whitelist_multipart:
                    for part in msg.get_payload():
                        nrmimesaved += savemime(part)
            else:    #is not a multipart
                if msg.get_content_maintype() not in whitelist_major or contenttype in blacklist_contenttype:
                    return 0
                content = msg.get_payload(decode=True)
                if not content or content.isspace():
                    return 0
                charset=msg.get_content_charset('')
                if not charset:
                    charset = self.channeldict['charset']
                if self.userscript and hasattr(self.userscript,'accept_incoming_attachment'):
                    accept_attachment = botslib.runscript(self.userscript,self.scriptname,'accept_incoming_attachment',channeldict=self.channeldict,ta=ta_mime,charset=charset,content=content,contenttype=contenttype)
                    if accept_attachment == False:
                        return 0
                ta_file = ta_mime.copyta(status=tostatus)
                outfilename = str(ta_file.idta)
                outfile = botslib.opendata(outfilename, 'wb')
                outfile.write(content)
                outfile.close()
                nrmimesaved+=1
                ta_file.update(statust=OK,
                                contenttype=contenttype,
                                charset=charset,
                                filename=outfilename)
            return nrmimesaved
        #*****************end of nested function savemime***************************
        @botslib.log_session
        def mdnreceive():
            tmp = msg.get_param('reporttype')
            if tmp is None or email.Utils.collapse_rfc2231_value(tmp)!='disposition-notification':    #invalid MDN
                raise botslib.CommunicationInError(u'Received email-MDN with errors.')
            for part in msg.get_payload():
                if part.get_content_type()=='message/disposition-notification':
                    originalmessageid = part['original-message-id']
                    if originalmessageid is not None:
                        break
            else:   #invalid MDN: 'message/disposition-notification' not in email
                raise botslib.CommunicationInError(_(u'Received email-MDN with errors.'))
            botslib.change('''UPDATE ta
                               SET   confirmed=%(confirmed)s, confirmidta=%(confirmidta)s
                               WHERE reference=%(reference)s
                               AND   status=%(status)s
                               AND   confirmasked=%(confirmasked)s
                               AND   confirmtype=%(confirmtype)s
                               ''',
                                {'status':RAWOUT,'reference':originalmessageid,'confirmed':True,'confirmtype':'ask-email-MDN','confirmidta':ta_mail.idta,'confirmasked':True})
            #for now no checking if processing was OK.....
            #performance: not good. Another way is to extract the orginal idta from the original messageid
        @botslib.log_session
        def mdnsend():
            if not botslib.checkconfirmrules('send-email-MDN',idroute=self.idroute,idchannel=self.channeldict['idchannel'],
                                                            frompartner=frompartner,topartner=topartner):
                return 0 #do not send
            #make message: header, text/plain, message/disposition-notification
            message = email.Message.Message()
            message['From'] = tomail
            dispositionnotificationto = email.Utils.parseaddr(msg['disposition-notification-to'])[1]
            message['To'] = dispositionnotificationto
            message['Subject']='Return Receipt (displayed) - '+subject
            message["Date"]=email.Utils.formatdate(localtime=True)
            message.set_type('multipart/report')
            message.set_param('reporttype','disposition-notification')
            message.epilogue = ''	# Make sure message ends in a newline

            #make human readable message
            humanmessage = email.Message.Message()
            humanmessage['Content-Type'] = 'text/plain'
            humanmessage.set_payload('This is an return receipt for the mail that you send to '+tomail)
            humanmessage.epilogue = ''	# Make sure message ends in a newline
            message.attach(humanmessage)
            
            #make machine readable message
            machinemessage = email.Message.Message()
            machinemessage['Content-Type'] = 'message/disposition-notification'
            machinemessage["Original-Message-ID"]=reference
            machinemessage.epilogue = ''	# Make sure message ends in a newline
            nep = email.Message.Message()
            machinemessage.attach(nep)
            message.attach(machinemessage)

            #write email to file;
            ta_mdn=botslib.NewTransaction(status=MERGED)  #new transaction for group-file
            mdn_reference = email.Utils.make_msgid(str(ta_mdn.idta))    #we first have to get the mda-ta to make this reference
            message['Message-ID'] = mdn_reference
            mdnfilename = str(ta_mdn.idta)
            mdnfile = botslib.opendata(mdnfilename, 'wb')
            g = email.Generator.Generator(mdnfile, mangle_from_=False, maxheaderlen=78)
            g.flatten(message,unixfrom=False)
            mdnfile.close()
            ta_mdn.update(statust=OK,
                            idroute=self.idroute,
                            filename=mdnfilename,
                            editype='email-confirmation',
                            frompartner=topartner,
                            topartner=frompartner,
                            frommail=tomail,
                            tomail=dispositionnotificationto,
                            reference=mdn_reference,
                            content='multipart/report',
                            fromchannel=self.channeldict['idchannel'],
                            charset='ascii')
            return ta_mdn.idta
        #*****************end of nested function dispositionnotification***************************
        #select received mails for channel
        for row in botslib.query('''SELECT    idta,filename
                                    FROM  ta
                                    WHERE   idta>%(rootidta)s
                                    AND     status=%(status)s
                                    AND     statust=%(statust)s
                                    AND     fromchannel=%(fromchannel)s
                                    ''',
                                    {'status':fromstatus,'statust':OK,'rootidta':botslib.get_minta4query(),
                                    'fromchannel':self.channeldict['idchannel'],'idroute':self.idroute}):
            try:
                confirmtype = ''
                confirmed = False
                confirmasked = False
                confirmidta = 0
                ta_mail = botslib.OldTransaction(row['idta'])
                ta_mime = ta_mail.copyta(status=MIMEIN)
                infile = botslib.opendata(row['filename'], 'rb')
                msg             = email.message_from_file(infile)   #read and parse mail
                infile.close()
                frommail        = email.Utils.parseaddr(msg['from'])[1]
                tos             = email.Utils.getaddresses(msg.get_all('to', []))
                ccs             = email.Utils.getaddresses(msg.get_all('cc', []))
                #~ tomail          = tos[0][1]  #tomail is the email address of the first "To"-recepient
                cc              = ','.join([emailaddress[1] for emailaddress in (tos + ccs)])
                reference       = msg['message-id']
                subject         = msg['subject']
                contenttype     = msg.get_content_type()
                #authorize: find the frompartner for the email addresses in the message
                frompartner = ''
                if not self.channeldict['starttls']:    #reusing old datbase name; 'no check on "from:" email adress'
                    frompartner = self.mailaddress2idpartner(frommail)
                topartner = ''  #initialise topartner
                tomail = ''  #initialise tomail
                if not self.channeldict['apop']:    #reusing old datbase name; 'no check on "to:" email adress'
                    for toname,tomail_tmp in tos:   #all tos-addresses are checked; only one needs to be authorised.
                        try:
                            topartner =  self.mailaddress2idpartner(tomail_tmp)
                            tomail = tomail_tmp
                            break
                        except botslib.CommunicationInError:
                            pass
                    else:
                        if not topartner:
                            emailtos = [address[1] for address in tos]
                            raise botslib.CommunicationInError(_(u'Emailaddress(es) $email not authorised/unknown (channel "$idchannel").'),email=emailtos,idchannel=self.channeldict['idchannel'])
                        
                
                #update transaction of mail with information found in mail
                ta_mime.update(frommail=frommail,   #why now why not later: because ta_mime is copied to seperate files later, so need the info now 
                                tomail=tomail,
                                reference=reference,
                                contenttype=contenttype,
                                frompartner=frompartner,
                                topartner=topartner,
                                cc = cc)
                if contenttype == 'multipart/report':   #process received MDN confirmation
                    mdnreceive()
                else:
                    if msg.has_key('disposition-notification-To'):  #sender requests a MDN
                        confirmidta = mdnsend()
                        if confirmidta:
                            confirmtype = 'send-email-MDN'
                            confirmed = True
                            confirmasked = True
                nrmimesaved = savemime(msg)
                if not nrmimesaved:
                    raise botslib.CommunicationInError (_(u'No valid attachment in received email'))
            except:
                txt=botslib.txtexc()
                ta_mime.failure()
                ta_mime.update(statust=ERROR,errortext=txt)
            else:
                ta_mime.update(statust=DONE)
                ta_mail.update(statust=DONE,confirmtype=confirmtype,confirmed=confirmed,confirmasked=confirmasked,confirmidta=confirmidta)
        return 0    #is not useful, as mime2file is used in postcommunication, and #files processed is not checked in postcommunication.

    def mailaddress2idpartner(self,mailaddress):
        for row in botslib.query(u'''SELECT chanpar.idpartner_id as idpartner
                                    FROM chanpar,channel,partner
                                    WHERE chanpar.idchannel_id=channel.idchannel
                                    AND chanpar.idpartner_id=partner.idpartner
                                    AND partner.active=%(active)s
                                    AND chanpar.idchannel_id=%(idchannel)s
                                    AND LOWER(chanpar.mail)=%(mail)s''',
                                    {'active':True,'idchannel':self.channeldict['idchannel'],'mail':mailaddress.lower()}):
            return row['idpartner']
        else:   #if not found
            for row in botslib.query(u'''SELECT idpartner
                                        FROM partner
                                        WHERE active=%(active)s
                                        AND LOWER(mail)=%(mail)s''',
                                        {'active':True,'mail':mailaddress.lower()}):
                return row['idpartner']
            raise botslib.CommunicationInError(_(u'Emailaddress "$email" unknown (or not authorised for channel "$idchannel").'),email=mailaddress,idchannel=self.channeldict['idchannel'])


    def idpartner2mailaddress(self,idpartner):
        for row in botslib.query(u'''SELECT chanpar.mail as mail,chanpar.cc as cc
                                    FROM    chanpar,channel,partner
                                    WHERE   chanpar.idchannel_id=channel.idchannel
                                    AND     chanpar.idpartner_id=partner.idpartner
                                    AND     partner.active=%(active)s
                                    AND     chanpar.idchannel_id=%(idchannel)s
                                    AND     chanpar.idpartner_id=%(idpartner)s''',
                                    {'active':True,'idchannel':self.channeldict['idchannel'],'idpartner':idpartner}):
            if row['mail']:
                return row['mail'],row['cc']
        else:   #if not found
            for row in botslib.query(u'''SELECT mail,cc
                                        FROM    partner
                                        WHERE   active=%(active)s
                                        AND     idpartner=%(idpartner)s''',
                                        {'active':True,'idpartner':idpartner}):
                if row['mail']:
                    return row['mail'],row['cc']
            else:
                raise botslib.CommunicationOutError(_(u'No mail-address for partner "$partner" (channel "$idchannel").'),partner=idpartner,idchannel=self.channeldict['idchannel'])

    def connect(self):
        pass
        
    def disconnect(self):
        pass

    @staticmethod
    def convertcodecformime(codec_in):
        convertdict = {
            'ascii' : 'us-ascii',
            'unoa' : 'us-ascii',
            'unob' : 'us-ascii',
            'unoc' : 'iso-8859-1',
            }
        codec_in = codec_in.lower().replace('_','-')
        return convertdict.get(codec_in,codec_in)
            

class pop3(_comsession):
    def connect(self):
        self.session = poplib.POP3(host=self.channeldict['host'],port=int(self.channeldict['port']))
        self.session.set_debuglevel(botsglobal.ini.getint('settings','pop3debug',0))    #if used, gives information about session (on screen), for debugging pop3
        self.session.user(self.channeldict['username'])
        self.session.pass_(self.channeldict['secret'])

    @botslib.log_session
    def incommunicate(self):
        ''' Fetch messages from Pop3-mailbox.
            SSL supported but: no keys-file/cert-file??.
            apop supported
        '''
        maillist = self.session.list()[1]     #get list of messages #alt: (response, messagelist, octets) = popsession.list()     #get list of messages
        for mail in maillist:				#message is string
            try:
                ta_from = botslib.NewTransaction(filename='pop3://'+self.channeldict['username']+'@'+self.channeldict['host'],
                                                    status=EXTERNIN,
                                                    fromchannel=self.channeldict['idchannel'],idroute=self.idroute)
                ta_to =   ta_from.copyta(status=RAWIN)
                filename = str(ta_to.idta)
                mailID = int(mail.split()[0])	#first 'word' is the message number/ID
                maillines = self.session.retr(mailID)[1]        #alt: (header, messagelines, octets) = popsession.retr(messageID)
                fp = botslib.opendata(filename, 'wb')
                fp.write(os.linesep.join(maillines))
                fp.close()
                if self.channeldict['remove']:
                    self.session.dele(mailID)
            except:
                txt=botslib.txtexc()
                botslib.ErrorProcess(functionname='pop3-incommunicate',errortext=txt)
                #~ ta_from.update(statust=ERROR,errortext=txt)  #this has the big advantage it will be retried again!
                ta_from.delete()
                ta_to.delete()    #is not received
            else:
                ta_from.update(statust=DONE)
                ta_to.update(statust=OK,filename=filename)

    @botslib.log_session
    def postcommunicate(self,fromstatus,tostatus):
        self.mime2file(fromstatus,tostatus)

    def disconnect(self):
        self.session.quit()

class pop3s(pop3):
    def connect(self):
        self.session = poplib.POP3_SSL(host=self.channeldict['host'],port=int(self.channeldict['port']))
        self.session.set_debuglevel(botsglobal.ini.getint('settings','pop3debug',0))    #if used, gives information about session (on screen), for debugging pop3
        self.session.user(self.channeldict['username'])
        self.session.pass_(self.channeldict['secret'])
        
class pop3apop(pop3):
    def connect(self):
        self.session = poplib.POP3(host=self.channeldict['host'],port=int(self.channeldict['port']))
        self.session.set_debuglevel(botsglobal.ini.getint('settings','pop3debug',0))    #if used, gives information about session (on screen), for debugging pop3
        self.session.apop(self.channeldict['username'],self.channeldict['secret'])    #looks like python handles password encryption by itself


class smtp(_comsession):
    @botslib.log_session
    def precommunicate(self,fromstatus,tostatus):
        return self.file2mime(fromstatus,tostatus)

    def connect(self):
        self.session = smtplib.SMTP(host=self.channeldict['host'],port=int(self.channeldict['port'])) #make connection
        self.session.set_debuglevel(botsglobal.ini.getint('settings','smtpdebug',0))    #if used, gives information about session (on screen), for debugging smtp
        self.login()

    def login(self):
        if self.channeldict['username'] and self.channeldict['secret']:
            try: 
                #error in python 2.6.4....user and password can not be unicode
                self.session.login(str(self.channeldict['username']),str(self.channeldict['secret']))
            except smtplib.SMTPAuthenticationError:
                raise botslib.CommunicationOutError(_(u'SMTP server did not accept user/password combination.'))
            except:
                txt=botslib.txtexc()
                raise botslib.CommunicationOutError(_(u'SMTP login failed: "$txt".'),txt=txt)
        
    @botslib.log_session
    def outcommunicate(self):
        ''' does smtp-session.
            SSL/TLS supported (no keys-file/cert-file supported yet)
            SMTP does not allow rollback. So if the sending of a mail fails, other mails may have been send.
        '''
        #send messages
        for row in botslib.query(u'''SELECT idta,filename,frommail,tomail,cc
                                    FROM  ta
                                    WHERE idta>%(rootidta)s
                                    AND   status=%(status)s
                                    AND   statust=%(statust)s
                                    AND   tochannel=%(tochannel)s
                                    ''',
                                    {'status':RAWOUT,'statust':OK,'rootidta':botslib.get_minta4query(),
                                    'tochannel':self.channeldict['idchannel']}):
            try:
                ta_from = botslib.OldTransaction(row['idta'])
                ta_to = ta_from.copyta(status=EXTERNOUT)
                addresslist = [x for x in (row['tomail'],row['cc']) if x]
                sendfile = botslib.opendata(row['filename'], 'rb')
                msg = sendfile.read()
                sendfile.close()
                self.session.sendmail(row['frommail'], addresslist, msg)
            except:
                txt=botslib.txtexc()
                ta_to.update(statust=ERROR,errortext=txt,filename='smtp://'+self.channeldict['username']+'@'+self.channeldict['host'])
            else:
                ta_from.update(statust=DONE)
                ta_to.update(statust=DONE,filename='smtp://'+self.channeldict['username']+'@'+self.channeldict['host'])
                
    def disconnect(self):
        try:    #Google gives/gave error closing connection. Not a real problem.
            self.session.quit()
        except:
            pass

class smtps(smtp):
    def connect(self):
        if hasattr(smtplib,'SMTP_SSL'):
            self.session = smtplib.SMTP_SSL(host=self.channeldict['host'],port=int(self.channeldict['port'])) #make connection
        else:   #smtp_ssl not in standard lib for python<=2.5 for . So I used another module for smtp_ssl. But if in stdlib, use it. 
            import bots.smtpssllib as smtpssllib
            self.session = smtpssllib.SMTP_SSL(host=self.channeldict['host'],port=int(self.channeldict['port'])) #make connection
        self.session.set_debuglevel(botsglobal.ini.getint('settings','smtpdebug',0))    #if used, gives information about session (on screen), for debugging smtp
        self.login()

class smtpstarttls(smtp):
    def connect(self):
        self.session = smtplib.SMTP(host=self.channeldict['host'],port=int(self.channeldict['port'])) #make connection
        self.session.set_debuglevel(botsglobal.ini.getint('settings','smtpdebug',0))    #if used, gives information about session (on screen), for debugging smtp
        self.session.ehlo()
        self.session.starttls()
        self.session.ehlo()
        self.login()


class file(_comsession):
    def connect(self):
        #set up directory-lockfile
        #~ if self.channeldict['inorout'] == 'out':
            #~ raise Exception('test')
        if self.channeldict['lockname']:
            lockname = botslib.join(self.channeldict['path'],self.channeldict['lockname'])
            lock = os.open(lockname,os.O_WRONLY | os.O_CREAT | os.O_EXCL)
            os.close(lock)

    @botslib.log_session
    def incommunicate(self):
        ''' gets files from filesystem. To be used via receive-dispatcher.
            each to be imported file is transaction.
            each imported file is transaction.
            IF error in importing: imported files are either OK or ERROR.
                                    what could not be imported is not removed
        '''
        frompath = botslib.join(self.channeldict['path'],self.channeldict['filename'])
        #fetch messages from filesystem.
        for fromfilename in [c for c in glob.glob(frompath) if os.path.isfile(c)]:
            try:
                ta_from = botslib.NewTransaction(filename=fromfilename,
                                                status=EXTERNIN,
                                                fromchannel=self.channeldict['idchannel'],
                                                charset=self.channeldict['charset'],idroute=self.idroute)
                ta_to =   ta_from.copyta(status=RAWIN)
                #open fromfile, syslock if indicated
                fromfile = open(fromfilename,'rb')
                if self.channeldict['syslock']:
                    if os.name == 'nt':
                        msvcrt.locking(fromfile.fileno(), msvcrt.LK_LOCK, 0x0fffffff)
                    elif os.name == 'posix':
                        fcntl.lockf(fromfile.fileno(), fcntl.LOCK_SH|fcntl.LOCK_NB)
                    else:
                        raise botslib.LockedFileError("Can not do a systemlock on this platform")
                #open tofile
                tofilename = str(ta_to.idta)
                tofile = botslib.opendata(tofilename, 'wb')
                #copy
                shutil.copyfileobj(fromfile,tofile)
                fromfile.close()
                tofile.close()
                if self.channeldict['remove']:
                    os.remove(fromfilename)
            except:
                txt=botslib.txtexc()
                botslib.ErrorProcess(functionname='file-incommunicate',errortext=txt)
                ta_from.delete()
                ta_to.delete()    #is not received
                botsglobal.logger.debug(u'Error reading incoming file "%s".',fromfilename)
            else:
                ta_from.update(statust=DONE)
                ta_to.update(filename=tofilename,statust=OK)
                botsglobal.logger.debug(u'Read incoming file "%s".',fromfilename)
                
    @botslib.log_session
    def outcommunicate(self):
        ''' does output of files to filesystem. To be used via send-dispatcher.
            Output is either:
            1.  1 outputfile, messages are appended; filename is a fixed name
            2.  to directory; new file for each db-ta; if file exits: overwrite. File has to have a unique name.
        '''
        #check if output dir exists, else create it.
        outputdir = botslib.join(self.channeldict['path'])
        botslib.dirshouldbethere(outputdir)
        #output to one file or a queue of files (with unique names)
        if not self.channeldict['filename'] or '*' not in self.channeldict['filename']:
            mode = 'ab'  #fixed filename; not unique: append to file
        else:
            mode = 'wb'  #unique filenames; (over)write
        #select the db-ta's for this channel
        for row in botslib.query(u'''SELECT idta,filename,charset
                                       FROM ta
                                      WHERE idta>%(rootidta)s
                                        AND status=%(status)s
                                        AND statust=%(statust)s
                                        AND tochannel=%(tochannel)s
                                        ''',
                                    {'tochannel':self.channeldict['idchannel'],'rootidta':botslib.get_minta4query(),
                                    'status':RAWOUT,'statust':OK}):
            try:    #for each db-ta:
                ta_from = botslib.OldTransaction(row['idta'])
                ta_to =   ta_from.copyta(status=EXTERNOUT)
                botslib.checkcodeciscompatible(row['charset'],self.channeldict['charset'])
                #open tofile, incl syslock if indicated
                unique = str(botslib.unique(self.channeldict['idchannel'])) #create unique part for filename
                if self.channeldict['filename']:
                    filename = self.channeldict['filename'].replace('*',unique) #filename is filename in channel where '*' is replaced by idta
                else:
                    filename = unique
                if self.userscript and hasattr(self.userscript,'filename'):
                    filename = botslib.runscript(self.userscript,self.scriptname,'filename',channeldict=self.channeldict,filename=filename,ta=ta_from)
                tofilename = botslib.join(outputdir,filename)
                tofile = open(tofilename, mode)
                #~ raise Exception('test')  #for testing
                if self.channeldict['syslock']:
                    if os.name == 'nt':
                        msvcrt.locking(tofile.fileno(), msvcrt.LK_LOCK, 0x0fffffff)
                    elif os.name == 'posix':
                        fcntl.lockf(tofile.fileno(), fcntl.LOCK_EX|fcntl.LOCK_NB)
                    else:
                        raise botslib.LockedFileError(_('Can not do a systemlock on this platform'))
                #open fromfile
                fromfile = botslib.opendata(row['filename'], 'rb')
                #copy
                shutil.copyfileobj(fromfile,tofile)
                fromfile.close()
                tofile.close()
            except:
                txt=botslib.txtexc()
                ta_to.update(statust=ERROR,errortext=txt)
            else:
                ta_from.update(statust=DONE)
                ta_to.update(statust=DONE,filename=tofilename)


    def disconnect(self):
        #delete directory-lockfile
        if self.channeldict['lockname']:
            os.remove(lockname)


class mimefile(file):
    @botslib.log_session
    def postcommunicate(self,fromstatus,tostatus):
        self.mime2file(fromstatus,tostatus)
    @botslib.log_session
    def precommunicate(self,fromstatus,tostatus):
        return self.file2mime(fromstatus,tostatus)

class ftp(_comsession):
    def connect(self):
        botslib.settimeout(botsglobal.ini.getint('settings','ftptimeout',10))
        self.session = ftplib.FTP()
        self.session.set_debuglevel(botsglobal.ini.getint('settings','ftpdebug',0))   #set debug level (0=no, 1=medium, 2=full debug)
        self.session.set_pasv(not self.channeldict['ftpactive']) #active or passive ftp
        self.session.connect(host=self.channeldict['host'],port=int(self.channeldict['port']))
        self.session.login(user=self.channeldict['username'],passwd=self.channeldict['secret'],acct=self.channeldict['ftpaccount'])
        self.dirpath = self.session.pwd()
        if self.channeldict['path']:
            self.dirpath = posixpath.normpath(posixpath.join(self.dirpath,self.channeldict['path']))
            try:
                self.session.cwd(self.dirpath)           #set right path on ftp-server
            except:
                self.session.mkd(self.dirpath)           #set right path on ftp-server; no nested directories
                self.session.cwd(self.dirpath)           #set right path on ftp-server

    @botslib.log_session
    def incommunicate(self):
        ''' do ftp: receive files. To be used via receive-dispatcher.
            each to be imported file is transaction.
            each imported file is transaction.
        '''
        #'ls' to ftp-server; filter this list
        #~ lijst = fnmatch.filter(self.session.nlst(),self.channeldict['filename'])
        files = []
        try:
            files = self.session.nlst()
        except (ftplib.error_perm,ftplib.error_temp),resp:
            resp = str(resp).strip(' \t.').lower()  #'normalise' error
            if resp not in ['550 no files found','450 no files found']:     #some ftp servers give errors when directory is empty. here these errors are catched
                raise
        lijst = fnmatch.filter(files,self.channeldict['filename'])
        for fromfilename in lijst:  #fetch messages from ftp-server.
            try:
                ta_from = botslib.NewTransaction(filename='ftp:/'+posixpath.join(self.dirpath,fromfilename),
                                                    status=EXTERNIN,
                                                    fromchannel=self.channeldict['idchannel'],
                                                    charset=self.channeldict['charset'],idroute=self.idroute)
                ta_to =   ta_from.copyta(status=RAWIN)
                tofilename = str(ta_to.idta)
                if self.channeldict['ftpbinary']:
                    tofile = botslib.opendata(tofilename, 'wb')
                    self.session.retrbinary("RETR " + fromfilename, tofile.write)
                else:
                    tofile = botslib.opendata(tofilename, 'w')
                    self.session.retrlines("RETR " + fromfilename, lambda s, w=tofile.write: w(s+"\n"))
                tofile.close()
                if self.channeldict['remove']:
                    self.session.delete(fromfilename)
            except:
                txt=botslib.txtexc()
                botslib.ErrorProcess(functionname='ftp-incommunicate',errortext=txt)
                #~ ta_from.update(statust=ERROR,errortext=txt)  #this has the big advantage it will be retried again!
                ta_from.delete()
                ta_to.delete()    #is not received
            else:
                ta_from.update(statust=DONE)
                ta_to.update(filename=tofilename,statust=OK)
        
    @botslib.log_session
    def outcommunicate(self):
        ''' do ftp: send files. To be used via receive-dispatcher.
            each to be send file is transaction.
            each send file is transaction.
            NB: ftp command APPE should be supported by server
        '''
        #check if one file or queue of files with unique names
        if not self.channeldict['filename'] or '*'not in self.channeldict['filename']:
            mode = 'APPE '  #fixed filename; not unique: append to file
        else:
            mode = 'STOR '  #unique filenames; (over)write
        for row in botslib.query('''SELECT idta,filename,charset
                                    FROM ta
                                    WHERE idta>%(rootidta)s
                                      AND status=%(status)s
                                      AND statust=%(statust)s
                                      AND tochannel=%(tochannel)s
                                        ''',
                                    {'tochannel':self.channeldict['idchannel'],'rootidta':botslib.get_minta4query(),
                                    'status':RAWOUT,'statust':OK}):
            try:
                ta_from = botslib.OldTransaction(row['idta'])
                ta_to = ta_from.copyta(status=EXTERNOUT)
                unique = str(botslib.unique(self.channeldict['idchannel'])) #create unique part for filename
                if self.channeldict['filename']:
                    tofilename = self.channeldict['filename'].replace('*',unique) #filename is filename in channel where '*' is replaced by idta
                else:
                    tofilename = unique
                if self.userscript and hasattr(self.userscript,'filename'):
                    tofilename = botslib.runscript(self.userscript,self.scriptname,'filename',channeldict=self.channeldict,filename=tofilename,ta=ta_from)
                if self.channeldict['ftpbinary']:
                    botslib.checkcodeciscompatible(row['charset'],self.channeldict['charset'])
                    fromfile = botslib.opendata(row['filename'], 'rb')
                    self.session.storbinary(mode + tofilename, fromfile)
                else:
                    #~ self.channeldict['charset'] = 'us-ascii'
                    botslib.checkcodeciscompatible(row['charset'],self.channeldict['charset'])
                    fromfile = botslib.opendata(row['filename'], 'r')
                    self.session.storlines(mode + tofilename, fromfile)
                fromfile.close()
            except:
                txt=botslib.txtexc()
                ta_to.update(statust=ERROR,errortext=txt,filename='ftp:/'+posixpath.join(self.dirpath,tofilename))
            else:
                ta_from.update(statust=DONE)
                ta_to.update(statust=DONE,filename='ftp:/'+posixpath.join(self.dirpath,tofilename))

    def disconnect(self):
        try:
            self.session.quit()
        except:
            self.session.close()
        botslib.settimeout(botsglobal.ini.getint('settings','globaltimeout',10))
        
class ftps(ftp):
    def connect(self):
        botslib.settimeout(botsglobal.ini.getint('settings','ftptimeout',10))
        if not hasattr(ftplib,'FTP_TLS'):
            raise botslib.CommunicationError('FTPS is not supported by your python version, use >=2.7')
        self.session = ftplib.FTP_TLS()
        self.session.set_debuglevel(botsglobal.ini.getint('settings','ftpdebug',0))   #set debug level (0=no, 1=medium, 2=full debug)
        self.session.set_pasv(not self.channeldict['ftpactive']) #active or passive ftp
        self.session.connect(host=self.channeldict['host'],port=int(self.channeldict['port']))
        #support key files (PEM, cert)?
        self.session.auth()
        self.session.login(user=self.channeldict['username'],passwd=self.channeldict['secret'],acct=self.channeldict['ftpaccount'])
        self.session.prot_p()
        self.dirpath = self.session.pwd()
        if self.channeldict['path']:
            self.dirpath = posixpath.normpath(posixpath.join(self.dirpath,self.channeldict['path']))
            try:
                self.session.cwd(self.dirpath)           #set right path on ftp-server
            except:
                self.session.mkd(self.dirpath)           #set right path on ftp-server; no nested directories
                self.session.cwd(self.dirpath)           #set right path on ftp-server

class sftp(_comsession):
    # for sftp channel type, requires paramiko and pycrypto to be installed
    # based on class ftp and ftps above with code from demo_sftp.py which is included with paramiko
    # Mike Griffin 16/10/2010
    def connect(self):
        # check dependencies
        try:
            import paramiko
            from Crypto import Cipher
        except:
            raise botslib.CommunicationError('Dependency failure: communicationtype "sftp" requires "paramiko" and "pycrypto". Please install these python libraries first.')
        # setup logging if required
        ftpdebug = botsglobal.ini.getint('settings','ftpdebug',0)
        if ftpdebug > 0:
            log_file = botslib.join(botsglobal.ini.get('directories','logging'),'sftp.log')
            # Convert ftpdebug to paramiko logging level (1=20=info, 2=10=debug)
            paramiko.util.log_to_file(log_file, 30-(ftpdebug*10))

        # Get hostname and port to use
        hostname = self.channeldict['host']
        try:
            port = int(self.channeldict['port'])
        except:
            port = 22 # default port for sftp

        # get host key, if we know one
        # (I have not tested this, just copied from demo)
        hostkeytype = None
        hostkey = None
        try:
            host_keys = paramiko.util.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))
        except IOError:
            try: # try ~/ssh/ too, because windows can't have a folder named ~/.ssh/
                host_keys = paramiko.util.load_host_keys(os.path.expanduser('~/ssh/known_hosts'))
            except IOError:
                host_keys = {}
                botsglobal.logger.debug(u'No host keys found for sftp')
        if host_keys.has_key(hostname):
            hostkeytype = host_keys[hostname].keys()[0]
            hostkey = host_keys[hostname][hostkeytype]
            botsglobal.logger.debug(u'Using host key of type "%s" for sftp',hostkeytype)

        # now, connect and use paramiko Transport to negotiate SSH2 across the connection
        transport = paramiko.Transport((hostname,port))
        transport.connect(username=self.channeldict['username'],password=self.channeldict['secret'],hostkey=hostkey)
        self.session = paramiko.SFTPClient.from_transport(transport)
        channel = self.session.get_channel()
        channel.settimeout(botsglobal.ini.getint('settings','ftptimeout',10))

        self.session.chdir('.') # getcwd does not work without this chdir first!
        self.dirpath = self.session.getcwd()

        #set right path on ftp-server
        if self.channeldict['path']:
            self.dirpath = posixpath.normpath(posixpath.join(self.dirpath,self.channeldict['path']))
            try:
                self.session.chdir(self.dirpath)
            except:
                self.session.mkdir(self.dirpath)
                self.session.chdir(self.dirpath)

    def disconnect(self):
        self.session.close()

    @botslib.log_session
    def incommunicate(self):
        ''' do ftp: receive files. To be used via receive-dispatcher.
            each to be imported file is transaction.
            each imported file is transaction.
        '''
        files = []
        try:
            files = self.session.listdir('.')
        except:
            raise
        lijst = fnmatch.filter(files,self.channeldict['filename'])
        for fromfilename in lijst:  #fetch messages from sftp-server.
            try:
                ta_from = botslib.NewTransaction(filename='ftp:/'+posixpath.join(self.dirpath,fromfilename),
                                                    status=EXTERNIN,
                                                    fromchannel=self.channeldict['idchannel'],
                                                    charset=self.channeldict['charset'],idroute=self.idroute)
                ta_to =   ta_from.copyta(status=RAWIN)
                tofilename = str(ta_to.idta)

                # SSH treats all files as binary
                tofile = botslib.opendata(tofilename, 'wb')
                tofile.write(self.session.open(fromfilename, 'r').read())
                tofile.close()

                if self.channeldict['remove']:
                    self.session.remove(fromfilename)
            except:
                txt=botslib.txtexc()
                botslib.ErrorProcess(functionname='sftp-incommunicate',errortext=txt)
                ta_from.delete()
                ta_to.delete()    #is not received
            else:
                ta_from.update(statust=DONE)
                ta_to.update(filename=tofilename,statust=OK)

    @botslib.log_session
    def outcommunicate(self):
        ''' do ftp: send files. To be used via receive-dispatcher.
            each to be send file is transaction.
            each send file is transaction.
        '''
        #check if one file or queue of files with unique names
        if not self.channeldict['filename'] or '*'not in self.channeldict['filename']:
            mode = 'a'  #fixed filename; not unique: append to file
        else:
            mode = 'w'  #unique filenames; (over)write
        for row in botslib.query('''SELECT idta,filename,charset
                                    FROM ta
                                    WHERE idta>%(rootidta)s
                                      AND status=%(status)s
                                      AND statust=%(statust)s
                                      AND tochannel=%(tochannel)s
                                        ''',
                                    {'tochannel':self.channeldict['idchannel'],'rootidta':botslib.get_minta4query(),
                                    'status':RAWOUT,'statust':OK}):
            try:
                ta_from = botslib.OldTransaction(row['idta'])
                ta_to = ta_from.copyta(status=EXTERNOUT)
                unique = str(botslib.unique(self.channeldict['idchannel'])) #create unique part for filename
                if self.channeldict['filename']:
                    tofilename = self.channeldict['filename'].replace('*',unique) #filename is filename in channel where '*' is replaced by idta
                else:
                    tofilename = unique
                if self.userscript and hasattr(self.userscript,'filename'):
                    tofilename = botslib.runscript(self.userscript,self.scriptname,'filename',channeldict=self.channeldict,filename=tofilename,ta=ta_from)

                # SSH treats all files as binary
                botslib.checkcodeciscompatible(row['charset'],self.channeldict['charset'])
                fromfile = botslib.opendata(row['filename'], 'rb')
                self.session.open(tofilename, mode).write(fromfile.read())
                fromfile.close()

            except:
                txt=botslib.txtexc()
                ta_to.update(statust=ERROR,errortext=txt,filename='sftp:/'+posixpath.join(self.dirpath,tofilename))
            else:
                ta_from.update(statust=DONE)
                ta_to.update(statust=DONE,filename='sftp:/'+posixpath.join(self.dirpath,tofilename))


class xmlrpc(_comsession):
    scheme = 'http'
    def connect(self):
        self.uri = botslib.Uri(scheme=self.scheme,username=self.channeldict['username'],password=self.channeldict['secret'],host=self.channeldict['host'],port=self.channeldict['port'],path=self.channeldict['path'])
        self.session = xmlrpclib.ServerProxy(self.uri.uri)


    @botslib.log_session
    def outcommunicate(self):
        ''' do xml-rpc: send files. To be used via receive-dispatcher.
            each to be send file is transaction.
            each send file is transaction.
        '''
        for row in botslib.query('''SELECT idta,filename,charset
                                    FROM ta
                                    WHERE tochannel=%(tochannel)s
                                      AND status=%(status)s
                                      AND statust=%(statust)s
                                      AND idta>%(rootidta)s
                                        ''',
                                    {'tochannel':self.channeldict['idchannel'],'rootidta':botslib.get_minta4query(),
                                    'status':RAWOUT,'statust':OK}):
            try:
                ta_from = botslib.OldTransaction(row['idta'])
                ta_to =   ta_from.copyta(status=EXTERNOUT)
                botslib.checkcodeciscompatible(row['charset'],self.channeldict['charset'])
                fromfile = botslib.opendata(row['fromfilename'], 'rb',row['charset'])
                content = fromfile.read()
                fromfile.close()
                tocall = getattr(self.session,self.channeldict['filename'])
                filename = tocall(content)
            except:
                txt=botslib.txtexc()
                ta_to.update(statust=ERROR,errortext=txt)
            else:
                ta_from.update(statust=DONE)
                ta_to.update(statust=DONE,filename=self.uri.update(path=self.channeldict['path'],filename=str(filename)))


    @botslib.log_session
    def incommunicate(self):
        while (True):
            try:
                tocall = getattr(self.session,self.channeldict['path'])
                content = tocall()
                if content is None:
                    break   #nothing (more) to receive.
                ta_from = botslib.NewTransaction(filename=self.uri.update(path=self.channeldict['path'],filename=self.channeldict['filename']),
                                                    status=EXTERNIN,
                                                    fromchannel=self.channeldict['idchannel'],
                                                    charset=self.channeldict['charset'],idroute=self.idroute)
                ta_to =   ta_from.copyta(status=RAWIN)
                tofilename = str(ta_to.idta)
                tofile = botslib.opendata(tofilename, 'wb')
                simplejson.dump(content, tofile, skipkeys=False, ensure_ascii=False, check_circular=False)
                tofile.close()
            except:
                txt=botslib.txtexc()
                botslib.ErrorProcess(functionname='xmlprc-incommunicate',errortext=txt)
                ta_from.delete()
                ta_to.delete()    #is not received
            else:
                ta_from.update(statust=DONE)
                ta_to.update(filename=tofilename,statust=OK)


class intercommit(_comsession):
    def connect(self):
        #TODO: check if intercommit program is installed/reachable
        pass
        
    @botslib.log_session
    def incommunicate(self):
        botslib.runexternprogram(botsglobal.ini.get('intercommit','path'), '-R')
        frompath = botslib.join(self.channeldict['path'],self.channeldict['filename'])
        for fromheadername in [c for c in glob.glob(frompath) if os.path.isfile(c)]:    #get intercommit xml-header
            try:
                #open  db-ta's
                ta_from = botslib.NewTransaction(filename=fromheadername,
                                                status=EXTERNIN,
                                                fromchannel=self.channeldict['idchannel'],
                                                charset=self.channeldict['charset'],
                                                idroute=self.idroute)
                ta_to = ta_from.copyta(status=RAWIN)
                #parse the intercommit 'header'-file (named *.edi)
                self.parsestuurbestand(filename=fromheadername,charset=self.channeldict['charset'])
                #convert parameters (mail-addresses to partners-ID's; flename)
                self.p['frompartner'] = self.mailaddress2idpartner(self.p['frommail'])
                self.p['topartner'] =  self.mailaddress2idpartner(self.p['tomail'])
                fromfilename = botslib.join(self.channeldict['path'],self.p['Attachment'])
                self.p['filename'] = str(ta_to.idta)
                #read/write files (xml=header is already done
                fromfile = open(fromfilename,'rb')
                tofile = botslib.opendata(self.p['filename'], 'wb')
                shutil.copyfileobj(fromfile,tofile)
                fromfile.close()
                tofile.close()
                if self.channeldict['remove']:
                    os.remove(fromfilename)
                    os.remove(fromheadername)
            except:
                txt=botslib.txtexc()
                ta_from.update(statust=ERROR,errortext=txt,filename=fromfilename)
                ta_to.delete()
            else:
                ta_from.update(statust=DONE,filename=fromfilename)
                ta_to.update(statust=OK,**self.p)

    def parsestuurbestand(self,filename,charset):
        self.p = {}
        edifile = inmessage.edifromfile(filename=filename,messagetype='intercommitenvelope',editype='xml',charset=charset)
        for inn in edifile.nextmessage():
            break
        self.p['frommail'] = inn.get({'BOTSID':'Edicon'},{'BOTSID':'Header'},{'BOTSID':'From','BOTSCONTENT':None})
        self.p['tomail'] = inn.get({'BOTSID':'Edicon'},{'BOTSID':'Header'},{'BOTSID':'To','BOTSCONTENT':None})
        self.p['reference'] = inn.get({'BOTSID':'Edicon'},{'BOTSID':'Header'},{'BOTSID':'X-ClientMsgID','BOTSCONTENT':None})
        self.p['Subject'] = inn.get({'BOTSID':'Edicon'},{'BOTSID':'Header'},{'BOTSID':'Subject','BOTSCONTENT':None})
        self.p['Attachment'] = inn.get({'BOTSID':'Edicon'},{'BOTSID':'Body'},{'BOTSID':'Attachment','BOTSCONTENT':None})

    @botslib.log_session
    def outcommunicate(self):
        #check if output dir exists, else create it.
        dirforintercommitsend = botslib.join(self.channeldict['path'])
        botslib.dirshouldbethere(dirforintercommitsend)
        #output to one file or a queue of files (with unique names)
        if not self.channeldict['filename'] or '*'not in self.channeldict['filename']:
            raise botslib.CommunicationOutError(_(u'channel "$channel" needs unique filenames (no queue-file); use eg *.edi as value for "filename"'),channel=self.channeldict['idchannel'])
        else:
            mode = 'wb'  #unique filenames; (over)write
        #select the db-ta's for this channel
        for row in botslib.query('''SELECT idta,filename,frompartner,topartner,charset
                                    FROM  ta
                                    WHERE idta>%(rootidta)s
                                    AND   status=%(status)s
                                    AND   statust=%(statust)s
                                    AND   tochannel=%(idchannel)s
                                    AND   idroute=%(idroute)s
                                    ''',
                                    {'idchannel':self.channeldict['idchannel'],'rootidta':botslib.get_minta4query(),
                                    'status':RAWOUT,'statust':OK,'idroute':self.idroute}):
            try:    #for each db-ta:
                ta_attr={}    #ta_attr contains attributes used for updating ta
                ta_from = botslib.OldTransaction(row['idta'])
                ta_to =   ta_from.copyta(status=EXTERNOUT)
                #check encoding for outchannel
                botslib.checkcodeciscompatible(row['charset'],self.channeldict['charset'])
                #create unique for filenames of xml-header file and contentfile
                uniquepart = str(botslib.unique(self.channeldict['idchannel'])) #create unique part for fielanmes
                statusfilename = self.channeldict['filename'].replace('*',uniquepart) #filename is filename in channel where '*' is replaced by idta
                statusfilenamewithpath = botslib.join(dirforintercommitsend,statusfilename)
                (filenamewithoutext,ext)=os.path.splitext(statusfilename)
                datafilename = filenamewithoutext + '.dat'
                ta_attr['filename'] = botslib.join(dirforintercommitsend,datafilename)
                ta_attr['frompartner'],nep = self.idpartner2mailaddress(row['frompartner'])
                ta_attr['topartner'],nep = self.idpartner2mailaddress(row['topartner'])
                ta_attr['reference'] = email.Utils.make_msgid(str(row['idta']))[1:-1]  #[1:-1]: strip angle brackets
                #create xml-headerfile
                out = outmessage.outmessage_init(messagetype='intercommitenvelope',editype='xml',filename=statusfilenamewithpath)    #make outmessage object
                out.put({'BOTSID':'Edicon'},{'BOTSID':'Header'},{'BOTSID':'From','BOTSCONTENT':ta_attr['frompartner']})
                out.put({'BOTSID':'Edicon'},{'BOTSID':'Header'},{'BOTSID':'To','BOTSCONTENT':ta_attr['topartner']})
                out.put({'BOTSID':'Edicon'},{'BOTSID':'Header'},{'BOTSID':'Subject','BOTSCONTENT':ta_attr['reference']})
                out.put({'BOTSID':'Edicon'},{'BOTSID':'Body'},{'BOTSID':'Attachment','Type':'external','BOTSCONTENT':datafilename})
                out.put({'BOTSID':'Edicon'},{'BOTSID':'Header'},{'BOTSID':'X-mtype','BOTSCONTENT':'EDI'})
                out.writeall()   #write tomessage (result of translation)
                #read/write datafiles
                tofile = open(ta_attr['filename'], mode)
                fromfile = open(row['filename'], 'rb')
                shutil.copyfileobj(fromfile,tofile)
                fromfile.close()
                tofile.close()
            except:
                txt=botslib.txtexc()
                ta_to.update(statust=ERROR,errortext=txt)
            else:
                ta_from.update(statust=DONE)
                ta_to.update(statust=DONE,**ta_attr)
        botslib.runexternprogram(botsglobal.ini.get('intercommit','path'),'-s')

    def disconnect(self):
        statusfilenaam = botslib.join(botsglobal.ini.get('intercommit','logfile'))
        edifile = inmessage.edifromfile(filename=statusfilenaam,messagetype='intercommitstatus',editype='csv',charset='utf-8')
        for inn in edifile.nextmessage():
            for inline in inn.getloop({'BOTSID':'regel'}):
                statuse = int(inline.get({'BOTSID':'regel','Berichtstatus':None}))
                ICID = inline.get({'BOTSID':'regel','X-ClientMsgID':None})
                if statuse==2:
                    subject = inline.get({'BOTSID':'regel','Onderwerp':None})
                    botslib.change(u'''UPDATE ta
                                       SET statuse=%(statuse)s, reference=%(newref)s
                                       WHERE reference = %(oldref)s
                                       AND status=%(status)s''',
                                       {'status':EXTERNOUT,'oldref':subject,'newref':ICID,'statuse':statuse})
                else:
                    botslib.change(u'''UPDATE ta
                                       SET statuse=%(statuse)s
                                       WHERE reference = %(reference)s
                                       AND status=%(status)s''',
                                       {'status':EXTERNOUT,'reference':ICID,'statuse':statuse})
        os.remove(statusfilenaam)


class database(_comsession):
    ''' this class is obsolete and only heere for compatibility reasons.
        this calls is repalced by class db
        communicate with a database; directly read or write from a database.
        the user HAS to provide a script that does the actual import/export using SQLalchemy API.
        use of channel parameters:
        - path: contains the connection string (a sqlachlemy db uri)
        - idchannel: name user script that does the database query & data formatting. in usersys/dbconnectors. ' main' function is called.
        incommunicate (read from database) expects a json object. In the mapping script this is presented the usual way - use inn.get() etc.
        outcommunicate (write to database) gets a json object.
    '''
    def connect(self):
        botsglobal.logger.debug(u'(try) to read user databasescript channel "%s".',self.channeldict['idchannel'])
        self.dbscript,self.dbscriptname = botslib.botsimport('dbconnectors',self.channeldict['idchannel']) #get the dbconnector-script
        if not hasattr(self.dbscript,'main'):
            raise botslib.ScriptImportError(_(u'No function "$function" in imported script "$script".'),function='main',script=self.dbscript)
        
        import sqlalchemy
        from sqlalchemy.orm import sessionmaker
        engine = sqlalchemy.create_engine(self.channeldict['path'],strategy='threadlocal') 
        self.metadata = sqlalchemy.MetaData()
        self.metadata.bind = engine
        Session = sessionmaker(bind=engine, autoflush=False, transactional=True)
        self.session = Session()

    @botslib.log_session
    def incommunicate(self):
        ''' read data from database.
        '''
        jsonobject = botslib.runscript(self.dbscript,self.dbscriptname,'main',channeldict=self.channeldict,session=self.session,metadata=self.metadata)
        self.session.flush()
        self.session.commit()
        #shoudl I check here more elaborate if jsonobject has 'real' data?
        if jsonobject:
            ta_from = botslib.NewTransaction(filename=self.channeldict['path'],
                                                status=EXTERNIN,
                                                fromchannel=self.channeldict['idchannel'],
                                                charset=self.channeldict['charset'],idroute=self.idroute)
            ta_to =   ta_from.copyta(status=RAWIN)
            tofilename = str(ta_to.idta)
            tofile = botslib.opendata(tofilename,'wb',charset=u'utf-8')
            simplejson.dump(jsonobject, tofile, skipkeys=False, ensure_ascii=False, check_circular=False)
            tofile.close()
            ta_from.update(statust=DONE)
            ta_to.update(filename=tofilename,statust=OK)

    @botslib.log_session
    def outcommunicate(self):
        ''' write data to database.
        '''
        for row in botslib.query('''SELECT idta,filename
                                    FROM  ta
                                    WHERE idta>%(rootidta)s
                                        AND status=%(status)s
                                        AND statust=%(statust)s
                                        AND tochannel=%(tochannel)s
                                        ''',
                                    {'tochannel':self.channeldict['idchannel'],'rootidta':botslib.get_minta4query(),
                                    'status':RAWOUT,'statust':OK}):
            try:
                ta_from = botslib.OldTransaction(row['idta'])
                ta_to = ta_from.copyta(status=EXTERNOUT)
                fromfile = botslib.opendata(row['filename'], 'rb',charset=u'utf-8')
                jsonobject = simplejson.load(fromfile)
                fromfile.close()
                botslib.runscript(self.dbscript,self.dbscriptname,'main',channeldict=self.channeldict,session=self.session,metadata=self.metadata,content=jsonobject)
                self.session.flush()
                self.session.commit()
            except:
                self.session.rollback()
                txt=botslib.txtexc()
                ta_to.update(statust=ERROR,errortext=txt,filename=self.channeldict['path'])
            else:
                ta_from.update(statust=DONE)
                ta_to.update(statust=DONE,filename=self.channeldict['path'])
        
    def disconnect(self):
        self.session.close()
        #~ pass

class db(_comsession):
    ''' communicate with a database; directly read or write from a database.
        the user HAS to provide a script file in usersys/communicationscripts that does the actual import/export using **some** python database library.
        Other parameters are passed, use them for your own convenience.
        Bots 'pickles' the results returned from the user scripts.
    '''
    def connect(self):
        botsglobal.logger.debug(u'(try) to read user databasescript channel "%s".',self.channeldict['idchannel'])
        self.dbscript,self.dbscriptname = botslib.botsimport('communicationscripts',self.channeldict['idchannel']) #get the dbconnector-script
        if not hasattr(self.dbscript,'connect'):
            raise botslib.ScriptImportError(_(u'No function "$function" in imported script "$script".'),function='connect',script=self.dbscript)
        if self.channeldict['inorout']=='in' and not hasattr(self.dbscript,'incommunicate'):
            raise botslib.ScriptImportError(_(u'No function "$function" in imported script "$script".'),function='incommunicate',script=self.dbscript)
        if self.channeldict['inorout']=='out' and not hasattr(self.dbscript,'outcommunicate'):
            raise botslib.ScriptImportError(_(u'No function "$function" in imported script "$script".'),function='outcommunicate',script=self.dbscript)
        if not hasattr(self.dbscript,'disconnect'):
            raise botslib.ScriptImportError(_(u'No function "$function" in imported script "$script".'),function='disconnect',script=self.dbscript)
            
        self.dbconnection = botslib.runscript(self.dbscript,self.dbscriptname,'connect',channeldict=self.channeldict)

    @botslib.log_session
    def incommunicate(self):
        ''' read data from database.
            returns db_objects;
            if this is None, do nothing
            if this is a list, treat each member of the list as a seperate 'message'
        '''
        db_objects = botslib.runscript(self.dbscript,self.dbscriptname,'incommunicate',channeldict=self.channeldict,dbconnection=self.dbconnection)
        if not db_objects:
            return
        if not isinstance(db_objects,list):
            db_objects = [db_objects]
        
        for db_object in db_objects:
            ta_from = botslib.NewTransaction(filename=self.channeldict['path'],
                                                status=EXTERNIN,
                                                fromchannel=self.channeldict['idchannel'],
                                                charset=self.channeldict['charset'],
                                                idroute=self.idroute)
            ta_to = ta_from.copyta(status=RAWIN)
            tofilename = str(ta_to.idta)
            tofile = botslib.opendata(tofilename,'wb')
            pickle.dump(db_object, tofile,2)
            tofile.close()
            ta_from.update(statust=DONE)
            ta_to.update(filename=tofilename,statust=OK)

    @botslib.log_session
    def outcommunicate(self):
        ''' write data to database.
        '''
        for row in botslib.query('''SELECT idta,filename
                                    FROM  ta
                                    WHERE idta>%(rootidta)s
                                        AND status=%(status)s
                                        AND statust=%(statust)s
                                        AND tochannel=%(tochannel)s
                                        ''',
                                    {'tochannel':self.channeldict['idchannel'],'rootidta':botslib.get_minta4query(),
                                    'status':RAWOUT,'statust':OK}):
            try:
                ta_from = botslib.OldTransaction(row['idta'])
                ta_to = ta_from.copyta(status=EXTERNOUT)
                fromfile = botslib.opendata(row['filename'], 'rb')
                db_object = pickle.load(fromfile)
                fromfile.close()
                botslib.runscript(self.dbscript,self.dbscriptname,'outcommunicate',channeldict=self.channeldict,dbconnection=self.dbconnection,db_object=db_object)
            except:
                txt=botslib.txtexc()
                ta_to.update(statust=ERROR,errortext=txt,filename=self.channeldict['path'])
            else:
                ta_from.update(statust=DONE)
                ta_to.update(statust=DONE,filename=self.channeldict['path'])
        
    def disconnect(self):
        botslib.runscript(self.dbscript,self.dbscriptname,'disconnect',channeldict=self.channeldict,dbconnection=self.dbconnection)



class communicationscript(_comsession):
    """
    For running an (user maintained) communcation script. 
    Examples of use:
    - call external communication program or a program that imports data in ERP system
    - communication method not available in Bots
    - specialised I/O wishes; eg specific naming of output files. (eg including partner name)
    place of communcation scripts: bots/usersys/communcationscripts
    name of communcation script: same name as channel (the channelID)
    in this communication script some functions will be called:
    -   connect
    -   main
    -   disconnect
    arguments: dict 'channel' which has all channel attributes
    more parameters/data for communication script:   hard code in communication script; or use bots.ini
    Different ways of working:
    2. communication script processes all edi file in one time. For in: via connect; for out: disconnect
    2. communication script processes edi files one by one. 
        For in: main should be generator; the filename should be yielded/passed back.
        For out: the filename is passed as an argument to main
    'Remove' paramater
    """
    def connect(self):
        if not botslib.tryrunscript(self.userscript,self.scriptname,'connect',channeldict=self.channeldict):
            raise ImportError(u'Channel "$channel" is type "communicationscript", but no communicationscript exists.',channel=self.channeldict['idchannel'])
            
            
    @botslib.log_session
    def incommunicate(self):
        if hasattr(self.userscript,'main'): #process files one by one; script has to be a generator
            for fromfilename in botslib.runscriptyield(self.userscript,self.scriptname,'main',channeldict=self.channeldict):
                try:
                    ta_from = botslib.NewTransaction(filename = fromfilename,
                                                    status = EXTERNIN,
                                                    fromchannel = self.channeldict['idchannel'],
                                                    charset = self.channeldict['charset'], idroute = self.idroute)
                    ta_to = ta_from.copyta(status = RAWIN)
                    fromfile = open(fromfilename, 'rb')
                    tofilename = str(ta_to.idta)
                    tofile = botslib.opendata(tofilename, 'wb')
                    #copy
                    shutil.copyfileobj(fromfile,tofile)
                    fromfile.close()
                    tofile.close()
                    if self.channeldict['remove']:
                        os.remove(fromfilename)
                except:
                    txt=botslib.txtexc()
                    botslib.ErrorProcess(functionname='communicationscript-incommunicate',errortext=txt)
                    #~ ta_from.update(statust=ERROR,errortext=txt)  #this has the big advantage it will be retried again!
                    ta_from.delete()
                    ta_to.delete()    #is not received
                else:
                    ta_from.update(statust=DONE)
                    ta_to.update(filename=tofilename,statust=OK)
        else:   #all files have been set ready by external script using 'connect'.
            frompath = botslib.join(self.channeldict['path'], self.channeldict['filename'])
            for fromfilename in [c for c in glob.glob(frompath) if os.path.isfile(c)]:
                try:
                    ta_from = botslib.NewTransaction(filename = fromfilename,
                                                    status = EXTERNIN,
                                                    fromchannel = self.channeldict['idchannel'],
                                                    charset = self.channeldict['charset'], idroute = self.idroute)
                    ta_to = ta_from.copyta(status = RAWIN)
                    fromfile = open(fromfilename, 'rb')
                    tofilename = str(ta_to.idta)
                    tofile = botslib.opendata(tofilename, 'wb')
                    #copy
                    shutil.copyfileobj(fromfile,tofile)
                    fromfile.close()
                    tofile.close()
                    if self.channeldict['remove']:
                        os.remove(fromfilename)
                except:
                    txt=botslib.txtexc()
                    botslib.ErrorProcess(functionname='communicationscript-incommunicate',errortext=txt)
                    #~ ta_from.update(statust=ERROR,errortext=txt)  #this has the big advantage it will be retried again!
                    ta_from.delete()
                    ta_to.delete()    #is not received
                else:
                    ta_from.update(statust=DONE)
                    ta_to.update(filename=tofilename,statust=OK)

                
    @botslib.log_session
    def outcommunicate(self):
        #check if output dir exists, else create it.
        outputdir = botslib.join(self.channeldict['path'])
        botslib.dirshouldbethere(outputdir)
        #output to one file or a queue of files (with unique names)
        if not self.channeldict['filename'] or '*'not in self.channeldict['filename']:
            mode = 'ab'  #fixed filename; not unique: append to file
        else:
            mode = 'wb'  #unique filenames; (over)write
        #select the db-ta's for this channel
        for row in botslib.query(u'''SELECT idta,filename,charset
                                       FROM ta
                                      WHERE idta>%(rootidta)s
                                        AND status=%(status)s
                                        AND statust=%(statust)s
                                        AND tochannel=%(tochannel)s
                                        ''',
                                    {'tochannel':self.channeldict['idchannel'],'rootidta':botslib.get_minta4query(),
                                    'status':RAWOUT,'statust':OK}):
            try:    #for each db-ta:
                ta_from = botslib.OldTransaction(row['idta'])
                ta_to =   ta_from.copyta(status=EXTERNOUT)
                botslib.checkcodeciscompatible(row['charset'],self.channeldict['charset'])
                #open tofile, incl syslock if indicated
                unique = str(botslib.unique(self.channeldict['idchannel'])) #create unique part for filename
                if self.channeldict['filename']:
                    filename = self.channeldict['filename'].replace('*',unique) #filename is filename in channel where '*' is replaced by idta
                else:
                    filename = unique
                tofilename = botslib.join(outputdir,filename)
                tofile = open(tofilename, mode)
                #open fromfile
                fromfile = botslib.opendata(row['filename'], 'rb')
                #copy
                shutil.copyfileobj(fromfile,tofile)
                fromfile.close()
                tofile.close()
                #one file is written; call external
                if botslib.tryrunscript(self.userscript,self.scriptname,'main',channeldict=self.channeldict,filename=tofilename):
                    if self.channeldict['remove']:
                        os.remove(tofilename)
            except:
                txt=botslib.txtexc()
                ta_to.update(statust=ERROR,errortext=txt)
            else:
                ta_from.update(statust=DONE)
                ta_to.update(statust=DONE,filename=tofilename)

    def disconnect(self):
        botslib.tryrunscript(self.userscript,self.scriptname,'disconnect',channeldict=self.channeldict)
        if self.channeldict['remove'] and not hasattr(self.userscript,'main'):  #if bots should remove the files, and all files are passed at once, delete these files. 
            outputdir = botslib.join(self.channeldict['path'], self.channeldict['filename'])
            for filename in [c for c in glob.glob(outputdir) if os.path.isfile(c)]:
                try:
                    os.remove(filename)
                except:
                    pass
