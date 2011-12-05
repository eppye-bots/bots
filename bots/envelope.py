import shutil
import time
from django.utils.translation import ugettext as _
#bots-modules
import botslib
import botsglobal
import grammar
import outmessage
from botsconfig import *

@botslib.log_session
def mergemessages(startstatus=TRANSLATED,endstatus=MERGED,idroute=''):
    ''' Merges en envelopes several messages to one file;
        In db-ta: attribute 'merge' indicates message should be merged with similar messages; 'merge' is generated in translation from messagetype-grammar
        If merge==False: 1 message per envelope - no merging, else append all similar messages to one file
        Implementation as separate loops: one for merge&envelope, another for enveloping only
        db-ta status TRANSLATED---->MERGED
    '''
    outerqueryparameters = {'status':startstatus,'statust':OK,'idroute':idroute,'rootidta':botslib.get_minta4query(),'merge':False}
    #**********for messages only to envelope (no merging)
    for row in botslib.query(u'''SELECT editype,messagetype,frompartner,topartner,testindicator,charset,contenttype,tochannel,envelope,nrmessages,idta,filename,idroute,merge
                                FROM  ta
                                WHERE   idta>%(rootidta)s
                                AND     status=%(status)s
                                AND     statust=%(statust)s
                                AND     idroute=%(idroute)s
                                AND     merge=%(merge)s
                                ''',
                                outerqueryparameters):
        try:
            ta_info = dict([(key,row[key]) for key in row.keys()])
            #~ ta_info={'merge':False,'idroute':idroute}
            #~ for key in row.keys():
                #~ ta_info[key] = row[key]
            ta_fromfile = botslib.OldTransaction(row['idta'])    #edi message to envelope
            ta_tofile=ta_fromfile.copyta(status=endstatus)  #edifile for enveloped message; attributes of not-enveloped message are copied...
            #~ ta_fromfile.update(child=ta_tofile.idta)        #??there is already a parent-child relation (1-1)...
            ta_info['filename'] = str(ta_tofile.idta)   #create filename for enveloped message
            botsglobal.logger.debug(u'Envelope 1 message editype: %s, messagetype: %s.',ta_info['editype'],ta_info['messagetype'])
            envelope(ta_info,[row['filename']])
        except:
            txt=botslib.txtexc()
            ta_tofile.update(statust=ERROR,errortext=txt)
        else:
            ta_fromfile.update(statust=DONE)
            ta_tofile.update(statust=OK,**ta_info)  #selection is used to update enveloped message;
            
    #**********for messages to merge & envelope
    #all GROUP BY fields must be used in SELECT!
    #as files get merged: can not copy idta; must extract relevant attributes.
    outerqueryparameters['merge']=True
    for row in botslib.query(u'''SELECT editype,messagetype,frompartner,topartner,tochannel,testindicator,charset,contenttype,envelope,sum(nrmessages) as nrmessages
                                FROM  ta
                                WHERE   idta>%(rootidta)s
                                AND     status=%(status)s
                                AND     statust=%(statust)s
                                AND     idroute=%(idroute)s
                                AND     merge=%(merge)s
                                GROUP BY editype,messagetype,frompartner,topartner,tochannel,testindicator,charset,contenttype,envelope
                                ''',
                                outerqueryparameters):
        try:
            ta_info = dict([(key,row[key]) for key in row.keys()])
            ta_info.update({'merge':False,'idroute':idroute})
            #~ for key in row.keys():
                #~ ta_info[key] = row[key]
            ta_tofile=botslib.NewTransaction(status=endstatus,idroute=idroute)  #edifile for enveloped messages
            ta_info['filename'] = str(ta_tofile.idta)                           #create filename for enveloped message
            innerqueryparameters = ta_info.copy()
            innerqueryparameters.update(outerqueryparameters)
            ta_list=[]
            #gather individual idta and filenames
            #explicitly allow formpartner/topartner to be None/NULL
            for row2 in botslib.query(u'''SELECT idta, filename
                                                    FROM ta
                                                    WHERE idta>%(rootidta)s
                                                    AND status=%(status)s
                                                    AND statust=%(statust)s
                                                    AND merge=%(merge)s
                                                    AND editype=%(editype)s
                                                    AND messagetype=%(messagetype)s
                                                    AND (frompartner=%(frompartner)s OR frompartner IS NULL)
                                                    AND (topartner=%(topartner)s OR topartner IS NULL)
                                                    AND tochannel=%(tochannel)s
                                                    AND testindicator=%(testindicator)s
                                                    AND charset=%(charset)s
                                                    AND idroute=%(idroute)s
                                                    ''', 
                                                    innerqueryparameters):
                ta_fromfile = botslib.OldTransaction(row2['idta'])           #edi message to envelope
                ta_fromfile.update(statust=DONE,child=ta_tofile.idta)   #st child because of n->1 relation
                ta_list.append(row2['filename'])
            botsglobal.logger.debug(u'Merge and envelope: editype: %s, messagetype: %s, %s messages',ta_info['editype'],ta_info['messagetype'],ta_info['nrmessages'])
            envelope(ta_info,ta_list)
        except:
            txt=botslib.txtexc()
            ta_tofile.mergefailure()
            ta_tofile.update(statust=ERROR,errortext=txt)
        else:
            ta_tofile.update(statust=OK,**ta_info)


def envelope(ta_info,ta_list):
    ''' dispatch function for class Envelope and subclasses.
        editype, edimessage and envelope essential for enveloping.
        
        determine the class for enveloping:
        1. empty string: no enveloping (class noenvelope); file(s) is/are just copied. No user scripting for envelope.
        2. if envelope is a class in this module, use it
        3. if editype is a class in this module, use it
        4. if user defined enveloping in usersys/envelope/<editype>/<envelope>.<envelope>, use it (user defined scripting overrides)
        
        Always check if user envelope script. user exits extends/replaces default enveloping. 
    '''
    #determine which class to use for enveloping
    userscript = scriptname = None
    if not ta_info['envelope']:     #used when enveloping is just appending files.
        classtocall = noenvelope
    else:
        try:    #see if the is user scripted enveloping
            botsglobal.logger.debug(u'(try) to read user envelopescript editype "%s", envelope "%s".',ta_info['editype'],ta_info['envelope'])
            userscript,scriptname = botslib.botsimport('envelopescripts',ta_info['editype'] + '.' + ta_info['envelope'])
        except ImportError: #other errors, eg syntax errors are just passed
            pass
        #first: check if there is a class with name ta_info['envelope'] in the user scripting
        #this allows complete enveloping in user scripting
        if userscript and hasattr(userscript,ta_info['envelope']):
            classtocall = getattr(userscript,ta_info['envelope'])
        else:
            try:    #check if there is a envelope class with name ta_info['envelope'] in this file (envelope.py)
                classtocall = globals()[ta_info['envelope']]
            except KeyError:
                try:    #check if there is a envelope class with name ta_info['editype'] in this file (envelope.py).
                        #20110919: this should disappear in the long run....use this now for orders2printenvelope and myxmlenvelop
                        #reason to disappear: confusing when setting up. 
                    classtocall = globals()[ta_info['editype']]
                except KeyError:
                    raise botslib.OutMessageError(_(u'Not found envelope "$envelope".'),envelope=ta_info['editype'])
    env = classtocall(ta_info,ta_list,userscript,scriptname)
    env.run()

class Envelope(object):
    ''' Base Class for enveloping; use subclasses.'''
    def __init__(self,ta_info,ta_list,userscript,scriptname):
        self.ta_info = ta_info
        self.ta_list = ta_list
        self.userscript = userscript
        self.scriptname = scriptname

    def _openoutenvelope(self,editype, messagetype_or_envelope):
        ''' make an outmessage object; read the grammar.'''
        #self.ta_info now contains information from ta: editype, messagetype,testindicator,charset,envelope, contenttype
        self.out = outmessage.outmessage_init(**self.ta_info)    #make outmessage object. Init with self.out.ta_info
        #read grammar for envelopesyntax. Remark: self.ta_info is not updated now
        self.out.outmessagegrammarread(editype, messagetype_or_envelope)    
        #self.out.ta_info can contain partner dependent parameters. the partner dependent parameters have overwritten parameters fro mmessage/envelope

    def writefilelist(self,tofile):
        for filename in self.ta_list:
            fromfile = botslib.opendata(filename, 'rb',self.ta_info['charset'])
            shutil.copyfileobj(fromfile,tofile)
            fromfile.close()

    def filelist2absolutepaths(self):
        ''' utility function; some classes need absolute filenames eg for xml-including'''
        return [botslib.abspathdata(filename) for filename in self.ta_list]

class noenvelope(Envelope):
    ''' Only copies the input files to one output file.'''
    def run(self):
        botslib.tryrunscript(self.userscript,self.scriptname,'ta_infocontent',ta_info=self.ta_info)
        tofile = botslib.opendata(self.ta_info['filename'],'wb',self.ta_info['charset'])
        self.writefilelist(tofile)
        tofile.close()

class fixed(noenvelope):
    pass
    
class csv(noenvelope):
    pass
    
class csvheader(Envelope):
    def run(self):
        self._openoutenvelope(self.ta_info['editype'],self.ta_info['messagetype'])
        botslib.tryrunscript(self.userscript,self.scriptname,'ta_infocontent',ta_info=self.ta_info)
        #self.ta_info is not overwritten
        tofile = botslib.opendata(self.ta_info['filename'],'wb',self.ta_info['charset'])
        headers = dict([(field[ID],field[ID]) for field in self.out.defmessage.structure[0][FIELDS]])
        self.out.put(headers)
        self.out.tree2records(self.out.root)
        tofile.write(self.out._record2string(self.out.records[0]))
        self.writefilelist(tofile)
        tofile.close()

class edifact(Envelope):
    ''' Generate UNB and UNZ segment; fill with data, write to interchange-file.'''
    def run(self):
        if not self.ta_info['topartner'] or not self.ta_info['frompartner']:
            raise botslib.OutMessageError(_(u'In enveloping "frompartner" or "topartner" unknown: "$ta_info".'),ta_info=self.ta_info)
            
        self._openoutenvelope(self.ta_info['editype'],self.ta_info['envelope'])
        self.ta_info.update(self.out.ta_info)
        botslib.tryrunscript(self.userscript,self.scriptname,'ta_infocontent',ta_info=self.ta_info)
        
        #version dependent enveloping
        writeUNA = False
        if self.ta_info['version']<'4':
            date = time.strftime('%y%m%d')
            reserve = ' '
            if self.ta_info['charset'] != 'UNOA':
                writeUNA = True
        else:
            date = time.strftime('%Y%m%d')
            reserve = self.ta_info['reserve']
            if self.ta_info['charset'] not in ['UNOA','UNOB']:
                writeUNA = True
        
        #UNB counter is per sender or receiver
        if botsglobal.ini.getboolean('settings','interchangecontrolperpartner',False):
            self.ta_info['reference'] = str(botslib.unique('unbcounter_' + self.ta_info['topartner']))
        else:
            self.ta_info['reference'] = str(botslib.unique('unbcounter_' + self.ta_info['frompartner']))
        
        #testindicator is more complex:
        if self.ta_info['testindicator'] and self.ta_info['testindicator']!='0':    #first check value from ta; do not use default
            testindicator = '1'
        elif self.ta_info['UNB.0035'] != '0':   #than check values from grammar
            testindicator = '1'
        else:
            testindicator = ''
        #build the envelope segments (that is, the tree from which the segments will be generated)
        self.out.put({'BOTSID':'UNB',
                        'S001.0001':self.ta_info['charset'],
                        'S001.0002':self.ta_info['version'],
                        'S002.0004':self.ta_info['frompartner'],
                        'S003.0010':self.ta_info['topartner'],
                        'S004.0017':date,
                        'S004.0019':time.strftime('%H%M'),
                        '0020':self.ta_info['reference']})
        #the following fields are conditional; do not write these when empty string (separator compression does take empty strings into account)
        if self.ta_info['UNB.S002.0007']:
            self.out.put({'BOTSID':'UNB','S002.0007': self.ta_info['UNB.S002.0007']})
        if self.ta_info['UNB.S003.0007']:
            self.out.put({'BOTSID':'UNB','S003.0007': self.ta_info['UNB.S003.0007']})
        if self.ta_info['UNB.0026']:
            self.out.put({'BOTSID':'UNB','0026': self.ta_info['UNB.0026']})
        if testindicator:
            self.out.put({'BOTSID':'UNB','0035': testindicator})
        self.out.put({'BOTSID':'UNB'},{'BOTSID':'UNZ','0036':self.ta_info['nrmessages'],'0020':self.ta_info['reference']})  #dummy segment; is not used
        #user exit
        botslib.tryrunscript(self.userscript,self.scriptname,'envelopecontent',ta_info=self.ta_info,out=self.out)
        #convert the tree into segments; here only the UNB is written (first segment)
        self.out.normalisetree(self.out.root)
        self.out.tree2records(self.out.root)
        
        #start doing the actual writing:
        tofile = botslib.opendata(self.ta_info['filename'],'wb',self.ta_info['charset'])
        if writeUNA or self.ta_info['forceUNA']:
            tofile.write('UNA'+self.ta_info['sfield_sep']+self.ta_info['field_sep']+self.ta_info['decimaal']+self.ta_info['escape']+ reserve +self.ta_info['record_sep']+self.ta_info['add_crlfafterrecord_sep'])
        tofile.write(self.out._record2string(self.out.records[0]))
        self.writefilelist(tofile)
        tofile.write(self.out._record2string(self.out.records[-1]))
        tofile.close()
        if self.ta_info['messagetype'][:6]!='CONTRL' and botslib.checkconfirmrules('ask-edifact-CONTRL',idroute=self.ta_info['idroute'],idchannel=self.ta_info['tochannel'],
                                                                                topartner=self.ta_info['topartner'],frompartner=self.ta_info['frompartner'],
                                                                                editype=self.ta_info['editype'],messagetype=self.ta_info['messagetype']):
            self.ta_info['confirmtype'] = u'ask-edifact-CONTRL'
            self.ta_info['confirmasked'] = True


class tradacoms(Envelope):
    ''' Generate STX and END segment; fill with appropriate data, write to interchange file.'''
    def run(self):
        if not self.ta_info['topartner'] or not self.ta_info['frompartner']:
            raise botslib.OutMessageError(_(u'In enveloping "frompartner" or "topartner" unknown: "$ta_info".'),ta_info=self.ta_info)
        self._openoutenvelope(self.ta_info['editype'],self.ta_info['envelope'])
        self.ta_info.update(self.out.ta_info)
        botslib.tryrunscript(self.userscript,self.scriptname,'ta_infocontent',ta_info=self.ta_info)
        #prepare data for envelope
        if botsglobal.ini.getboolean('settings','interchangecontrolperpartner',False):
            self.ta_info['reference'] = str(botslib.unique('stxcounter_' + self.ta_info['topartner']))
        else:
            self.ta_info['reference'] = str(botslib.unique('stxcounter_' + self.ta_info['frompartner']))
        #build the envelope segments (that is, the tree from which the segments will be generated)
        self.out.put({'BOTSID':'STX',
                        'STDS1':self.ta_info['STX.STDS1'],
                        'STDS2':self.ta_info['STX.STDS2'],
                        'FROM.01':self.ta_info['frompartner'],
                        'UNTO.01':self.ta_info['topartner'],
                        'TRDT.01':time.strftime('%y%m%d'),
                        'TRDT.02':time.strftime('%H%M%S'),
                        'SNRF':self.ta_info['reference']})
        if self.ta_info['STX.FROM.02']:
            self.out.put({'BOTSID':'STX','FROM.02':self.ta_info['STX.FROM.02']})
        if self.ta_info['STX.UNTO.02']:
            self.out.put({'BOTSID':'STX','UNTO.02':self.ta_info['STX.UNTO.02']})
        if self.ta_info['STX.APRF']:
            self.out.put({'BOTSID':'STX','APRF':self.ta_info['STX.APRF']})
        if self.ta_info['STX.PRCD']:
            self.out.put({'BOTSID':'STX','PRCD':self.ta_info['STX.PRCD']})
        self.out.put({'BOTSID':'STX'},{'BOTSID':'END','NMST':self.ta_info['nrmessages']})  #dummy segment; is not used
        #user exit
        botslib.tryrunscript(self.userscript,self.scriptname,'envelopecontent',ta_info=self.ta_info,out=self.out)
        #convert the tree into segments; here only the STX is written (first segment)
        self.out.normalisetree(self.out.root)
        self.out.tree2records(self.out.root)
        
        #start doing the actual writing:
        tofile = botslib.opendata(self.ta_info['filename'],'wb',self.ta_info['charset'])
        tofile.write(self.out._record2string(self.out.records[0]))
        self.writefilelist(tofile)
        tofile.write(self.out._record2string(self.out.records[-1]))
        tofile.close()


class template(Envelope):
    def run(self):
        ''' class for (test) orderprint; delevers a valid html-file.
            Uses a kid-template for the enveloping/merging.
            use kid to write; no envelope grammar is used
        '''
        try:
            import kid
        except:
            txt=botslib.txtexc()
            raise ImportError(_(u'Dependency failure: editype "template" requires python library "kid". Error:\n%s'%txt))
        defmessage = grammar.grammarread(self.ta_info['editype'],self.ta_info['messagetype'])   #needed because we do not know envelope; read syntax for editype/messagetype
        self.ta_info.update(defmessage.syntax)
        botslib.tryrunscript(self.userscript,self.scriptname,'ta_infocontent',ta_info=self.ta_info)
        if not self.ta_info['envelope-template']:
            raise botslib.OutMessageError(_(u'While enveloping in "$editype.$messagetype": syntax option "envelope-template" not filled; is required.'),editype=self.ta_info['editype'],messagetype=self.ta_info['messagetype'])
        templatefile = botslib.abspath('templates',self.ta_info['envelope-template'])
        ta_list = self.filelist2absolutepaths()
        try:
            botsglobal.logger.debug(u'Start writing envelope to file "%s".',self.ta_info['filename'])
            ediprint = kid.Template(file=templatefile, data=ta_list) #init template; pass list with filenames
        except:
            txt=botslib.txtexc()
            raise botslib.OutMessageError(_(u'While enveloping in "$editype.$messagetype", error:\n$txt'),editype=self.ta_info['editype'],messagetype=self.ta_info['messagetype'],txt=txt)
        try:
            f = botslib.opendata(self.ta_info['filename'],'wb')
            ediprint.write(f,
                            encoding=self.ta_info['charset'],
                            output=self.ta_info['output'])
        except:
            txt=botslib.txtexc()
            raise botslib.OutMessageError(_(u'While enveloping in "$editype.$messagetype", error:\n$txt'),editype=self.ta_info['editype'],messagetype=self.ta_info['messagetype'],txt=txt)


class orders2printenvelope(template):
    pass


class x12(Envelope):
    ''' Generate envelope segments; fill with appropriate data, write to interchange-file.'''
    def run(self):
        if not self.ta_info['topartner'] or not self.ta_info['frompartner']:
            raise botslib.OutMessageError(_(u'In enveloping "frompartner" or "topartner" unknown: "$ta_info".'),ta_info=self.ta_info)
        self._openoutenvelope(self.ta_info['editype'],self.ta_info['envelope'])
        self.ta_info.update(self.out.ta_info)
        #need to know the functionalgroup code:
        defmessage = grammar.grammarread(self.ta_info['editype'],self.ta_info['messagetype'])
        self.ta_info['functionalgroup'] = defmessage.syntax['functionalgroup']
        botslib.tryrunscript(self.userscript,self.scriptname,'ta_infocontent',ta_info=self.ta_info)
        #prepare data for envelope
        ISA09date = time.strftime('%y%m%d')
        #test indicator can either be from configuration (self.ta_info['ISA15']) or by mapping (self.ta_info['testindicator'])
        #mapping overrules. 
        if self.ta_info['testindicator'] and self.ta_info['testindicator']!='0':    #'0' is default value (in db)
            testindicator = self.ta_info['testindicator']
        else:
            testindicator = self.ta_info['ISA15']
        #~ print self.ta_info['messagetype'], 'grammar:',self.ta_info['ISA15'],'ta:',self.ta_info['testindicator'],'out:',testindicator
        if botsglobal.ini.getboolean('settings','interchangecontrolperpartner',False):
            self.ta_info['reference'] = str(botslib.unique('isacounter_' + self.ta_info['topartner']))
        else:
            self.ta_info['reference'] = str(botslib.unique('isacounter_' + self.ta_info['frompartner']))
        #ISA06 and GS02 can be different; eg ISA06 is a service provider.
        #ISA06 and GS02 can be in the syntax....
        ISA06 = self.ta_info.get('ISA06',self.ta_info['frompartner'])
        ISA06 = ISA06.ljust(15)    #add spaces; is fixed length
        GS02 = self.ta_info.get('GS02',self.ta_info['frompartner'])
        #also for ISA08 and GS03
        ISA08 = self.ta_info.get('ISA08',self.ta_info['topartner'])
        ISA08 = ISA08.ljust(15)    #add spaces; is fixed length
        GS03 = self.ta_info.get('GS03',self.ta_info['topartner'])
        #build the envelope segments (that is, the tree from which the segments will be generated)
        self.out.put({'BOTSID':'ISA',
                        'ISA01':self.ta_info['ISA01'],
                        'ISA02':self.ta_info['ISA02'],
                        'ISA03':self.ta_info['ISA03'],
                        'ISA04':self.ta_info['ISA04'],
                        'ISA05':self.ta_info['ISA05'],
                        'ISA06':ISA06,
                        'ISA07':self.ta_info['ISA07'],
                        'ISA08':ISA08,
                        'ISA09':ISA09date,
                        'ISA10':time.strftime('%H%M'),
                        'ISA11':self.ta_info['ISA11'],      #if ISA version > 00403, replaced by reprtion separator
                        'ISA12':self.ta_info['version'],
                        'ISA13':self.ta_info['reference'],
                        'ISA14':self.ta_info['ISA14'],
                        'ISA15':testindicator},strip=False)         #MIND: strip=False: ISA fields shoudl not be stripped as it is soemwhat like fixed-length
        self.out.put({'BOTSID':'ISA'},{'BOTSID':'IEA','IEA01':'1','IEA02':self.ta_info['reference']})
        GS08 = self.ta_info['messagetype'][3:]
        if GS08[:6]<'004010':
            GS04date = time.strftime('%y%m%d')
        else:
            GS04date = time.strftime('%Y%m%d')
        self.out.put({'BOTSID':'ISA'},{'BOTSID':'GS',
                                        'GS01':self.ta_info['functionalgroup'],
                                        'GS02':GS02,
                                        'GS03':GS03,
                                        'GS04':GS04date,
                                        'GS05':time.strftime('%H%M'),
                                        'GS06':self.ta_info['reference'],
                                        'GS07':self.ta_info['GS07'],
                                        'GS08':GS08})
        self.out.put({'BOTSID':'ISA'},{'BOTSID':'GS'},{'BOTSID':'GE','GE01':self.ta_info['nrmessages'],'GE02':self.ta_info['reference']})  #dummy segment; is not used
        #user exit
        botslib.tryrunscript(self.userscript,self.scriptname,'envelopecontent',ta_info=self.ta_info,out=self.out)
        #convert the tree into segments; here only the UNB is written (first segment)
        self.out.normalisetree(self.out.root)
        self.out.tree2records(self.out.root)
        #start doing the actual writing:
        tofile = botslib.opendata(self.ta_info['filename'],'wb',self.ta_info['charset'])
        ISAstring = self.out._record2string(self.out.records[0])
        if self.ta_info['version']<'00403':
            ISAstring = ISAstring[:103] + self.ta_info['field_sep']+ self.ta_info['sfield_sep'] + ISAstring[103:] #hack for strange characters at end of ISA; hardcoded
        else:
            ISAstring = ISAstring[:82] +self.ta_info['reserve'] + ISAstring[83:103] + self.ta_info['field_sep']+ self.ta_info['sfield_sep'] + ISAstring[103:] #hack for strange characters at end of ISA; hardcoded
        tofile.write(ISAstring)                                     #write ISA
        tofile.write(self.out._record2string(self.out.records[1]))  #write GS
        self.writefilelist(tofile)
        tofile.write(self.out._record2string(self.out.records[-2])) #write GE
        tofile.write(self.out._record2string(self.out.records[-1])) #write IEA
        tofile.close()
        if self.ta_info['functionalgroup']!='FA' and botslib.checkconfirmrules('ask-x12-997',idroute=self.ta_info['idroute'],idchannel=self.ta_info['tochannel'],
                                                                                topartner=self.ta_info['topartner'],frompartner=self.ta_info['frompartner'],
                                                                                editype=self.ta_info['editype'],messagetype=self.ta_info['messagetype']):
            self.ta_info['confirmtype'] = u'ask-x12-997'
            self.ta_info['confirmasked'] = True


class jsonnocheck(noenvelope):
    pass

class json(noenvelope):
    pass

class xmlnocheck(noenvelope):
    pass

class xml(noenvelope):
    pass


class myxmlenvelop(xml):
    ''' old xml enveloping; name is kept for upward comp. & as example for xml enveloping'''
    def run(self):
        ''' class for (test) xml envelope. There is no standardised XML-envelope!
            writes a new XML-tree; uses places-holders for XML-files to include; real enveloping is done by ElementTree's include'''
        include = '{http://www.w3.org/2001/XInclude}include'
        self._openoutenvelope(self.ta_info['editype'],self.ta_info['envelope'])
        botslib.tryrunscript(self.userscript,self.scriptname,'ta_infocontent',ta_info=self.ta_info)
        #~ self.out.put({'BOTSID':'root','xmlns:xi':"http://www.w3.org/2001/XInclude"})     #works, but attribute is not removed bij ETI.include
        self.out.put({'BOTSID':'root'})     #start filling out-tree
        ta_list = self.filelist2absolutepaths() 
        for filename in ta_list:
            self.out.put({'BOTSID':'root'},{'BOTSID':include,include + '__parse':'xml',include + '__href':filename})
        self.out.envelopewrite(self.out.root)   #'resolves' the included xml files 

class db(Envelope):
    ''' Only copies the input files to one output file.'''
    def run(self):
        botslib.tryrunscript(self.userscript,self.scriptname,'ta_infocontent',ta_info=self.ta_info)
        self.ta_info['filename'] = self.ta_list[0]

class raw(Envelope):
    ''' Only copies the input files to one output file.'''
    def run(self):
        botslib.tryrunscript(self.userscript,self.scriptname,'ta_infocontent',ta_info=self.ta_info)
        self.ta_info['filename'] = self.ta_list[0]
