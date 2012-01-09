import time
import sys
try:
    import cPickle as pickle
except:
    import pickle
import decimal
NODECIMAL = decimal.Decimal(1)
try:
    import cElementTree as ET
    #~ print 'imported cElementTree'
except ImportError:
    try:
        import elementtree.ElementTree as ET
        #~ print 'imported elementtree.ElementTree'
    except ImportError:
        try:
            from xml.etree import cElementTree as ET
            #~ print 'imported xml.etree.cElementTree'
        except ImportError:
            from xml.etree import ElementTree as ET
            #~ print 'imported xml.etree.ElementTree'
#~ print ET.VERSION
try:
    import elementtree.ElementInclude as ETI
except ImportError:
    from xml.etree import ElementInclude as ETI
try:
    import json as simplejson
except ImportError:
    import simplejson
from django.utils.translation import ugettext as _
#bots-modules
import botslib
import botsglobal
import grammar
import message
import node
from botsconfig import *

def outmessage_init(**ta_info):
    ''' dispatch function class Outmessage or subclass
        ta_info: needed is editype, messagetype, filename, charset, merge
    '''
    try:
        classtocall = globals()[ta_info['editype']]
    except KeyError:
        raise botslib.OutMessageError(_(u'Unknown editype for outgoing message: $editype'),editype=ta_info['editype'])
    return classtocall(ta_info)

class Outmessage(message.Message):
    ''' abstract class; represents a outgoing edi message.
        subclassing is necessary for the editype (csv, edi, x12, etc)
        A tree of nodes is build form the mpaths received from put()or putloop(). tree starts at self.root.
        Put() recieves mpaths from mappingscript
        The next algorithm is used to 'map' a mpath into the tree:
            For each part of a mpath: search node in 'current' level of tree
                If part already as a node: 
                    recursively search node-children
                If part not as a node:
                    append new node to tree;
                    recursively append next parts to tree
        After the mapping-script is finished, the resulting tree is converted to records (self.records).
        These records are written to file.
        Structure of self.records:
            list of record;
            record is list of field
            field is dict. Keys in field:
            -   ID       field ID (id within this record). For in-file
            -   VALUE    value, content of field
            -   MPATH    mpath of record, only for first field(=recordID)
            -   LIN     linenr of field in in-file
            -   POS      positionnr within line in in-file
            -   SFIELD   True if subfield (edifact-only)
            first field for record is recordID.
    '''
    def __init__(self,ta_info):
        self.ta_info = ta_info
        self.root = node.Node(record={})         #message tree; build via put()-interface in mapping-script. Initialise with empty dict
        super(Outmessage,self).__init__()

    def outmessagegrammarread(self,editype,messagetype):
        ''' read the grammar for a out-message.
            try to read the topartner dependent grammar syntax.
        ''' 
        self.defmessage = grammar.grammarread(editype,messagetype)
        self.defmessage.display(self.defmessage.structure)
        #~ print 'self.ta_info',self.ta_info
        #~ print 'self.defmessage.syntax',self.defmessage.syntax
        botslib.updateunlessset(self.ta_info,self.defmessage.syntax)    #write values from grammar to self.ta_info - unless these values are already set eg by mapping script
        if self.ta_info['topartner']:   #read syntax-file for partner dependent syntax
            try:
                partnersyntax = grammar.syntaxread('partners',editype,self.ta_info['topartner'])
                self.ta_info.update(partnersyntax.syntax) #partner syntax overrules!
            except ImportError:
                pass        #No partner specific syntax found (is not an error).

    def writeall(self):
        ''' writeall is called for writing all 'real' outmessage objects; but not for envelopes.
            writeall is call from transform.translate()
        '''
        self.outmessagegrammarread(self.ta_info['editype'],self.ta_info['messagetype'])
        self.nrmessagewritten = 0
        if self.root.record:        #root record contains information; write whole tree in one time
            self.multiplewrite = False
            self.normalisetree(self.root)
            self._initwrite()
            self._write(self.root)
            self.nrmessagewritten = 1
            self._closewrite()
        elif not self.root.children:
            raise botslib.OutMessageError(_(u'No outgoing message'))    #then there is nothing to write...
        else:
            self.multiplewrite = True
            for childnode in self.root.children:
                self.normalisetree(childnode)
            self._initwrite()
            for childnode in self.root.children:
                self._write(childnode)
                self.nrmessagewritten += 1
            self._closewrite()

    def _initwrite(self):
        botsglobal.logger.debug(u'Start writing to file "%s".',self.ta_info['filename'])
        self._outstream = botslib.opendata(self.ta_info['filename'],'wb',charset=self.ta_info['charset'],errors=self.ta_info['checkcharsetout'])
        
    def _closewrite(self):
        botsglobal.logger.debug(u'End writing to file "%s".',self.ta_info['filename'])
        self._outstream.close()

    def _write(self,node):
        ''' the write method for most classes.
            tree is serialised to sequential records; records are written to file.
            Classses that write using other libraries (xml, json, template, db) use specific write methods. 
        ''' 
        self.tree2records(node)
        self._records2file()

    def tree2records(self,node):
        self.records = []                   #tree of nodes is flattened to these records
        self._tree2recordscore(node,self.defmessage.structure[0])
        
    def _tree2recordscore(self,node,structure):
        ''' Write tree of nodes to flat records.
            The nodes are already sorted 
        '''
        self._tree2recordfields(node.record,structure)    #write root node->first record
        for childnode in node.children:            #for every node in mpathtree, these are already sorted#SPEED: node.children is already sorted!
            for structure_record in structure[LEVEL]:  #for structure_record of this level in grammar
                if childnode.record['BOTSID'] == structure_record[ID] and childnode.record['BOTSIDnr'] == structure_record[BOTSIDnr]:   #if is is the right node:
                    self._tree2recordscore(childnode,structure_record)         #use rest of index in deeper level

    def _tree2recordfields(self,noderecord,structure_record):
        ''' appends fields in noderecord to (raw)record; use structure_record as guide.
            complex because is is used for: editypes that have compression rules (edifact), var editypes without compression, fixed protocols 
        '''
        buildrecord = []    #the record that is going to be build; list of dicts. Each dict is a field.
        buffer = []
        for grammarfield in structure_record[FIELDS]:       #loop all fields in grammar-definition
            if grammarfield[ISFIELD]:    #if field (no composite)
                if grammarfield[ID] in noderecord  and noderecord[grammarfield[ID]]:      #field exists in outgoing message and has data
                    buildrecord += buffer          #write the buffer to buildrecord
                    buffer=[]                           #clear the buffer
                    buildrecord += [{VALUE:noderecord[grammarfield[ID]],SFIELD:False,FORMATFROMGRAMMAR:grammarfield[FORMAT]}]      #append new field
                else:                                   #there is no data for this field
                    if self.ta_info['stripfield_sep']:
                        buffer += [{VALUE:'',SFIELD:False,FORMATFROMGRAMMAR:grammarfield[FORMAT]}]      #append new empty to buffer;
                    else:
                        value = self._formatfield('',grammarfield,structure_record)  #generate field
                        buildrecord += [{VALUE:value,SFIELD:False,FORMATFROMGRAMMAR:grammarfield[FORMAT]}]                #append new field
            else:  #if composite
                donefirst = False       #used because first subfield in composite is marked as a field (not a subfield).
                subbuffer=[]            #buffer for this composite. 
                subiswritten=False      #check if composite contains data
                for grammarsubfield in grammarfield[SUBFIELDS]:   #loop subfields
                    if grammarsubfield[ID] in noderecord and noderecord[grammarsubfield[ID]]:   #field exists in outgoing message and has data
                        buildrecord += buffer           #write buffer
                        buffer=[]                       #clear buffer
                        buildrecord += subbuffer        #write subbuffer
                        subbuffer=[]                    #clear subbuffer
                        buildrecord += [{VALUE:noderecord[grammarsubfield[ID]],SFIELD:donefirst}]      #append field
                        subiswritten = True    
                    else:
                        if self.ta_info['stripfield_sep']:
                            subbuffer += [{VALUE:'',SFIELD:donefirst}]      #append new empty to buffer;
                        else:
                            value = self._formatfield('',grammarsubfield,structure_record)      #generate & append new field. For eg fixed and csv: all field have to be present
                            subbuffer += [{VALUE:value,SFIELD:donefirst}]      #generate & append new field
                    donefirst = True
                if not subiswritten:    #if composite has no data: write placeholder for composite (stripping is done later)
                    buffer += [{VALUE:'',SFIELD:False}]
        #~ print [buildrecord]
        
        self.records += [buildrecord]
                

    def _formatfield(self,value, grammarfield,record):
        ''' Input: value (as a string) and field definition.
            Some parameters of self.syntax are used: decimaal
            Format is checked and converted (if needed).
            return the formatted value
        '''
        if grammarfield[BFORMAT] == 'A':
            if isinstance(self,fixed):  #check length fields in variable records
                if grammarfield[FORMAT] == 'AR':    #if field format is alfanumeric right aligned
                    value = value.rjust(grammarfield[MINLENGTH])
                else:
                    value = value.ljust(grammarfield[MINLENGTH])    #add spaces (left, because A-field is right aligned)
            valuelength=len(value)
            if valuelength > grammarfield[LENGTH]:
                raise botslib.OutMessageError(_(u'record "$mpath" field "$field" too big (max $max): "$content".'),field=grammarfield[ID],content=value,mpath=record[MPATH],max=grammarfield[LENGTH])
            if valuelength < grammarfield[MINLENGTH]:
                raise botslib.OutMessageError(_(u'record "$mpath" field "$field" too small (min $min): "$content".'),field=grammarfield[ID],content=value,mpath=record[MPATH],min=grammarfield[MINLENGTH])
        elif grammarfield[BFORMAT] == 'D':
            try:
                lenght = len(value)
                if lenght==6:
                    time.strptime(value,'%y%m%d')
                elif lenght==8:
                    time.strptime(value,'%Y%m%d')
                else:
                    raise ValueError(u'To be catched')
            except ValueError:
                raise botslib.OutMessageError(_(u'record "$mpath" field "$field" no valid date: "$content".'),field=grammarfield[ID],content=value,mpath=record[MPATH])
            valuelength=len(value)
            if valuelength > grammarfield[LENGTH]:
                raise botslib.OutMessageError(_(u'record "$mpath" field "$field" too big (max $max): "$content".'),field=grammarfield[ID],content=value,mpath=record[MPATH],max=grammarfield[LENGTH])
            if valuelength < grammarfield[MINLENGTH]:
                raise botslib.OutMessageError(_(u'record "$mpath" field "$field" too small (min $min): "$content".'),field=grammarfield[ID],content=value,mpath=record[MPATH],min=grammarfield[MINLENGTH])
        elif grammarfield[BFORMAT] == 'T':
            try:
                lenght = len(value)
                if lenght==4:
                    time.strptime(value,'%H%M')
                elif lenght==6:
                    time.strptime(value,'%H%M%S')
                else: #lenght==8:     #tsja...just use first part of field
                    raise ValueError(u'To be catched')
            except  ValueError:
                raise botslib.OutMessageError(_(u'record "$mpath" field "$field" no valid time: "$content".'),field=grammarfield[ID],content=value,mpath=record[MPATH])
            valuelength=len(value)
            if valuelength > grammarfield[LENGTH]:
                raise botslib.OutMessageError(_(u'record "$mpath" field "$field" too big (max $max): "$content".'),field=grammarfield[ID],content=value,mpath=record[MPATH],max=grammarfield[LENGTH])
            if valuelength < grammarfield[MINLENGTH]:
                raise botslib.OutMessageError(_(u'record "$mpath" field "$field" too small (min $min): "$content".'),field=grammarfield[ID],content=value,mpath=record[MPATH],min=grammarfield[MINLENGTH])
        else:   #numerics
            if value or isinstance(self,fixed):    #if empty string for non-fixed: just return. Later on, ta_info[stripemptyfield] determines what to do with them
                if not value:   #see last if; if a numerical fixed field has content '' , change this to '0' (init)
                    value='0'
                else:
                    value = value.strip()
                if value[0]=='-':
                    minussign = '-'
                    absvalue = value[1:]
                else:
                    minussign = ''
                    absvalue = value
                digits,decimalsign,decimals = absvalue.partition('.')
                if not digits and not decimals:# and decimalsign:
                    raise botslib.OutMessageError(_(u'record "$mpath" field "$field" numerical format not valid: "$content".'),field=grammarfield[ID],content=value,mpath=record[MPATH])
                if not digits:
                    digits = '0'
                    
                lengthcorrection = 0        #for some formats (if self.ta_info['lengthnumericbare']=True; eg edifact) length is calculated without decimal sing and/or minus sign.
                if grammarfield[BFORMAT] == 'R':    #floating point: use all decimals received
                    if self.ta_info['lengthnumericbare']:
                        if minussign:
                            lengthcorrection += 1
                        if decimalsign:
                            lengthcorrection += 1
                    try:
                        value = str(decimal.Decimal(minussign + digits + decimalsign + decimals).quantize(decimal.Decimal(10) ** -len(decimals)))
                    except:
                        raise botslib.OutMessageError(_(u'record "$mpath" field "$field" numerical format not valid: "$content".'),field=grammarfield[ID],content=value,mpath=record[MPATH])
                    if grammarfield[FORMAT] == 'RL':    #if field format is numeric right aligned
                        value = value.ljust(grammarfield[MINLENGTH] + lengthcorrection)                        
                    elif grammarfield[FORMAT] == 'RR':    #if field format is numeric right aligned
                        value = value.rjust(grammarfield[MINLENGTH] + lengthcorrection)                        
                    else:
                        value = value.zfill(grammarfield[MINLENGTH] + lengthcorrection)
                    value = value.replace('.',self.ta_info['decimaal'],1)    #replace '.' by required decimal sep.
                elif grammarfield[BFORMAT] == 'N':  #fixed decimals; round
                    if self.ta_info['lengthnumericbare']:
                        if minussign:
                            lengthcorrection += 1
                        if grammarfield[DECIMALS]:
                            lengthcorrection += 1
                    try:
                        value = str(decimal.Decimal(minussign + digits + decimalsign + decimals).quantize(decimal.Decimal(10) ** -grammarfield[DECIMALS]))
                    except:
                        raise botslib.OutMessageError(_(u'record "$mpath" field "$field" numerical format not valid: "$content".'),field=grammarfield[ID],content=value,mpath=record[MPATH])
                    if grammarfield[FORMAT] == 'NL':    #if field format is numeric right aligned
                        value = value.ljust(grammarfield[MINLENGTH] + lengthcorrection)                        
                    elif grammarfield[FORMAT] == 'NR':    #if field format is numeric right aligned
                        value = value.rjust(grammarfield[MINLENGTH] + lengthcorrection)                        
                    else:
                        value = value.zfill(grammarfield[MINLENGTH] + lengthcorrection)
                    value = value.replace('.',self.ta_info['decimaal'],1)    #replace '.' by required decimal sep.
                elif grammarfield[BFORMAT] == 'I':  #implicit decimals
                    if self.ta_info['lengthnumericbare']:
                        if minussign:
                            lengthcorrection += 1
                    try:
                        d = decimal.Decimal(minussign + digits + decimalsign + decimals) * 10**grammarfield[DECIMALS]
                    except:
                        raise botslib.OutMessageError(_(u'record "$mpath" field "$field" numerical format not valid: "$content".'),field=grammarfield[ID],content=value,mpath=record[MPATH])
                    value = str(d.quantize(NODECIMAL ))
                    value = value.zfill(grammarfield[MINLENGTH] + lengthcorrection)
                
                if len(value)-lengthcorrection > grammarfield[LENGTH]:
                    raise botslib.OutMessageError(_(u'record "$mpath" field "$field": content to large: "$content".'),field=grammarfield[ID],content=value,mpath=record[MPATH])
        return value
                

    def _records2file(self):
        ''' convert self.records to a file.
            using the right editype (edifact, x12, etc) and charset.
        '''
        wrap_length = int(self.ta_info.get('wrap_length', 0))
        if wrap_length:
            s = ''.join(self._record2string(r) for r in self.records) # join all records
            for i in range(0,len(s),wrap_length): # then split in fixed lengths
                try:
                    self._outstream.write(s[i:i+wrap_length] + '\r\n')
                except UnicodeEncodeError:
                    raise botslib.OutMessageError(_(u'Chars in outmessage not in charset "$char": $content'),char=self.ta_info['charset'],content=s[i:i+wrap_length])
        else:
            for record in self.records:     #loop all records
                try:
                    self._outstream.write(self._record2string(record))
                except UnicodeEncodeError:  #, flup:    testing with 2.7: flup did not contain the content.
                    raise botslib.OutMessageError(_(u'Chars in outmessage not in charset "$char": $content'),char=self.ta_info['charset'],content=str(record))
                    #code before 7 aug 2007 had other handling for flup. May have changed because python2.4->2.5?

    def _record2string(self,record):
        ''' write (all fields of) a record using the right separators, escape etc
        '''
        sfield_sep = self.ta_info['sfield_sep']
        if self.ta_info['record_tag_sep']:
            record_tag_sep = self.ta_info['record_tag_sep']
        else:
            record_tag_sep = self.ta_info['field_sep']
        field_sep = self.ta_info['field_sep']
        quote_char = self.ta_info['quote_char']
        escape = self.ta_info['escape']
        record_sep = self.ta_info['record_sep'] + self.ta_info['add_crlfafterrecord_sep']
        forcequote = self.ta_info['forcequote']
        escapechars = self.getescapechars()
        value = u''     #to collect separator/escape plus field content 
        fieldcount = 0
        mode_quote = False
        if self.ta_info['noBOTSID']:  #for some csv-files: do not write BOTSID so remove it
            del record[0]
        for field in record:        #loop all fields in record
            if field[SFIELD]:
                value += sfield_sep
            else:   #is a field: 
                if fieldcount == 0:  #do nothing because first field in record is not preceded by a separator
                    fieldcount = 1
                elif fieldcount == 1:
                    value += record_tag_sep
                    fieldcount = 2
                else:
                    value += field_sep
            if quote_char:      #quote char only used for csv
                start_to__quote=False
                if forcequote == 2:
                    if field[FORMATFROMGRAMMAR] in ['AN','A','AR']:
                        start_to__quote=True
                elif forcequote:    #always quote; this catches values 1, '1', '0'
                    start_to__quote=True
                else:
                    if field_sep in field[VALUE] or quote_char in field[VALUE] or record_sep in field[VALUE]:
                        start_to__quote=True
                #TO DO test. if quote_char='' this works OK. Alt: check first if quote_char
                if start_to__quote:
                    value += quote_char
                    mode_quote = True
            for char in field[VALUE]:   #use escape (edifact, tradacom). For x12 is warned if content contains separator
                if char in escapechars:
                    if isinstance(self,x12):
                        if self.ta_info['replacechar']:
                            char = self.ta_info['replacechar']
                        else:
                            raise botslib.OutMessageError(_(u'Character "$char" is in use as separator in this x12 file. Field: "$data".'),char=char,data=field[VALUE])
                    else:
                        value +=escape
                elif mode_quote and char==quote_char:
                    value +=quote_char
                value += char
            if mode_quote:
                value += quote_char
                mode_quote = False
        value += record_sep
        return value

    def getescapechars(self):
        return ''

class fixed(Outmessage):
    pass
        
        
class idoc(fixed):
    def _canonicalfields(self,noderecord,structure_record,headerrecordnumber):
        if self.ta_info['automaticcount']:
            noderecord.update({'MANDT':self.ta_info['MANDT'],'DOCNUM':self.ta_info['DOCNUM'],'SEGNUM':str(self.recordnumber),'PSGNUM':str(headerrecordnumber),'HLEVEL':str(len(structure_record[MPATH]))})
        else:
            noderecord.update({'MANDT':self.ta_info['MANDT'],'DOCNUM':self.ta_info['DOCNUM']})
        super(idoc,self)._canonicalfields(noderecord,structure_record,headerrecordnumber)
        self.recordnumber += 1      #tricky. EDI_DC is not counted, so I count after writing.


class var(Outmessage):
    pass


class csv(var):
    def getescapechars(self):
        return self.ta_info['escape']



class edifact(var):
    def getescapechars(self):
        terug = self.ta_info['record_sep']+self.ta_info['field_sep']+self.ta_info['sfield_sep']+self.ta_info['escape']
        if self.ta_info['version']>='4':
            terug += self.ta_info['reserve']
        return terug
        
class tradacoms(var):
    def getescapechars(self):
        terug = self.ta_info['record_sep']+self.ta_info['field_sep']+self.ta_info['sfield_sep']+self.ta_info['escape']+self.ta_info['record_tag_sep']
        return terug

    def writeall(self):
        ''' writeall is called for writing all 'real' outmessage objects; but not for enveloping.
            writeall is call from transform.translate()
        '''
        self.nrmessagewritten = 0
        if not self.root.children:
            raise botslib.OutMessageError(_(u'No outgoing message'))    #then there is nothing to write...
        for message in self.root.getloop({'BOTSID':'STX'},{'BOTSID':'MHD'}):
            self.outmessagegrammarread(self.ta_info['editype'],message.get({'BOTSID':'MHD','TYPE.01':None}) + message.get({'BOTSID':'MHD','TYPE.02':None}))
            if not self.nrmessagewritten:
                self._initwrite()
            self.normalisetree(message)
            self._write(message)
            self.nrmessagewritten += 1
        self._closewrite()
        self.ta_info['nrmessages'] = self.nrmessagewritten

class x12(var):
    def getescapechars(self):
        terug = self.ta_info['record_sep']+self.ta_info['field_sep']+self.ta_info['sfield_sep']
        if self.ta_info['version']>='00403':
            terug += self.ta_info['reserve']
        return terug
        

class xml(Outmessage):
    ''' 20110919: code for _write is almost the same as for envelopewrite.
        this could be one method.
        Some problems with right xml prolog, standalone, DOCTYPE, processing instructons: Different ET versions give different results:
        celementtree in 2.7 is version 1.0.6, but different implementation in 2.6??
        So: this works OK for python 2.7
        For python <2.7: do not generate standalone, DOCTYPE, processing instructions for encoding !=utf-8,ascii OR if elementtree package is installed (version 1.3.0 or bigger)
    '''
    def _write(self,node):
        ''' write normal XML messages (no envelope)'''
        xmltree = ET.ElementTree(self._node2xml(node))
        root = xmltree.getroot()
        self._xmlcorewrite(xmltree,root)

    def envelopewrite(self,node):
        ''' write envelope for XML messages'''
        self._initwrite()
        self.normalisetree(node)
        xmltree = ET.ElementTree(self._node2xml(node))
        root = xmltree.getroot()
        ETI.include(root)
        self._xmlcorewrite(xmltree,root)
        self._closewrite()

    def _xmlcorewrite(self,xmltree,root):
        #xml prolog: always use.*********************************
        #standalone, DOCTYPE, processing instructions: only possible in python >= 2.7 or if encoding is utf-8/ascii
        if sys.version >= '2.7.0' or self.ta_info['charset'] in ['us-ascii','utf-8'] or ET.VERSION >= '1.3.0':
            if self.ta_info['indented']:
                indentstring = '\n'
            else:
                indentstring = ''
            if self.ta_info['standalone']:
                standalonestring = 'standalone="%s" '%(self.ta_info['standalone'])
            else:
                standalonestring = ''
            PI = ET.ProcessingInstruction('xml', 'version="%s" encoding="%s" %s'%(self.ta_info['version'],self.ta_info['charset'], standalonestring))        
            self._outstream.write(ET.tostring(PI) + indentstring) #do not use encoding here. gives double xml prolog; possibly because ET.ElementTree.write i used again by write()
            #doctype /DTD **************************************
            if self.ta_info['DOCTYPE']:
                self._outstream.write('<!DOCTYPE %s>'%(self.ta_info['DOCTYPE']) + indentstring)
            #processing instructions (other than prolog) ************
            if self.ta_info['processing_instructions']:
                for pi in self.ta_info['processing_instructions']:
                    PI = ET.ProcessingInstruction(pi[0], pi[1])
                    self._outstream.write(ET.tostring(PI) + indentstring) #do not use encoding here. gives double xml prolog; possibly because ET.ElementTree.write i used again by write()
        #indent the xml elements
        if self.ta_info['indented']:
            self.botsindent(root)
        #write tree to file; this is differnt for different python/elementtree versions
        if sys.version < '2.7.0' and ET.VERSION < '1.3.0':
            xmltree.write(self._outstream,encoding=self.ta_info['charset'])
        else:
            xmltree.write(self._outstream,encoding=self.ta_info['charset'],xml_declaration=False)
        
    def botsindent(self,elem, level=0,indentstring='    '):
        i = "\n" + level*indentstring
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + indentstring
            for e in elem:
                self.botsindent(e, level+1)
                if not e.tail or not e.tail.strip():
                    e.tail = i + indentstring
            if not e.tail or not e.tail.strip():
                e.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    def _node2xml(self,node):
        ''' recursive method.
        '''
        newnode = self._node2xmlfields(node.record)
        for childnode in node.children:
            newnode.append(self._node2xml(childnode))
        return newnode

    def _node2xmlfields(self,noderecord):
        ''' fields in a node are written to xml fields; output is sorted according to grammar
        '''
        #first generate the xml-'record'
        #~ print 'record',noderecord['BOTSID']
        attributedict = {}
        recordtag = noderecord['BOTSID']
        attributemarker = recordtag + self.ta_info['attributemarker']       #attributemarker is a marker in the fieldname used to find out if field is an attribute of either xml-'record' or xml-element
        #~ print '    rec_att_mark',attributemarker
        for key,value in noderecord.items():    #find attributes belonging to xml-'record' and store in attributedict
            if key.startswith(attributemarker):
                #~ print '    record attribute',key,value
                attributedict[key[len(attributemarker):]] = value
        xmlrecord = ET.Element(recordtag,attributedict) #make the xml ET node
        if 'BOTSCONTENT' in noderecord:     #BOTSCONTENT is used to store the value/text of the xml-record itself.
            xmlrecord.text = noderecord['BOTSCONTENT']
            del noderecord['BOTSCONTENT']
        for key in attributedict.keys():  #remove used fields
            del noderecord[attributemarker+key]
        del noderecord['BOTSID']    #remove 'record' tag
        #generate xml-'fields' in xml-'record'; sort these by looping over records definition
        for field_def in self.defmessage.recorddefs[recordtag]:  #loop over fields in 'record'
            if field_def[ID] not in noderecord: #if field not in outmessage: skip
                continue
            #~ print '    field',field_def
            attributedict = {}
            attributemarker = field_def[ID] + self.ta_info['attributemarker'] 
            #~ print '    field_att_mark',attributemarker
            for key,value in noderecord.items():
                if key.startswith(attributemarker):
                    #~ print '        field attribute',key,value
                    attributedict[key[len(attributemarker):]] = value
            ET.SubElement(xmlrecord, field_def[ID],attributedict).text=noderecord[field_def[ID]]    #add xml element to xml record
            for key in attributedict.keys():  #remove used fields
                del noderecord[attributemarker+key]
            del noderecord[field_def[ID]]    #remove xml entity tag
        return xmlrecord
        
    def _initwrite(self):
        botsglobal.logger.debug(u'Start writing to file "%s".',self.ta_info['filename'])
        self._outstream = botslib.opendata(self.ta_info['filename'],"wb")
        

class xmlnocheck(xml):
    def normalisetree(self,node):
        pass

    def _node2xmlfields(self,noderecord):
        ''' fields in a node are written to xml fields; output is sorted according to grammar
        '''
        if 'BOTSID' not in noderecord:
            raise botslib.OutMessageError(_(u'No field "BOTSID" in xml-output in: "$record"'),record=noderecord)
        #first generate the xml-'record'
        attributedict = {}
        recordtag = noderecord['BOTSID']
        attributemarker = recordtag + self.ta_info['attributemarker'] 
        for key,value in noderecord.items():    #find the attributes for the xml-record, put these in attributedict
            if key.startswith(attributemarker):
                attributedict[key[len(attributemarker):]] = value
        xmlrecord = ET.Element(recordtag,attributedict) #make the xml ET node
        if 'BOTSCONTENT' in noderecord:
            xmlrecord.text = noderecord['BOTSCONTENT']
            del noderecord['BOTSCONTENT']
        for key in attributedict.keys():  #remove used fields
            del noderecord[attributemarker+key]
        del noderecord['BOTSID']    #remove 'record' tag
        #generate xml-'fields' in xml-'record'; not sorted
        noderecordcopy = noderecord.copy()
        for key,value in noderecordcopy.items():
            if key not in noderecord or self.ta_info['attributemarker'] in key: #if field not in outmessage: skip
                continue
            attributedict = {}
            attributemarker = key + self.ta_info['attributemarker'] 
            for key2,value2 in noderecord.items():
                if key2.startswith(attributemarker):
                    attributedict[key2[len(attributemarker):]] = value2
            ET.SubElement(xmlrecord, key,attributedict).text=value    #add xml element to xml record
            for key2 in attributedict.keys():  #remove used fields
                del noderecord[attributemarker+key2]
            del noderecord[key]    #remove xml entity tag
        return xmlrecord
        

class json(Outmessage):
    def _initwrite(self):
        super(json,self)._initwrite()
        if self.multiplewrite:
            self._outstream.write(u'[')

    def _write(self,node):
        ''' convert node tree to appropriate python object.
            python objects are written to json by simplejson.
        '''
        if self.nrmessagewritten:
            self._outstream.write(u',')
        jsonobject = {node.record['BOTSID']:self._node2json(node)}
        if self.ta_info['indented']:
            indent=2
        else:
            indent=None
        simplejson.dump(jsonobject, self._outstream, skipkeys=False, ensure_ascii=False, check_circular=False, indent=indent)

    def _closewrite(self):
        if self.multiplewrite:
            self._outstream.write(u']')
        super(json,self)._closewrite()

    def _node2json(self,node):
        ''' recursive method.
        '''
        #newjsonobject is the json object assembled in the function.
        newjsonobject = node.record.copy()    #init newjsonobject with record fields from node 
        for childnode in node.children: #fill newjsonobject with the records from childnodes. 
            key=childnode.record['BOTSID']
            if key in newjsonobject:
                newjsonobject[key].append(self._node2json(childnode))
            else:
                newjsonobject[key]=[self._node2json(childnode)]
        del newjsonobject['BOTSID']
        return newjsonobject
        
    def _node2jsonold(self,node):
        ''' recursive method.
        '''
        newdict = node.record.copy()
        if node.children:   #if this node has records in it.
            sortedchildren={}   #empty dict 
            for childnode in node.children:
                botsid=childnode.record['BOTSID']
                if botsid in sortedchildren:
                    sortedchildren[botsid].append(self._node2json(childnode))
                else:
                    sortedchildren[botsid]=[self._node2json(childnode)]
            for key,value in sortedchildren.items():
                if len(value)==1:
                    newdict[key]=value[0]
                else:
                    newdict[key]=value
        del newdict['BOTSID']
        return newdict
        
class jsonnocheck(json):
    def normalisetree(self,node):
        pass

class template(Outmessage):
    ''' uses Kid library for templating.'''
    class TemplateData(object):
        pass
    def __init__(self,ta_info):
        self.data = template.TemplateData() #self.data is used by mapping script as container for content
        super(template,self).__init__(ta_info)

    def writeall(self):
        ''' Very different writeall:
            there is no tree of nodes; there is no grammar.structure/recorddefs; kid opens file by itself.
        '''
        try:
            import kid
        except:
            txt=botslib.txtexc()
            raise ImportError(_(u'Dependency failure: editype "template" requires python library "kid". Error:\n%s'%txt))
        #for template-grammar: only syntax is used. Section 'syntax' has to have 'template'
        self.outmessagegrammarread(self.ta_info['editype'],self.ta_info['messagetype'])
        templatefile = botslib.abspath(u'templates',self.ta_info['template'])
        try:
            botsglobal.logger.debug(u'Start writing to file "%s".',self.ta_info['filename'])
            ediprint = kid.Template(file=templatefile, data=self.data)
        except:
            txt=botslib.txtexc()
            raise botslib.OutMessageError(_(u'While templating "$editype.$messagetype", error:\n$txt'),editype=self.ta_info['editype'],messagetype=self.ta_info['messagetype'],txt=txt)
        try:
            f = botslib.opendata(self.ta_info['filename'],'wb')
            ediprint.write(f,
            #~ ediprint.write(botslib.abspathdata(self.ta_info['filename']),
                            encoding=self.ta_info['charset'],
                            output=self.ta_info['output'],    #output is specific parameter for class; init from grammar.syntax
                            fragment=self.ta_info['merge'])
        except:
            txt=botslib.txtexc()
            raise botslib.OutMessageError(_(u'While templating "$editype.$messagetype", error:\n$txt'),editype=self.ta_info['editype'],messagetype=self.ta_info['messagetype'],txt=txt)
        botsglobal.logger.debug(_(u'End writing to file "%s".'),self.ta_info['filename'])


class templatehtml(Outmessage):
    ''' uses Genshi library for templating. Genshi is very similar to Kid, and is the fork/follow-up of Kid.
        Kid is not being deveolped further; in time Kid will not be in repositories etc.
        Templates for Genshi are like Kid templates. Changes:
        - other namespace: xmlns:py="http://genshi.edgewall.org/" instead of xmlns:py="http://purl.org/kid/ns#"
        - enveloping is different: <xi:include href="${message}" /> instead of <div py:replace="document(message)"/>
    '''
    class TemplateData(object):
        pass
    def __init__(self,ta_info):
        self.data = template.TemplateData() #self.data is used by mapping script as container for content
        super(templatehtml,self).__init__(ta_info)

    def writeall(self):
        ''' Very different writeall:
            there is no tree of nodes; there is no grammar.structure/recorddefs; kid opens file by itself.
        '''
        try:
            from genshi.template import TemplateLoader
        except:
            txt=botslib.txtexc()
            raise ImportError(_(u'Dependency failure: editype "template" requires python library "genshi". Error:\n%s'%txt))
        #for template-grammar: only syntax is used. Section 'syntax' has to have 'template'
        self.outmessagegrammarread(self.ta_info['editype'],self.ta_info['messagetype'])
        templatefile = botslib.abspath(u'templateshtml',self.ta_info['template'])
        try:
            botsglobal.logger.debug(u'Start writing to file "%s".',self.ta_info['filename'])
            loader = TemplateLoader(auto_reload=False)
            tmpl = loader.load(templatefile)
        except:
            txt=botslib.txtexc()
            raise botslib.OutMessageError(_(u'While templating "$editype.$messagetype", error:\n$txt'),editype=self.ta_info['editype'],messagetype=self.ta_info['messagetype'],txt=txt)
        try:
            f = botslib.opendata(self.ta_info['filename'],'wb')
            stream = tmpl.generate(data=self.data)
            stream.render(method='xhtml',encoding=self.ta_info['charset'],out=f)
        except:
            txt=botslib.txtexc()
            raise botslib.OutMessageError(_(u'While templating "$editype.$messagetype", error:\n$txt'),editype=self.ta_info['editype'],messagetype=self.ta_info['messagetype'],txt=txt)
        botsglobal.logger.debug(_(u'End writing to file "%s".'),self.ta_info['filename'])


class database(jsonnocheck):
    pass
    
class db(Outmessage):
    ''' out.root is pickled, and saved.
    '''
    def __init__(self,ta_info):
        super(db,self).__init__(ta_info)
        self.root = None    #make root None; root is not a Node-object anyway; None can easy be tested when writing.

    def writeall(self):
        if self.root is None:
            raise botslib.OutMessageError(_(u'No outgoing message'))    #then there is nothing to write...
        botsglobal.logger.debug(u'Start writing to file "%s".',self.ta_info['filename'])
        self._outstream = botslib.opendata(self.ta_info['filename'],'wb')
        db_object = pickle.dump(self.root,self._outstream,2)
        self._outstream.close()
        botsglobal.logger.debug(u'End writing to file "%s".',self.ta_info['filename'])
        self.ta_info['envelope'] = 'db'     #use right enveloping for db: no coping etc, use same file.


class raw(Outmessage):
    ''' out.root is just saved.
    '''
    def __init__(self,ta_info):
        super(raw,self).__init__(ta_info)
        self.root = None    #make root None; root is not a Node-object anyway; None can easy be tested when writing.

    def writeall(self):
        if self.root is None:
            raise botslib.OutMessageError(_(u'No outgoing message'))    #then there is nothing to write...
        botsglobal.logger.debug(u'Start writing to file "%s".',self.ta_info['filename'])
        self._outstream = botslib.opendata(self.ta_info['filename'],'wb')
        self._outstream.write(self.root)
        self._outstream.close()
        botsglobal.logger.debug(u'End writing to file "%s".',self.ta_info['filename'])
        self.ta_info['envelope'] = 'raw'     #use right enveloping for raw: no coping etc, use same file.
