''' Reading/lexing/parsing/splitting an edifile.'''
import time
#~ import sys
try:
    import cPickle as pickle
except:
    import pickle
try:
    import cElementTree as ET
except ImportError:
    try:
        import elementtree.ElementTree as ET
    except ImportError:
        try:
            from xml.etree import cElementTree as ET
        except ImportError:
            from xml.etree import ElementTree as ET
try:
    import json as simplejson
except ImportError:
    import simplejson
from django.utils.translation import ugettext as _
import botslib
import botsglobal
import outmessage
import message
import node
import grammar
from botsconfig import *

def edifromfile(**ta_info):
    ''' Read,lex, parse edi-file. Is a dispatch function for Inmessage and subclasses.'''
    try:
        classtocall = globals()[ta_info['editype']]  #get inmessage class to call (subclass of Inmessage)
    except KeyError:
        raise botslib.InMessageError(_(u'Unknown editype for incoming message: $editype'),editype=ta_info['editype'])
    ediobject = classtocall(ta_info)
    ediobject.initfromfile()
    return ediobject

def _edifromparsed(editype,inode,ta_info):
    ''' Get a edi-message (inmessage-object) from node in tree.
        is used in splitting edi-messages.'''
    classtocall = globals()[editype]
    ediobject = classtocall(ta_info)
    ediobject.initfromparsed(inode)
    return ediobject

#*****************************************************************************
class Inmessage(message.Message):
    ''' abstract class for incoming ediobject (file or message).
        Can be initialised from a file or a tree.
    '''
    def __init__(self,ta_info):
        super(Inmessage,self).__init__()
        self.records = []        #init list of records
        self.confirminfo = {}
        self.ta_info = ta_info  #here ta_info is only filled with parameters from db-ta

    def initfromfile(self):
        ''' initialisation from a edi file '''
        self.defmessage = grammar.grammarread(self.ta_info['editype'],self.ta_info['messagetype'])  #read grammar, after sniffing. Information from sniffing can be used (eg name editype for edifact, using version info from UNB)
        botslib.updateunlessset(self.ta_info,self.defmessage.syntax)    #write values from grammar to self.ta_info - unless these values are already set
        self.ta_info['charset'] =self.defmessage.syntax['charset']      #always use charset of edi file.
        self._readcontent_edifile()
        self._sniff()           #some hard-coded parsing of edi file; eg ta_info can be overruled by syntax-parameters in edi-file
        #start lexing and parsing
        self._lex()
        if hasattr(self,'rawinput'):
            del self.rawinput
        #~ self.display(self.records)   #show lexed records (for protocol debugging)
        self.root = node.Node()  #make root Node None.
        self.iternextrecord = iter(self.records)
        result = self._parse(structure_level=self.defmessage.structure,inode=self.root)
        if result:
            raise botslib.InMessageError(_(u'Unknown data beyond end of message; mostly problem with separators or message structure: "$content"'),content=result)
        del self.records
        #end parsing; self.root is root of a tree (of nodes).
        self.checkenvelope()
        self.checkmessage(self.root,self.defmessage)
        #~ self.root.display() #show tree of nodes (for protocol debugging)
        #~ self.root.displayqueries() #show queries in tree of nodes (for protocol debugging)

    def initfromparsed(self,node_instance):
        ''' initialisation from a tree (node is passed).
            to initialise message in an envelope
        '''
        self.root = node_instance

    def handleconfirm(self,ta_fromfile,error):
        ''' end of edi file handling.
            eg writing of confirmations etc.
        '''
        pass

    def _formatfield(self,value,grammarfield,structure_record):
        ''' Format of a field is checked and converted if needed.
            Input: value (string), field definition.
            Output: the formatted value (string)
            Parameters of self.ta_info are used: triad, decimaal
            for fixed field: same handling; length is not checked.
        '''
        if grammarfield[BFORMAT] == 'A':
            if isinstance(self,var):  #check length fields in variable records
                lenght = len(value)
                if lenght > grammarfield[LENGTH]:
                    self.add2errorlist(_(u'[F05] Record "%(record)s" field "%(field)s" too big (max %(max)s): "%(content)s".\n')%{'record':structure_record[MPATH],'field':grammarfield[ID],'content':value,'max':grammarfield[LENGTH]})
                if lenght < grammarfield[MINLENGTH]:
                    self.add2errorlist(_(u'[F06] Record "%(record)s" field "%(field)s" too small (min %(min)s): "%(content)s".\n')%{'record':structure_record[MPATH],'field':grammarfield[ID],'content':value,'min':grammarfield[MINLENGTH]})
        elif grammarfield[BFORMAT] == 'D':
            try:
                lenght = len(value)
                if lenght == 6:
                    time.strptime(value,'%y%m%d')
                elif lenght == 8:
                    time.strptime(value,'%Y%m%d')
                else:
                    raise ValueError(u'To be catched')
            except ValueError:
                self.add2errorlist(_(u'[F07] Record "%(record)s" date field "%(field)s" not a valid date: "%(content)s".\n')%{'record':structure_record[MPATH],'field':grammarfield[ID],'content':value})
        elif grammarfield[BFORMAT] == 'T':
            try:
                lenght = len(value)
                if lenght == 4:
                    time.strptime(value,'%H%M')
                elif lenght == 6:
                    time.strptime(value,'%H%M%S')
                elif lenght == 7 or lenght == 8:
                    time.strptime(value[0:6],'%H%M%S')
                    if not value[6:].isdigit():
                        raise ValueError(u'To be catched')
                else:
                    raise ValueError(u'To be catched')
            except  ValueError:
                self.add2errorlist(_(u'[F08] Record "%(record)s" time field "%(field)s" not a valid time: "%(content)s".\n')%{'record':structure_record[MPATH],'field':grammarfield[ID],'content':value})
        else:   #numerics (R, N, I)
            #~ if not value:
                #~ if self.ta_info['acceptspaceinnumfield']:
                    #~ value='0'
                #~ else:
                    #~ self.add2errorlist(_(u'[13] Record "%(record)s" field "%(field)s" has numeric format but contains only space.\n')%{'record':structure_record[MPATH],'field':grammarfield[ID]})
                #~ return ''   #when num field has spaces as content, spaces are stripped. Field should be numeric.
            if value[-1] == u'-':    #if minus-sign at the end, put it in front.
                value = value[-1] + value[:-1]
            value = value.replace(self.ta_info['triad'],u'')     #strip triad-separators
            value = value.replace(self.ta_info['decimaal'],u'.',1) #replace decimal sign by canonical decimal sign
            if 'E' in value or 'e' in value:
                self.add2errorlist(_(u'[F09] Record "%(record)s" field "%(field)s" contains exponent: "%(content)s".\n')%{'record':structure_record[MPATH],'field':grammarfield[ID],'content':value})
            if isinstance(self,var):  #check length num fields in variable records
                if self.ta_info['lengthnumericbare']:
                    length = botslib.countunripchars(value,'-+.')
                else:
                    length = len(value)
                if length > grammarfield[LENGTH]:
                    self.add2errorlist(_(u'[F10] Record "%(record)s" field "%(field)s" too big (max %(max)s): "%(content)s".\n')%{'record':structure_record[MPATH],'field':grammarfield[ID],'content':value,'max':grammarfield[LENGTH]})
                if length < grammarfield[MINLENGTH]:
                    self.add2errorlist(_(u'[F11] Record "%(record)s" field "%(field)s" too small (min %(min)s): "%(content)s".\n')%{'record':structure_record[MPATH],'field':grammarfield[ID],'content':value,'min':grammarfield[MINLENGTH]})
            if grammarfield[BFORMAT] == 'I':
                if '.' in value:
                    self.add2errorlist(_(u'[F12] Record "%(record)s" field "%(field)s" has format "I" but contains decimal sign: "%(content)s".\n')%{'record':structure_record[MPATH],'field':grammarfield[ID],'content':value})
                else:
                    try:    #convert to decimal in order to check validity
                        valuedecimal = float(value)
                        valuedecimal = valuedecimal / 10**grammarfield[DECIMALS]
                        value = '%.*F'%(grammarfield[DECIMALS],valuedecimal)
                    except:
                        self.add2errorlist(_(u'[F13] Record "%(record)s" numeric field "%(field)s" has non-numerical content: "%(content)s".\n')%{'record':structure_record[MPATH],'field':grammarfield[ID],'content':value})
            elif grammarfield[BFORMAT] == 'N':
                lendecimal = len(value[value.find('.'):])-1
                if lendecimal != grammarfield[DECIMALS]:
                    self.add2errorlist(_(u'[F14] Record "%(record)s" numeric field "%(field)s" has invalid nr of decimals: "%(content)s".\n')%{'record':structure_record[MPATH],'field':grammarfield[ID],'content':value})
                try:    #convert to decimal in order to check validity
                    valuedecimal = float(value)
                    value = '%.*F'%(lendecimal,valuedecimal)
                except:
                    self.add2errorlist(_(u'[F15] Record "%(record)s" numeric field "%(field)s" has non-numerical content: "%(content)s".\n')%{'record':structure_record[MPATH],'field':grammarfield[ID],'content':value})
            elif grammarfield[BFORMAT] == 'R':
                lendecimal = len(value[value.find('.'):])-1
                try:    #convert to decimal in order to check validity
                    valuedecimal = float(value)
                    value = '%.*F'%(lendecimal,valuedecimal)
                except:
                    self.add2errorlist(_(u'[F16] Record "%(record)s" numeric field "%(field)s" has non-numerical content: "%(content)s".\n')%{'record':structure_record[MPATH],'field':grammarfield[ID],'content':value})
        return value

    def _parse(self,structure_level,inode):
        ''' This is the heart of the parsing of incoming messages (but not for xml, json)
            Read the records one by one (self.iternextrecord, is an iterator)
            - parse the (lexed) records.
            - identify record (lookup in structure)
            - identify fields in the record (use the structurerecord from the grammar).
            - add grammar-info to records: field-tag,mpath.
            Parameters:
            - structure_level: current grammar/segmentgroup of the grammar-structure.
            - inode: parent node; all parsed records are added as children of inode
            2x recursive: SUBTRANSLATION and segmentgroups
        '''
        structure_index = 0     #keep track of where we are in the structure_level
        countnrofoccurences = 0 #number of occurences of current record in structure
        structure_end = len(structure_level)
        get_next_edi_record = True      #indicate if the next record should be fetched, or if the current_edi_record is still being parsed.
                                        #it might seem logical to test here 'current_edi_record is None', but this is already used to indicate 'no more records'.
        while 1:
            if get_next_edi_record:
                try:
                    current_edi_record = self.iternextrecord.next()
                except StopIteration:   #catch when no more current_edi_record.
                    current_edi_record = None
                get_next_edi_record = False
            if current_edi_record is None or structure_level[structure_index][ID] != current_edi_record[ID][VALUE]:
                if structure_level[structure_index][MIN] and not countnrofoccurences:   #is record is required in structure_level, and countnrofoccurences==0: error;
                                                                                        #enough check here; message is validated more accurate later
                    try:
                        raise botslib.InMessageError(_(u'Line:$line pos:$pos record:"$record": message has an error in its structure; this record is not allowed here. Scanned in message definition until mandatory record: "$looked".'),record=current_edi_record[ID][VALUE],line=current_edi_record[ID][LIN],pos=current_edi_record[ID][POS],looked=structure_level[structure_index][MPATH])
                    except TypeError:       #when no UNZ (edifact)
                        raise botslib.InMessageError(_(u'Missing mandatory record "$record".'),record=structure_level[structure_index][MPATH])
                structure_index += 1
                if structure_index == structure_end:  #current_edi_record is not in this level. Go level up
                    return current_edi_record    #return either None (no more data-records to parse) or the last record2parse (the last record2parse is not found in this level)
                countnrofoccurences = 0
                continue  #continue while-loop: get_next_edi_record is false as no match with structure is made; go and look at next record of structure
            #record is found in grammar
            countnrofoccurences += 1
            newnode = node.Node(record=self._parsefields(current_edi_record,structure_level[structure_index]),botsidnr=structure_level[structure_index][BOTSIDNR])  #make new node
            inode.append(newnode)   #succes! append new node as a child to current (parent)node
            if SUBTRANSLATION in structure_level[structure_index]:
                # start a SUBTRANSLATION; find the right messagetype, etc
                messagetype = newnode.enhancedget(structure_level[structure_index][SUBTRANSLATION])
                if not messagetype:
                    raise botslib.InMessageError(_(u'Could not find SUBTRANSLATION "$sub" in (sub)message.'),sub=structure_level[structure_index][SUBTRANSLATION])
                if hasattr(self,'_getmessagetype'):     #x12 also needs field from GS record
                    messagetype = self._getmessagetype(messagetype,inode)
                messagetype = messagetype.replace('.','_')      #hack: older edifact messages have eg 90.1 as version...does not match with python imports...so convert this
                try:
                    defmessage = grammar.grammarread(self.__class__.__name__,messagetype)
                except ImportError:
                    raise botslib.InMessageError(_(u'No (valid) grammar for editype "$editype" messagetype "$messagetype".'),editype=self.__class__.__name__,messagetype=messagetype)
                current_edi_record = self._parse(structure_level=defmessage.structure[0][LEVEL],inode=newnode)
                newnode.queries = {'messagetype':messagetype}       #copy messagetype into 1st segment of subtranslation (eg UNH, ST)
                self.checkmessage(newnode,defmessage,subtranslation=True)      #check the results of the subtranslation
                #~ end SUBTRANSLATION
                # get_next_edi_record is still False; the current_edi_record not matched in the SUBTRANSLATION is still being parsed.
            elif LEVEL in structure_level[structure_index]:        #if header, go parse segmentgroup (recursive)
                current_edi_record = self._parse(structure_level=structure_level[structure_index][LEVEL],inode=newnode)
                # get_next_edi_record is still False; the current_edi_record that was not matched in lower segmentgroups is still being parsed.
            else:
                get_next_edi_record = True

    def _readcontent_edifile(self):
        ''' read content of edi file to memory.
        '''
        botsglobal.logger.debug(u'read edi file "%s".',self.ta_info['filename'])
        self.rawinput = botslib.readdata(filename=self.ta_info['filename'],charset=self.ta_info['charset'],errors=self.ta_info['checkcharsetin'])

    def _sniff(self):
        ''' sniffing: hard coded parsing of edi file.
            method is specified in subclasses.
        '''
        pass

    def checkenvelope(self):
        pass

    def nextmessage(self):
        ''' Generates each message as a separate Inmessage.
        '''
        #~ self.root.display()
        if self.defmessage.nextmessage is not None: #if nextmessage defined in grammar: split up messages
            first = True
            for eachmessage in self.getloop(*self.defmessage.nextmessage):  #get node of each message
                if first:
                    self.root.processqueries({},len(self.defmessage.nextmessage))
                    first = False
                ta_info = self.ta_info.copy()
                ta_info.update(eachmessage.queries)
                #~ ta_info['botsroot']=self.root
                yield _edifromparsed(self.__class__.__name__,eachmessage,ta_info)
            if self.defmessage.nextmessage2 is not None:        #edifact needs nextmessage2...OK
                first = True
                for eachmessage in self.getloop(*self.defmessage.nextmessage2):
                    if first:
                        self.root.processqueries({},len(self.defmessage.nextmessage2))
                        first = False
                    ta_info = self.ta_info.copy()
                    ta_info.update(eachmessage.queries)
                    #~ ta_info['botsroot']=self.root
                    yield _edifromparsed(self.__class__.__name__,eachmessage,ta_info)
        elif self.defmessage.nextmessageblock is not None:          #for csv/fixed: nextmessageblock indicates which field determines a message (as long as the field is the same, it is one message)
            #there is only one recordtype (this is checked in grammar.py).
            first = True
            for line in self.root.children:
                kriterium = line.get(self.defmessage.nextmessageblock)
                if first:
                    first = False
                    newroot = node.Node()  #make new empty root node.
                    oldkriterium = kriterium
                elif kriterium != oldkriterium:
                    ta_info = self.ta_info.copy()
                    ta_info.update(oldline.queries)        #update ta_info with information (from previous line) 20100905
                    #~ ta_info['botsroot']=self.root   #give mapping script access to all information in edi file: all records
                    yield _edifromparsed(self.__class__.__name__,newroot,ta_info)
                    newroot = node.Node()  #make new empty root node.
                    oldkriterium = kriterium
                else:
                    pass    #if kriterium is the same
                newroot.append(line)
                oldline = line #save line 20100905
            else:
                if not first:
                    ta_info = self.ta_info.copy()
                    ta_info.update(line.queries)        #update ta_info with information (from last line) 20100904
                    #~ ta_info['botsroot']=self.root
                    yield _edifromparsed(self.__class__.__name__,newroot,ta_info)
        else:   #no split up indicated in grammar;
            if self.root.record or self.ta_info['pass_all']:    #if contains root-record or explicitly indicated (csv): pass whole tree
                ta_info = self.ta_info.copy()
                ta_info.update(self.root.queries)
                #~ ta_info['botsroot']=None        #??is the same as self.root, so I use None??.
                yield _edifromparsed(self.__class__.__name__,self.root,ta_info)
            else:   #pass nodes under root one by one
                for child in self.root.children:
                    ta_info = self.ta_info.copy()
                    ta_info.update(child.queries)
                    #~ ta_info['botsroot']=self.root   #give mapping script access to all information in edi file: all roots
                    yield _edifromparsed(self.__class__.__name__,child,ta_info)

class fixed(Inmessage):
    ''' class for record of fixed length.'''
    def _readcontent_edifile(self):
        ''' read content of edi file to memory.
        '''
        botsglobal.logger.debug(u'read edi file "%s".',self.ta_info['filename'])
        self.filehandler = botslib.opendata(filename=self.ta_info['filename'],mode='rb',charset=self.ta_info['charset'],errors=self.ta_info['checkcharsetin'])

    def _lex(self):
        ''' lexes file with fixed records to list of records (self.records).'''
        linenr = 0
        startrecordid = self.ta_info['startrecordID']
        endrecordid = self.ta_info['endrecordID']
        for line in self.filehandler:
            linenr += 1
            if not line.isspace():
                line = line.rstrip('\r\n')
                self.records += [ [{VALUE:line[startrecordid:endrecordid].strip(),LIN:linenr,POS:0,FIXEDLINE:line}] ]    #append record to recordlist

    def _parsefields(self,record_in_edifile,structurerecord):
        ''' Parse fields from one fixed message-record (from record_in_edifile[ID][FIXEDLINE] using positions.
            fields are placed in recorddict, where key=field-info from grammar and value is from fixedrecord.'''
        recorddef = structurerecord[FIELDS]
        recorddict = {} #start with empty dict
        fixedrecord = record_in_edifile[ID][FIXEDLINE]  #shortcut to fixed record we are parsing
        lenfixed = len(fixedrecord)
        recordlength = sum([field[LENGTH] for field in recorddef])
        if recordlength > lenfixed and self.ta_info['checkfixedrecordtooshort']:
            raise botslib.InMessageError(_(u'line $line record "$record" too short; is $pos pos, defined is $defpos pos: "$content".'),line=record_in_edifile[ID][LIN],record=record_in_edifile[ID][VALUE],pos=lenfixed,defpos=recordlength,content=fixedrecord)
        if recordlength < lenfixed and self.ta_info['checkfixedrecordtoolong']:
            raise botslib.InMessageError(_(u'line $line record "$record" too long; is $pos pos, defined is $defpos pos: "$content".'),line=record_in_edifile[ID][LIN],record=record_in_edifile[ID][VALUE],pos=lenfixed,defpos=recordlength,content=fixedrecord)
        pos = 0
        for field in recorddef:   #for fields in this record
            value = fixedrecord[pos:pos+field[LENGTH]].strip()
            if value:
                recorddict[field[ID]] = value #copy id string to avoid memory problem ; value is already a copy
            pos += field[LENGTH]
        return recorddict


class idoc(fixed):
    ''' class for idoc ediobjects.
        for incoming the same as fixed.
        SAP does strip all empty fields for record; is catered for in grammar.defaultsyntax
    '''
    pass
    #~ def _sniff(self):
        #~ #goto char that is not whitespace
        #~ for count,char in enumerate(self.rawinput):
            #~ if not char.isspace():
                #~ self.rawinput = self.rawinput[count:]  #here the interchange should start
                #~ break
        #~ else:
            #~ raise botslib.InMessageError(_(u'edi file only contains whitespace.'))
        #~ if self.rawinput[:6] != 'EDI_DC':
            #~ raise botslib.InMessageError(_(u'expect "EDI_DC", found "$content". Probably no SAP idoc.'),content=self.rawinput[:6])


class var(Inmessage):
    ''' abstract class for ediobjects with records of variabele length.'''
    def _lex(self):
        ''' lexes file with variable records to list of records, fields and subfields (self.records).'''
        quote_char  = self.ta_info['quote_char']
        skip_char   = self.ta_info['skip_char'] #skip char (ignore);
        escape      = self.ta_info['escape']    #char after escape-char is not interpreted as seperator
        field_sep   = self.ta_info['field_sep'] + self.ta_info['record_tag_sep']    #for tradacoms; field_sep and record_tag_sep have same function.
        sfield_sep  = self.ta_info['sfield_sep']
        record_sep  = self.ta_info['record_sep']
        mode_escape = 0 #0=not escaping, 1=escaping
        mode_quote = 0 #0=not in quote, 1=in quote
        mode_2quote = 0 #0=not escaping quote, 1=escaping quote.
        mode_inrecord = 0    #indicates if lexing a record. If mode_inrecord==0: skip whitespace
        sfield = False # True: is subveld, False is geen subveld
        value = u''    #the value of the current token
        record = []
        valueline = 1    #starting line of token
        valuepos = 1    #starting position of token
        countline = 1
        countpos = 0
        #bepaal tekenset, separators etc adhv UNA/UNOB
        for char in self.rawinput:    #get next char
            if char == u'\n':    #line within file
                countline += 1
                countpos = 0            #new line, pos back to 0
                #no continue, because \n can be record separator. In edifact: catched with skip_char
            else:
                countpos += 1        #position within line
            if mode_quote:          #within a quote: quote-char is also escape-char
                if mode_2quote and char == quote_char: #thus we were escaping quote_char
                    mode_2quote = 0
                    value += char    #append quote_char
                    continue
                elif mode_escape:        #tricky: escaping a quote char
                    mode_escape = 0
                    value += char
                    continue
                elif mode_2quote:   #thus is was a end-quote
                    mode_2quote = 0
                    mode_quote = 0
                    #go on parsing
                elif char == quote_char:    #either end-quote or escaping quote_char,we do not know yet
                    mode_2quote = 1
                    continue
                elif char == escape:
                    mode_escape = 1
                    continue
                else:
                    value += char
                    continue
            if mode_inrecord:
                pass               #do nothing, is already in mode_inrecord
            else:
                if char.isspace():
                    continue       #not in mode_inrecord, and a space: ignore space between records.
                else:
                    mode_inrecord = 1
            if char in skip_char:    #after mode_quote, but before mode_escape!!
                continue
            if mode_escape:        #always append in escaped_mode
                mode_escape = 0
                value += char
                continue
            if not value:        #if no char in token: this is a new token, get line and pos for (new) token
                valueline = countline
                valuepos = countpos
            if char == quote_char:
                mode_quote = 1
                continue
            if char == escape:
                mode_escape = 1
                continue
            if char in field_sep:  #for tradacoms: record_tag_sep is appended to field_sep; in lexing they have the same function
                record += [{VALUE:value,SFIELD:sfield,LIN:valueline,POS:valuepos}]    #append element in record
                value = u''
                sfield = False
                continue
            if char == sfield_sep:
                record += [{VALUE:value,SFIELD:sfield,LIN:valueline,POS:valuepos}]    #append element in record
                value = u''
                sfield = True
                continue
            if char in record_sep:
                record += [{VALUE:value,SFIELD:sfield,LIN:valueline,POS:valuepos}]    #append element in record
                self.records += [record]    #write record to recordlist
                record = []
                value = u''
                sfield = False
                mode_inrecord = 0
                continue
            value += char    #just a char: append char to value
        #end of for-loop. all characters have been processed.
        #in a perfect world, value should always be empty now, but:
        #it appears a csv record is not always closed properly, so force the closing of the last record of csv file:
        if mode_inrecord and isinstance(self,csv) and self.ta_info['allow_lastrecordnotclosedproperly']:
            record += [{VALUE:value,SFIELD:sfield,LIN:valueline,POS:valuepos}]    #append element in record
            self.records += [record]    #write record to recordlist
        elif value.strip('\x00\x1a'):
            raise botslib.InMessageError(_(u'translation problem with lexing; probably a seperator-problem, or extra characters after interchange'))

    def _parsefields(self,record_in_edifile,structurerecord):
        ''' Identify fields in inmessage-record using grammar
            Build a record (dictionary; field-IDs are unique within record) and return this.
        '''
        recorddef = structurerecord[FIELDS]
        recordid = structurerecord[ID]
        recorddict = {}
        #****************** first: identify fields: assign field id to lexed fields
        tindex = -1     #elementcounter; composites count as one
        tsubindex = 0     #sub-element counter (within composite))
        for rfield in record_in_edifile:    #handle both fields and sub-fields
            if rfield[SFIELD]:
                tsubindex += 1
                try:
                    field = recorddef[tindex][SUBFIELDS][tsubindex]
                except TypeError:       #field has no SUBFIELDS
                    self.add2errorlist(_(u'[F17] Record "%(record)s" expect field but "%(content)s" is a subfield (line %(line)s position %(pos)s).\n')%{'line':rfield[LIN],'pos':rfield[POS],'record':structurerecord[MPATH],'content':rfield[VALUE]})
                    continue
                except IndexError:      #tsubindex is not in the subfields
                    self.add2errorlist(_(u'[F18] Record "%(record)s" too many subfields in composite; unknown subfield "%(content)s" (line %(line)s position %(pos)s).\n')%{'line':rfield[LIN],'pos':rfield[POS],'record':structurerecord[MPATH],'content':rfield[VALUE]})
                    continue
            else:
                tindex += 1
                try:
                    field = recorddef[tindex]
                except IndexError:
                    self.add2errorlist(_(u'[F19] Record "%(record)s" too many fields in record; unknown field "%(content)s" (line %(line)s position %(pos)s).\n')%{'line':rfield[LIN],'pos':rfield[POS],'record':structurerecord[MPATH],'content':rfield[VALUE]})
                    continue
                if not field[ISFIELD]: #if field is subfield according to grammar
                    tsubindex = 0
                    field = recorddef[tindex][SUBFIELDS][tsubindex]
            #*********if field has content: add to recorddictionary
            if recordid == 'ISA' and isinstance(self,x12):    #isa is an exception: no strip()
                value = rfield[VALUE]
            else:
                value = rfield[VALUE].strip()
            if value:
                recorddict[field[ID]] = value   #copy string to avoid memory problems
        return recorddict



class csv(var):
    ''' class for ediobjects with Comma Separated Values'''
    def _lex(self):
        super(csv,self)._lex()
        if self.ta_info['skip_firstline']:
            # if it is an integer, skip that many lines
            # if True, skip just the first line
            if isinstance(self.ta_info['skip_firstline'],int):
                del self.records[0:self.ta_info['skip_firstline']]
            else:
                del self.records[0]
        if self.ta_info['noBOTSID']:    #if read records contain no BOTSID: add it
            botsid = self.defmessage.structure[0][ID]   #add the recordname as BOTSID
            for record in self.records:
                record[0:0] = [{VALUE: botsid, POS: 0, LIN: 0, SFIELD: False}]


class edifact(var):
    ''' class for edifact inmessage objects.'''
    def _readcontent_edifile(self):
        ''' read content of edi file in memory.
            For edifact: not unicode. after sniffing unicode is used to check charset (UNOA etc)
            In sniff: determine charset; then decode according to charset
        '''
        botsglobal.logger.debug(u'read edi file "%s".',self.ta_info['filename'])
        self.rawinput = botslib.readdata(filename=self.ta_info['filename'],errors=self.ta_info['checkcharsetin'])

    def _sniff(self):
        ''' examine a read edifact file for syntax parameters and correctness: eg parse UNA, find UNB, get charset and version
        '''
        #**************look for UNA
        count = 0
        while True:
            if not self.rawinput[count].isspace():
                if self.rawinput[count:count+3] == 'UNA':
                    unacharset = True
                    self.ta_info['sfield_sep'] = self.rawinput[count+3]
                    self.ta_info['field_sep'] = self.rawinput[count+4]
                    self.ta_info['decimaal'] = self.rawinput[count+5]
                    self.ta_info['escape'] = self.rawinput[count+6]
                    self.ta_info['reserve'] = '' #self.rawinput[count+7]    #for now: no support of repeating dataelements
                    self.ta_info['record_sep'] = self.rawinput[count+8]
                    count += 9
                    while True:         #find first non-whitespace character
                        if not self.rawinput[count].isspace():
                            break
                        count += 1
                    else:
                        raise botslib.InMessageError(_(u'No "UNB" at the start of edifact file.'))
                else:
                    unacharset = False
                self.rawinput = self.rawinput[count:]  #self.rawinput[count] is a non-whitespace char, and it is not UNA. Look at p
                break
            count += 1
        else:
            raise botslib.InMessageError(_(u'Edifact file only contains whitespace.'))
        #**************expect UNB
        if self.rawinput[:3] == 'UNB':
            self.ta_info['charset'] = self.rawinput[4:8]
            self.ta_info['version'] = self.rawinput[9:10]
            if not unacharset:
                if self.rawinput[3] == '+' and self.rawinput[8] == ':':     #assume standard separators.
                    self.ta_info['sfield_sep'] = ':'
                    self.ta_info['field_sep'] = '+'
                    self.ta_info['decimaal'] = '.'
                    self.ta_info['escape'] = '?'
                    self.ta_info['reserve'] = ''    #for now: no support of repeating dataelements
                    self.ta_info['record_sep'] = "'"
                elif self.rawinput[3] == '\x1D' and self.rawinput[8] == '\x1F':     #check if UNOB separators are used
                    self.ta_info['sfield_sep'] = '\x1F'
                    self.ta_info['field_sep'] = '\x1D'
                    self.ta_info['decimaal'] = '.'
                    self.ta_info['escape'] = ''
                    self.ta_info['reserve'] = ''    #for now: no support of repeating dataelements
                    self.ta_info['record_sep'] = '\x1C'
                else:
                    raise botslib.InMessageError(_(u'Incoming edi file uses non-standard separators - should use UNA.'))
        else:
            raise botslib.InMessageError(_(u'No "UNB" at the start of edifact file.'))
        #*********** decode the file (to unicode)
        try:
            self.rawinput = self.rawinput.decode(self.ta_info['charset'],self.ta_info['checkcharsetin'])
        except LookupError:
            raise botslib.InMessageError(_(u'Incoming edifact file has unknown charset "$charset".'),charset=self.ta_info['charset'])
        except UnicodeDecodeError, msg:
            raise botslib.InMessageError(_(u'Not allowed chars in incoming edi file (for translation) at/after filepos: $content'),content=msg[2])

    def checkenvelope(self):
        self.confirmationlist = []              #information about the edifact file for confirmation/CONTRL; for edifact this is done per interchange (UNB-UNZ)
        for nodeunb in self.getloop({'BOTSID':'UNB'}):
            botsglobal.logmap.debug(u'Start parsing edifact envelopes')
            sender = nodeunb.get({'BOTSID':'UNB','S002.0004':None})
            receiver = nodeunb.get({'BOTSID':'UNB','S003.0010':None})
            unbreference = nodeunb.get({'BOTSID':'UNB','0020':None})
            unzreference = nodeunb.get({'BOTSID':'UNB'},{'BOTSID':'UNZ','0020':None})
            if unbreference and unzreference and unbreference != unzreference:
                self.add2errorlist(_(u'[E01] UNB-reference is "%(unbreference)s"; should be equal to UNZ-reference "%(unzreference)s".\n')%{'unbreference':unbreference,'unzreference':unzreference})
            unzcount = nodeunb.get({'BOTSID':'UNB'},{'BOTSID':'UNZ','0036':None})
            messagecount = len(nodeunb.children) - 1
            try:
                if int(unzcount) != messagecount:
                    self.add2errorlist(_(u'[E02] Count of messages in UNZ is %(unzcount)s; should be equal to number of messages %(messagecount)s.\n')%{'unzcount':unzcount,'messagecount':messagecount})
            except:
                self.add2errorlist(_(u'[E03] Count of messages in UNZ is invalid: "%(count)s".\n')%{'count':unzcount})
            self.confirmationlist.append({'unbreference':unbreference,'unzcount':unzcount,'sender':sender,'receiver':receiver,'UNHlist':[]})   #gather information about functional group (GS-GE)
            for nodeunh in nodeunb.getloop({'BOTSID':'UNB'},{'BOTSID':'UNH'}):
                unhtype = nodeunh.get({'BOTSID':'UNH','S009.0065':None})
                unhversion = nodeunh.get({'BOTSID':'UNH','S009.0052':None})
                unhrelease = nodeunh.get({'BOTSID':'UNH','S009.0054':None})
                unhcontrollingagency = nodeunh.get({'BOTSID':'UNH','S009.0051':None})
                unhassociationassigned = nodeunh.get({'BOTSID':'UNH','S009.0057':None})
                unhreference = nodeunh.get({'BOTSID':'UNH','0062':None})
                untreference = nodeunh.get({'BOTSID':'UNH'},{'BOTSID':'UNT','0062':None})
                if unhreference and untreference and unhreference != untreference:
                    self.add2errorlist(_(u'[E04] UNH-reference is "%(unhreference)s"; should be equal to UNT-reference "%(untreference)s".\n')%{'unhreference':unhreference,'untreference':untreference})
                untcount = nodeunh.get({'BOTSID':'UNH'},{'BOTSID':'UNT','0074':None})
                segmentcount = nodeunh.getcount()
                try:
                    if int(untcount) != segmentcount:
                        self.add2errorlist(_(u'[E05] Segmentcount in UNT is %(untcount)s; should be equal to number of segments %(segmentcount)s.\n')%{'untcount':untcount,'segmentcount':segmentcount})
                except:
                    self.add2errorlist(_(u'[E06] Count of segments in UNT is invalid: "%(count)s".\n')%{'count':untcount})
                self.confirmationlist[-1]['UNHlist'].append({'unhreference':unhreference,'unhtype':unhtype,'unhversion':unhversion,'unhrelease':unhrelease,'unhcontrollingagency':unhcontrollingagency,'unhassociationassigned':unhassociationassigned})   #add info per message to interchange
            for nodeung in nodeunb.getloop({'BOTSID':'UNB'},{'BOTSID':'UNG'}):
                ungreference = nodeung.get({'BOTSID':'UNG','0048':None})
                unereference = nodeung.get({'BOTSID':'UNG'},{'BOTSID':'UNE','0048':None})
                if ungreference and unereference and ungreference != unereference:
                    self.add2errorlist(_(u'[E07] UNG-reference is "%(ungreference)s"; should be equal to UNE-reference "%(unereference)s".\n')%{'ungreference':ungreference,'unereference':unereference})
                unecount = nodeung.get({'BOTSID':'UNG'},{'BOTSID':'UNE','0060':None})
                groupcount = len(nodeung.children) - 1
                try:
                    if int(unecount) != groupcount:
                        self.add2errorlist(_(u'[E08] Groupcount in UNE is %(unecount)s; should be equal to number of groups %(groupcount)s.\n')%{'unecount':unecount,'groupcount':groupcount})
                except:
                    self.add2errorlist(_(u'[E09] Groupcount in UNE is invalid: "%(count)s".')%{'count':unecount})
                for nodeunh in nodeung.getloop({'BOTSID':'UNG'},{'BOTSID':'UNH'}):
                    unhreference = nodeunh.get({'BOTSID':'UNH','0062':None})
                    untreference = nodeunh.get({'BOTSID':'UNH'},{'BOTSID':'UNT','0062':None})
                    if unhreference and untreference and unhreference != untreference:
                        self.add2errorlist(_(u'[E10] UNH-reference is "%(unhreference)s"; should be equal to UNT-reference "%(untreference)s".\n')%{'unhreference':unhreference,'untreference':untreference})
                    untcount = nodeunh.get({'BOTSID':'UNH'},{'BOTSID':'UNT','0074':None})
                    segmentcount = nodeunh.getcount()
                    try:
                        if int(untcount) != segmentcount:
                            self.add2errorlist(_(u'[E11] Segmentcount in UNT is %(untcount)s; should be equal to number of segments %(segmentcount)s.\n')%{'untcount':untcount,'segmentcount':segmentcount})
                    except:
                        self.add2errorlist(_(u'[E12] Count of segments in UNT is invalid: "%(count)s".\n')%{'count':untcount})
            botsglobal.logmap.debug(u'Parsing edifact envelopes is OK')

    def handleconfirm(self,ta_fromfile,error):
        ''' end of edi file handling.
            eg writing of confirmations etc.
            send CONTRL messages
            parameter 'error' is not used
        '''
        #filter the confirmationlist
        tmpconfirmationlist = []
        for confirmation in self.confirmationlist:
            tmpmessagelist = []
            for message_received in confirmation['UNHlist']:
                if message_received['unhtype'] == 'CONTRL': #do not generate CONTRL for a CONTRL message
                    continue
                if botslib.checkconfirmrules('send-edifact-CONTRL',idroute=self.ta_info['idroute'],idchannel=self.ta_info['fromchannel'],
                                                topartner=confirmation['sender'],frompartner=confirmation['receiver'],
                                                editype='edifact',messagetype=message_received['unhtype']):
                    tmpmessagelist.append(message_received)
            confirmation['UNHlist'] = tmpmessagelist
            if not tmpmessagelist: #if no messages/transactions in interchange
                continue
            tmpconfirmationlist.append(confirmation)
        self.confirmationlist = tmpconfirmationlist
        for confirmation in self.confirmationlist:
            reference = str(botslib.unique('messagecounter'))
            ta_confirmation = ta_fromfile.copyta(status=TRANSLATED,reference=reference)
            filename = str(ta_confirmation.idta)
            out = outmessage.outmessage_init(editype='edifact',messagetype='CONTRL22UNEAN002',filename=filename)    #make outmessage object
            out.ta_info['frompartner'] = confirmation['receiver']
            out.ta_info['topartner'] = confirmation['sender']
            out.put({'BOTSID':'UNH','0062':reference,'S009.0065':'CONTRL','S009.0052':'2','S009.0054':'2','S009.0051':'UN','S009.0057':'EAN002'})
            out.put({'BOTSID':'UNH'},{'BOTSID':'UCI','0083':'8','S002.0004':confirmation['sender'],'S003.0010':confirmation['sender'],'0020':confirmation['unbreference']}) #8: interchange received
            for message_received in confirmation['UNHlist']:
                lou = out.putloop({'BOTSID':'UNH'},{'BOTSID':'UCM'})
                lou.put({'BOTSID':'UCM','0083':'7','S009.0065':message_received['unhtype'],'S009.0052':message_received['unhversion'],'S009.0054':message_received['unhrelease'],'S009.0051':message_received['unhcontrollingagency'],'0062':message_received['unhreference']})
                lou.put({'BOTSID':'UCM','S009.0057':message_received['unhassociationassigned']})
            out.put({'BOTSID':'UNH'},{'BOTSID':'UNT','0074':out.getcount()+1,'0062':reference})  #last line (counts the segments produced in out-message)
            out.writeall()   #write tomessage (result of translation)
            botsglobal.logger.debug(u'Send edifact confirmation (CONTRL) route "%s" fromchannel "%s" frompartner "%s" topartner "%s".',
                self.ta_info['idroute'],self.ta_info['fromchannel'],confirmation['receiver'],confirmation['sender'])
            self.confirminfo = dict(confirmtype='send-edifact-CONTRL',confirmed=True,confirmasked = True,confirmidta=ta_confirmation.idta)  #this info is used in transform.py to update the ta.....ugly...
            ta_confirmation.update(statust=OK,**out.ta_info)    #update ta for confirmation


class x12(var):
    ''' class for edifact inmessage objects.'''
    @staticmethod
    def _getmessagetype(messagetypefromsubtranslation,inode):
        return messagetypefromsubtranslation +  inode.record['GS08']

    def _sniff(self):
        ''' examine a file for syntax parameters and correctness of protocol
            eg parse ISA, get charset and version
        '''
        #goto char that is not whitespace
        for count,char in enumerate(self.rawinput):
            if not char.isspace():
                self.rawinput = self.rawinput[count:]  #here the interchange should start
                break
        else:
            raise botslib.InMessageError(_(u'edifile only contains whitespace.'))
        if self.rawinput[:3] != 'ISA':
            raise botslib.InMessageError(_(u'expect "ISA", found "$content". Probably no x12?'),content=self.rawinput[:7])
        count = 0
        for char in self.rawinput[:120]:
            if char in '\r\n' and count != 105:
                continue
            count += 1
            if count == 4:
                self.ta_info['field_sep'] = char
            elif count == 105:
                self.ta_info['sfield_sep'] = char
            elif count == 106:
                self.ta_info['record_sep'] = char
                break
        # ISA-version: if <004030: SHOULD use repeating element?
        self.ta_info['reserve'] = ''
        self.ta_info['skip_char'] = self.ta_info['skip_char'].replace(self.ta_info['record_sep'],'') #if <CR> is segment terminator: cannot be in the skip_char-string!
        #more ISA's in file: find IEA+

    def checkenvelope(self):
        ''' check envelopes, gather information to generate 997 '''
        self.confirmationlist = []              #information about the x12 file for confirmation/997; for x12 this is done per functional group
        #~ self.root.display()
        for nodeisa in self.getloop({'BOTSID':'ISA'}):
            botsglobal.logmap.debug(u'Start parsing X12 envelopes')
            #~ sender = nodeisa.get({'BOTSID':'ISA','ISA06':None})
            #~ receiver = nodeisa.get({'BOTSID':'ISA','ISA08':None})
            isareference = nodeisa.get({'BOTSID':'ISA','ISA13':None})
            ieareference = nodeisa.get({'BOTSID':'ISA'},{'BOTSID':'IEA','IEA02':None})
            if isareference and ieareference and isareference != ieareference:
                self.add2errorlist(_(u'[E13] ISA-reference is "%(isareference)s"; should be equal to IEA-reference "%(ieareference)s".\n')%{'isareference':isareference,'ieareference':ieareference})
            ieacount = nodeisa.get({'BOTSID':'ISA'},{'BOTSID':'IEA','IEA01':None})
            groupcount = nodeisa.getcountoccurrences({'BOTSID':'ISA'},{'BOTSID':'GS'})
            try:
                if int(ieacount) != groupcount:
                    self.add2errorlist(_(u'[E14] Count in IEA-IEA01 is %(ieacount)s; should be equal to number of groups %(groupcount)s.\n')%{'ieacount':ieacount,'groupcount':groupcount})
            except:
                self.add2errorlist(_(u'[E15] Count of messages in IEA is invalid: "%(count)s".\n')%{'count':ieacount})
            for nodegs in nodeisa.getloop({'BOTSID':'ISA'},{'BOTSID':'GS'}):
                sender = nodegs.get({'BOTSID':'GS','GS02':None})
                receiver = nodegs.get({'BOTSID':'GS','GS03':None})
                gsqualifier = nodegs.get({'BOTSID':'GS','GS01':None})
                gsreference = nodegs.get({'BOTSID':'GS','GS06':None})
                gereference = nodegs.get({'BOTSID':'GS'},{'BOTSID':'GE','GE02':None})
                if gsreference and gereference and gsreference != gereference:
                    self.add2errorlist(_(u'[E16] GS-reference is "%(gsreference)s"; should be equal to GE-reference "%(gereference)s".\n')%{'gsreference':gsreference,'gereference':gereference})
                gecount = nodegs.get({'BOTSID':'GS'},{'BOTSID':'GE','GE01':None})
                messagecount = len(nodegs.children) - 1
                try:
                    if int(gecount) != messagecount:
                        self.add2errorlist(_(u'[E17] Count in GE-GE01 is %(gecount)s; should be equal to number of transactions: %(messagecount)s.\n')%{'gecount':gecount,'messagecount':messagecount})
                except:
                    self.add2errorlist(_(u'[E18] Count of messages in GE is invalid: "%(count)s".\n')%{'count':gecount})
                self.confirmationlist.append({'gsqualifier':gsqualifier,'gsreference':gsreference,'gecount':gecount,'sender':sender,'receiver':receiver,'STlist':[]})   #gather information about functional group (GS-GE)
                for nodest in nodegs.getloop({'BOTSID':'GS'},{'BOTSID':'ST'}):
                    stqualifier = nodest.get({'BOTSID':'ST','ST01':None})
                    streference = nodest.get({'BOTSID':'ST','ST02':None})
                    sereference = nodest.get({'BOTSID':'ST'},{'BOTSID':'SE','SE02':None})
                    #referencefields are numerical; should I compare values??
                    if streference and sereference and streference != sereference:
                        self.add2errorlist(_(u'[E19] ST-reference is "%(streference)s"; should be equal to SE-reference "%(sereference)s".\n')%{'streference':streference,'sereference':sereference})
                    secount = nodest.get({'BOTSID':'ST'},{'BOTSID':'SE','SE01':None})
                    segmentcount = nodest.getcount()
                    try:
                        if int(secount) != segmentcount:
                            self.add2errorlist(_(u'[E20] Count in SE-SE01 is %(secount)s; should be equal to number of segments %(segmentcount)s.\n')%{'secount':secount,'segmentcount':segmentcount})
                    except:
                        self.add2errorlist(_(u'[E21] Count of segments in SE is invalid: "%(count)s".\n')%{'count':secount})
                    self.confirmationlist[-1]['STlist'].append({'streference':streference,'stqualifier':stqualifier})   #add info per message to functional group
            botsglobal.logmap.debug(u'Parsing X12 envelopes is OK')

    def handleconfirm(self,ta_fromfile,error):
        ''' end of edi file handling.
            eg writing of confirmations etc.
            send 997 messages
            parameter 'error' is not used
        '''
        #filter the confirmationlist
        tmpconfirmationlist = []
        for confirmation in self.confirmationlist:
            if confirmation['gsqualifier'] == 'FA': #do not generate 997 for 997
                continue
            tmpmessagelist = []
            for message_received in confirmation['STlist']:
                if botslib.checkconfirmrules('send-x12-997',idroute=self.ta_info['idroute'],idchannel=self.ta_info['fromchannel'],
                                                topartner=confirmation['sender'],frompartner=confirmation['receiver'],
                                                editype='x12',messagetype=message_received['stqualifier']):
                    tmpmessagelist.append(message_received)
            confirmation['STlist'] = tmpmessagelist
            if not tmpmessagelist: #if no messages/transactions in GS-GE
                continue
            tmpconfirmationlist.append(confirmation)
        self.confirmationlist = tmpconfirmationlist
        for confirmation in self.confirmationlist:
            reference = str(botslib.unique('messagecounter')).zfill(4)    #20120411: use zfill as messagescounter can be <1000, ST02 field is min 4 positions
            ta_confirmation = ta_fromfile.copyta(status=TRANSLATED,reference=reference)
            filename = str(ta_confirmation.idta)
            out = outmessage.outmessage_init(editype='x12',messagetype='997004010',filename=filename)    #make outmessage object
            out.ta_info['frompartner'] = confirmation['receiver']
            out.ta_info['topartner'] = confirmation['sender']
            out.put({'BOTSID':'ST','ST01':'997','ST02':reference})
            out.put({'BOTSID':'ST'},{'BOTSID':'AK1','AK101':confirmation['gsqualifier'],'AK102':confirmation['gsreference']})
            out.put({'BOTSID':'ST'},{'BOTSID':'AK9','AK901':'A','AK902':confirmation['gecount'],'AK903':confirmation['gecount'],'AK904':confirmation['gecount']})
            for message_received in confirmation['STlist']:
                lou = out.putloop({'BOTSID':'ST'},{'BOTSID':'AK2'})
                lou.put({'BOTSID':'AK2','AK201':message_received['stqualifier'],'AK202':message_received['streference']})
                lou.put({'BOTSID':'AK2'},{'BOTSID':'AK5','AK501':'A'})
            out.put({'BOTSID':'ST'},{'BOTSID':'SE','SE01':out.getcount()+1,'SE02':reference})  #last line (counts the segments produced in out-message)
            out.writeall()   #write tomessage (result of translation)
            botsglobal.logger.debug(u'Send x12 confirmation (997) route "%s" fromchannel "%s" frompartner "%s" topartner "%s".',
                self.ta_info['idroute'],self.ta_info['fromchannel'],confirmation['receiver'],confirmation['sender'])
            self.confirminfo = dict(confirmtype='send-x12-997',confirmed=True,confirmasked = True,confirmidta=ta_confirmation.idta)  #this info is used in transform.py to update the ta.....ugly...
            ta_confirmation.update(statust=OK,**out.ta_info)    #update ta for confirmation


class tradacoms(var):
    def checkenvelope(self):
        for nodestx in self.getloop({'BOTSID':'STX'}):
            botsglobal.logmap.debug(u'Start parsing tradacoms envelopes')
            endcount = nodestx.get({'BOTSID':'STX'},{'BOTSID':'END','NMST':None})
            messagecount = len(nodestx.children) - 1
            try:
                if int(endcount) != messagecount:
                    self.add2errorlist(_(u'[E22] Count in END is %(endcount)s; should be equal to number of messages %(messagecount)s.\n')%{'endcount':endcount,'messagecount':messagecount})
            except:
                self.add2errorlist(_(u'[E23] Count of messages in END is invalid: "%(count)s".\n')%{'count':endcount})
            firstmessage = True
            for nodemhd in nodestx.getloop({'BOTSID':'STX'},{'BOTSID':'MHD'}):
                if firstmessage:    #
                    nodestx.queries = {'messagetype':nodemhd.queries['messagetype']}
                    firstmessage = False
                mtrcount = nodemhd.get({'BOTSID':'MHD'},{'BOTSID':'MTR','NOSG':None})
                segmentcount = nodemhd.getcount()
                try:
                    if int(mtrcount) != segmentcount:
                        self.add2errorlist(_(u'[E24] Count in MTR is %(mtrcount)s; should be equal to number of segments %(segmentcount)s.\n')%{'mtrcount':mtrcount,'segmentcount':segmentcount})
                except:
                    self.add2errorlist(_(u'[E25] Count of segments in MTR is invalid: "%(count)s".\n')%{'count':mtrcount})
            botsglobal.logmap.debug(u'Parsing tradacoms envelopes is OK')


class xml(var):
    ''' class for ediobjects in XML. Uses ElementTree'''
    def initfromfile(self):
        botsglobal.logger.debug(u'read edi file "%s".',self.ta_info['filename'])
        filename = botslib.abspathdata(self.ta_info['filename'])

        if self.ta_info['messagetype'] == 'mailbag':
                #~ the messagetype is not know.
                #~ bots reads file usersys/grammars/xml/mailbag.py, and uses 'mailbagsearch' to determine the messagetype
                #~ mailbagsearch is a list, containing python dicts. Dict consist of 'xpath', 'messagetype' and (optionally) 'content'.
                #~ 'xpath' is a xpath to use on xml-file (using elementtree xpath functionality)
                #~ if found, and 'content' in the dict; if 'content' is equal to value found by xpath-search, then set messagetype.
                #~ if found, and no 'content' in the dict; set messagetype.
            try:
                module,grammarname = botslib.botsimport('grammars','xml.mailbag')
                mailbagsearch = getattr(module, 'mailbagsearch')
            except AttributeError:
                botsglobal.logger.error(u'missing mailbagsearch in mailbag definitions for xml.')
                raise
            except ImportError:
                botsglobal.logger.error(u'missing mailbag definitions for xml, should be there.')
                raise
            parser = ET.XMLParser()
            try:
                extra_character_entity = getattr(module, 'extra_character_entity')
                for key,value in extra_character_entity.items():
                    parser.entity[key] = value
            except AttributeError:
                pass    #there is no extra_character_entity in the mailbag definitions, is OK.
            etree =  ET.ElementTree()   #ElementTree: lexes, parses, makes etree; etree is quite similar to bots-node trees but conversion is needed
            etreeroot = etree.parse(filename, parser)
            for item in mailbagsearch:
                if 'xpath' not in item or 'messagetype' not in item:
                    raise botslib.InMessageError(_(u'invalid search parameters in xml mailbag.'))
                #~ print 'search' ,item
                found = etree.find(item['xpath'])
                if found is not None:
                    #~ print '    found'
                    if 'content' in item and found.text != item['content']:
                        continue
                    self.ta_info['messagetype'] = item['messagetype']
                    #~ print '    found right messagedefinition'
                    #~ continue
                    break
            else:
                raise botslib.InMessageError(_(u'could not find right xml messagetype for mailbag.'))

            self.defmessage = grammar.grammarread(self.ta_info['editype'],self.ta_info['messagetype'])
            botslib.updateunlessset(self.ta_info,self.defmessage.syntax)    #write values from grammar to self.ta_info - unless these values are already set eg by sniffing
        else:
            self.defmessage = grammar.grammarread(self.ta_info['editype'],self.ta_info['messagetype'])
            botslib.updateunlessset(self.ta_info,self.defmessage.syntax)    #write values from grammar to self.ta_info - unless these values are already set eg by sniffing
            parser = ET.XMLParser()
            for key,value in self.ta_info['extra_character_entity'].items():
                parser.entity[key] = value
            etree =  ET.ElementTree()   #ElementTree: lexes, parses, makes etree; etree is quite similar to bots-node trees but conversion is needed
            etreeroot = etree.parse(filename, parser)
        self.stack = []
        self.root = self._etree2botstree(etreeroot)  #convert etree to bots-nodes-tree
        self.checkmessage(self.root,self.defmessage)

    def _etree2botstree(self,xmlnode):
        self.stack.append(xmlnode.tag)
        newnode = node.Node(record=self._etreenode2botstreenode(xmlnode))
        for xmlchildnode in xmlnode:   #for every node in mpathtree
            if self._isfield(xmlchildnode):    #if no child entities: treat as 'field': this misses xml where attributes are used as fields....testing for repeating is no good...
                if xmlchildnode.text and not xmlchildnode.text.isspace(): #skip empty xml entity
                    newnode.record[xmlchildnode.tag] = xmlchildnode.text      #add as a field
                    hastxt = True
                else:
                    hastxt = False
                for key,value in xmlchildnode.items():   #convert attributes to fields.
                    if not hastxt:
                        newnode.record[xmlchildnode.tag] = ''      #add empty content
                        hastxt = True
                    newnode.record[xmlchildnode.tag + self.ta_info['attributemarker'] + key] = value      #add as a field
            else:   #xmlchildnode is a record
                newnode.append(self._etree2botstree(xmlchildnode))           #add as a node/record
        #~ if botsglobal.ini.getboolean('settings','readrecorddebug',False):
            #~ botsglobal.logger.debug('read record "%s":',newnode.record['BOTSID'])
            #~ for key,value in newnode.record.items():
                #~ botsglobal.logger.debug('    "%s" : "%s"',key,value)
        self.stack.pop()
        #~ print self.stack
        return newnode

    def _etreenode2botstreenode(self,xmlnode):
        ''' build a dict from xml-node'''
        build = dict((xmlnode.tag + self.ta_info['attributemarker'] + key,value) for key,value in xmlnode.items())   #convert attributes to fields.
        build['BOTSID'] = xmlnode.tag     #'record' tag
        if xmlnode.text and not xmlnode.text.isspace():
            build['BOTSCONTENT'] = xmlnode.text
        return build

    def _isfield(self,xmlchildnode):
        ''' check if xmlchildnode is field (or record)'''
        #~ print 'examine record in stack',xmlchildnode.tag,self.stack
        str_recordlist = self.defmessage.structure
        for record in self.stack:   #find right level in structure
            for str_record in str_recordlist:
                #~ print '    find right level comparing',record,str_record[0]
                if record == str_record[0]:
                    if 4 not in str_record: #structure record contains no level: must be an attribute
                        return True
                    str_recordlist = str_record[4]
                    break
            else:
                raise botslib.InMessageError(_(u'Unknown XML-tag in "$record".'),record=record)
        for str_record in str_recordlist:   #see if xmlchildnode is in structure
            #~ print '    is xmlhildnode in this level comparing',xmlchildnode.tag,str_record[0]
            if xmlchildnode.tag == str_record[0]:
                #~ print 'found'
                return False
        #xml tag not found in structure: so must be field; validity is check later on with grammar
        if len(xmlchildnode)==0:
            return True
        return False

class xmlnocheck(xml):
    ''' class for ediobjects in XML. Uses ElementTree'''
    def checkmessage(self,node_instance,defmessage,subtranslation=False):
        pass

    def _isfield(self,xmlchildnode):
        if len(xmlchildnode) == 0:
            return True
        return False

class json(var):
    def initfromfile(self):
        self.defmessage = grammar.grammarread(self.ta_info['editype'],self.ta_info['messagetype'])
        botslib.updateunlessset(self.ta_info,self.defmessage.syntax)    #write values from grammar to self.ta_info - unless these values are already set eg by sniffing
        self._readcontent_edifile()

        jsonobject = simplejson.loads(self.rawinput)
        del self.rawinput
        if isinstance(jsonobject,list):
            self.root = node.Node()  #initialise empty node.
            self.root.children = self._dojsonlist(jsonobject,self._getrootid())   #fill root with children
            for child in self.root.children:
                if not child.record:    #sanity test: the children must have content
                    raise botslib.InMessageError(_(u'no usable content.'))
                self.checkmessage(child,self.defmessage)
        elif isinstance(jsonobject,dict):
            if len(jsonobject)==1 and isinstance(jsonobject.values()[0],dict):
                # best structure: {rootid:{id2:<dict, list>}}
                self.root = self._dojsonobject(jsonobject.values()[0],jsonobject.keys()[0])
            elif len(jsonobject)==1 and isinstance(jsonobject.values()[0],list) :
                #root dict has no name; use value from grammar for rootID; {id2:<dict, list>}
                self.root = node.Node(record={'BOTSID': self._getrootid()})  #initialise empty node.
                self.root.children = self._dojsonlist(jsonobject.values()[0],jsonobject.keys()[0])
            else:
                #~ print self._getrootid()
                self.root = self._dojsonobject(jsonobject,self._getrootid())
            if not self.root:
                raise botslib.InMessageError(_(u'no usable content.'))
            self.checkmessage(self.root,self.defmessage)
        else:
            #root in JSON is neither dict or list.
            raise botslib.InMessageError(_(u'Content must be a "list" or "object".'))

    def _getrootid(self):
        return self.defmessage.structure[0][ID]

    def _dojsonlist(self,jsonobject,name):
        lijst = [] #initialise empty list, used to append a listof (converted) json objects
        for i in jsonobject:
            if isinstance(i,dict):  #check list item is dict/object
                newnode = self._dojsonobject(i,name)
                if newnode:
                    lijst.append(newnode)
            elif self.ta_info['checkunknownentities']:
                raise botslib.InMessageError(_(u'List content in must be a "object".'))
        return lijst

    def _dojsonobject(self,jsonobject,name):
        thisnode = node.Node(record={'BOTSID':name})  #initialise empty node.
        for key,value in jsonobject.items():
            if value is None:
                continue
            elif isinstance(value,basestring):  #json field; map to field in node.record
                thisnode.record[key] = value
            elif isinstance(value,dict):
                newnode = self._dojsonobject(value,key)
                if newnode:
                    thisnode.append(newnode)
            elif isinstance(value,list):
                thisnode.children.extend(self._dojsonlist(value,key))
            elif isinstance(value,(int,long,float)):  #json field; map to field in node.record
                thisnode.record[key] = str(value)
            else:
                if self.ta_info['checkunknownentities']:
                    raise botslib.InMessageError(_(u'Key "$key" value "$value": is not string, list or dict.'),key=key,value=value)
                thisnode.record[key] = str(value)
        if len(thisnode.record)==2 and not thisnode.children:
            return None #node is empty...
        #~ thisnode.record['BOTSID']=name
        return thisnode


class jsonnocheck(json):
    def checkmessage(self,node_instance,defmessage,subtranslation=False):
        pass

    def _getrootid(self):
        return self.ta_info['defaultBOTSIDroot']   #as there is no structure in grammar, use value form syntax.


class database(jsonnocheck):
    pass


class db(Inmessage):
    ''' the database-object is unpickled, and passed to the mapping script.
    '''
    def initfromfile(self):
        botsglobal.logger.debug(u'read edi file "%s".',self.ta_info['filename'])
        filehandler = botslib.opendata(filename=self.ta_info['filename'],mode='rb')
        self.root = pickle.load(filehandler)
        filehandler.close()

    def nextmessage(self):
        yield self


class raw(Inmessage):
    ''' the file object is just read and passed to the mapping script.
    '''
    def initfromfile(self):
        botsglobal.logger.debug(u'read edi file "%s".',self.ta_info['filename'])
        filehandler = botslib.opendata(filename=self.ta_info['filename'],mode='rb')
        self.root = filehandler.read()
        filehandler.close()

    def nextmessage(self):
        yield self
