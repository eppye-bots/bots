''' Reading/lexing/parsing/splitting an edifile.'''
import time
#~ import sys
try:
    import cPickle as pickle
except ImportError:
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

def parse_edi_file(**ta_info):
    ''' Read,lex, parse edi-file. Is a dispatch function for Inmessage and subclasses.'''
    try:
        classtocall = globals()[ta_info['editype']]  #get inmessage class to call (subclass of Inmessage)
    except KeyError:
        raise botslib.InMessageError(_(u'Unknown editype for incoming message: %(editype)s'),ta_info)
    ediobject = classtocall(ta_info)
    ediobject.initfromfile()
    return ediobject

#*****************************************************************************
class Inmessage(message.Message):
    ''' abstract class for incoming ediobject (file or message).
        Can be initialised from a file or a tree.
    '''
    def __init__(self,ta_info):
        super(Inmessage,self).__init__()
        self.lex_records = []        #init list of lex_records
        self.ta_info = ta_info  #here ta_info is only filled with parameters from db-ta

    def initfromfile(self):
        ''' initialisation from a edi file '''
        self.messagegrammarread()
        self.ta_info['charset'] = self.defmessage.syntax['charset']      #always use charset of edi file.
        self._readcontent_edifile()
        self._sniff()           #some hard-coded parsing of edi file; ta_info can be overruled by syntax-parameters in edi-file
        #start lexing and parsing
        self._lex()
        if hasattr(self,'rawinput'):
            del self.rawinput
        #~ self.display(self.lex_records)   #show lexed lex_records (for protocol debugging)
        self.root = node.Node()  #make root Node None.
        self.iternextrecord = iter(self.lex_records)
        leftover = self._parse(structure_level=self.defmessage.structure,inode=self.root)
        if leftover:
            raise botslib.InMessageError(_(u'[A50] line %(line)s pos %(pos)s: Found non-valid data at end of edi file; probably a problem with separators or message structure.'),
                                            {'line':leftover[0][LIN], 'pos':leftover[0][POS]})
        del self.lex_records
        #end parsing; self.root is root of a tree (of nodes).
        
        self.checkenvelope()
        self.checkmessage(self.root,self.defmessage)
        #get queries-dict for parsed message; this is used to update in database
        if self.root.record:
            self.ta_info.update(self.root.queries)
        else:
            for childnode in self.root.children:
                self.ta_info.update(childnode.queries)
                break

    def handleconfirm(self,ta_fromfile,error):
        ''' end of edi file handling: writing of confirmations, etc.
        '''
        pass

    def _formatfield(self,value,field_definition,structure_record,node_instance):
        ''' Format of a field is checked and converted if needed.
            Input: value (string), field definition.
            Output: the formatted value (string)
            Parameters of self.ta_info are used: triad, decimaal
            for fixed field: same handling; length is not checked.
        '''
        if field_definition[BFORMAT] == 'A':
            if isinstance(self,var):  #check length fields in variable lex_records
                lenght = len(value)
                if lenght > field_definition[LENGTH]:
                    self.add2errorlist(_(u'[F05]%(linpos)s: Record "%(record)s" field "%(field)s" too big (max %(max)s): "%(content)s".\n')%
                                        {'linpos':node_instance.linpos(),'record':self.mpathformat(structure_record[MPATH]),'field':field_definition[ID],'content':value,'max':field_definition[LENGTH]})
                if lenght < field_definition[MINLENGTH]:
                    self.add2errorlist(_(u'[F06]%(linpos)s: Record "%(record)s" field "%(field)s" too small (min %(min)s): "%(content)s".\n')%
                                        {'linpos':node_instance.linpos(),'record':self.mpathformat(structure_record[MPATH]),'field':field_definition[ID],'content':value,'min':field_definition[MINLENGTH]})
        elif field_definition[BFORMAT] == 'D':
            try:
                lenght = len(value)
                if lenght == 6:
                    time.strptime(value,'%y%m%d')
                elif lenght == 8:
                    time.strptime(value,'%Y%m%d')
                else:
                    raise ValueError(u'To be catched')
            except ValueError:
                self.add2errorlist(_(u'[F07]%(linpos)s: Record "%(record)s" date field "%(field)s" not a valid date: "%(content)s".\n')%
                                    {'linpos':node_instance.linpos(),'record':self.mpathformat(structure_record[MPATH]),'field':field_definition[ID],'content':value})
        elif field_definition[BFORMAT] == 'T':
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
                self.add2errorlist(_(u'[F08]%(linpos)s: Record "%(record)s" time field "%(field)s" not a valid time: "%(content)s".\n')%
                                    {'linpos':node_instance.linpos(),'record':self.mpathformat(structure_record[MPATH]),'field':field_definition[ID],'content':value})
        else:   #numerics (R, N, I)
            #~ if not value:
                #~ if self.ta_info['acceptspaceinnumfield']:
                    #~ value='0'
                #~ else:
                    #~ self.add2errorlist(_(u'[13]%(linpos)s: Record "%(record)s" field "%(field)s" has numeric format but contains only space.\n')%
                                        #~ {'linpos':node_instance.linpos(),'record':self.mpathformat(structure_record[MPATH]),'field':field_definition[ID]})
                #~ return ''   #when num field has spaces as content, spaces are stripped. Field should be numeric.
            if value[-1] == u'-':    #if minus-sign at the end, put it in front.
                value = value[-1] + value[:-1]
            value = value.replace(self.ta_info['triad'],u'')     #strip triad-separators
            value = value.replace(self.ta_info['decimaal'],u'.',1) #replace decimal sign by canonical decimal sign
            if 'E' in value or 'e' in value:
                self.add2errorlist(_(u'[F09]%(linpos)s: Record "%(record)s" field "%(field)s" contains exponent: "%(content)s".\n')%
                                    {'linpos':node_instance.linpos(),'record':self.mpathformat(structure_record[MPATH]),'field':field_definition[ID],'content':value})
            if isinstance(self,var):  #check length num fields in variable lex_records
                if self.ta_info['lengthnumericbare']:
                    length = botslib.countunripchars(value,'-+.')
                else:
                    length = len(value)
                if length > field_definition[LENGTH]:
                    self.add2errorlist(_(u'[F10]%(linpos)s: Record "%(record)s" field "%(field)s" too big (max %(max)s): "%(content)s".\n')%
                                        {'linpos':node_instance.linpos(),'record':self.mpathformat(structure_record[MPATH]),'field':field_definition[ID],'content':value,'max':field_definition[LENGTH]})
                if length < field_definition[MINLENGTH]:
                    self.add2errorlist(_(u'[F11]%(linpos)s: Record "%(record)s" field "%(field)s" too small (min %(min)s): "%(content)s".\n')%
                                        {'linpos':node_instance.linpos(),'record':self.mpathformat(structure_record[MPATH]),'field':field_definition[ID],'content':value,'min':field_definition[MINLENGTH]})
            if field_definition[BFORMAT] == 'I':
                if '.' in value:
                    self.add2errorlist(_(u'[F12]%(linpos)s: Record "%(record)s" field "%(field)s" has format "I" but contains decimal sign: "%(content)s".\n')%
                                        {'linpos':node_instance.linpos(),'record':self.mpathformat(structure_record[MPATH]),'field':field_definition[ID],'content':value})
                else:
                    try:    #convert to decimal in order to check validity
                        valuedecimal = float(value)
                        valuedecimal = valuedecimal / 10**field_definition[DECIMALS]
                        value = '%.*F'%(field_definition[DECIMALS],valuedecimal)
                    except:
                        self.add2errorlist(_(u'[F13]%(linpos)s: Record "%(record)s" numeric field "%(field)s" has non-numerical content: "%(content)s".\n')%
                                            {'linpos':node_instance.linpos(),'record':self.mpathformat(structure_record[MPATH]),'field':field_definition[ID],'content':value})
            elif field_definition[BFORMAT] == 'N':
                lendecimal = len(value[value.find('.'):])-1
                if lendecimal != field_definition[DECIMALS]:
                    self.add2errorlist(_(u'[F14]%(linpos)s: Record "%(record)s" numeric field "%(field)s" has invalid nr of decimals: "%(content)s".\n')%
                                        {'linpos':node_instance.linpos(),'record':self.mpathformat(structure_record[MPATH]),'field':field_definition[ID],'content':value})
                try:    #convert to decimal in order to check validity
                    valuedecimal = float(value)
                    value = '%.*F'%(lendecimal,valuedecimal)
                except:
                    self.add2errorlist(_(u'[F15]%(linpos)s: Record "%(record)s" numeric field "%(field)s" has non-numerical content: "%(content)s".\n')%
                                        {'linpos':node_instance.linpos(),'record':self.mpathformat(structure_record[MPATH]),'field':field_definition[ID],'content':value})
            elif field_definition[BFORMAT] == 'R':
                lendecimal = len(value[value.find('.'):])-1
                try:    #convert to decimal in order to check validity
                    valuedecimal = float(value)
                    value = '%.*F'%(lendecimal,valuedecimal)
                except:
                    self.add2errorlist(_(u'[F16]%(linpos)s: Record "%(record)s" numeric field "%(field)s" has non-numerical content: "%(content)s".\n')%
                                        {'linpos':node_instance.linpos(),'record':self.mpathformat(structure_record[MPATH]),'field':field_definition[ID],'content':value})
        return value

    def _parse(self,structure_level,inode):
        ''' This is the heart of the parsing of incoming messages (but not for xml, json)
            Read the lex_records one by one (self.iternextrecord, is an iterator)
            - parse the lex_records.
            - identify record (lookup in structure)
            - identify fields in the record (use the record_definition from the grammar).
            - add grammar-info to lex_records: field-tag,mpath.
            Parameters:
            - structure_level: current grammar/segmentgroup of the grammar-structure.
            - inode: parent node; all parsed lex_records are added as children of inode
            2x recursive: SUBTRANSLATION and segmentgroups
        '''
        structure_index = 0     #keep track of where we are in the structure_level
        countnrofoccurences = 0 #number of occurences of current record in structure
        structure_end = len(structure_level)
        get_next_edi_record = True      #indicate if the next record should be fetched, or if the current_edi_record is still being parsed.
                                        #it might seem logical to test here 'current_edi_record is None', but this is already used to indicate 'no more lex_records'.
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
                        raise botslib.InMessageError(self.messagetypetxt + _(u'[S50]: Line:%(line)s pos:%(pos)s record:"%(record)s": message has an error in its structure; this record is not allowed here. Scanned in message definition until mandatory record: "%(looked)s".'),
                                                                            {'record':current_edi_record[ID][VALUE],'line':current_edi_record[ID][LIN],'pos':current_edi_record[ID][POS],'looked':structure_level[structure_index][MPATH]})
                    except TypeError:       #when no UNZ (edifact)
                        raise botslib.InMessageError(self.messagetypetxt + _(u'[S51]: Missing mandatory record "%(record)s".'),
                                                                            {'record':self.mpathformat(structure_level[structure_index][MPATH])})
                structure_index += 1
                if structure_index == structure_end:  #current_edi_record is not in this level. Go level up
                    return current_edi_record    #return either None (no more data-lex_records to parse) or the last record2parse (the last record2parse is not found in this level)
                countnrofoccurences = 0
                continue  #continue while-loop: get_next_edi_record is false as no match with structure is made; go and look at next record of structure
            #record is found in grammar
            countnrofoccurences += 1
            newnode = node.Node(record=self._parsefields(current_edi_record,structure_level[structure_index]),
                                botsidnr=structure_level[structure_index][BOTSIDNR],
                                pos=current_edi_record[0][POS],
                                line=current_edi_record[0][LIN])  #make new node
            inode.append(newnode)   #succes! append new node as a child to current (parent)node
            if SUBTRANSLATION in structure_level[structure_index]:
                # start a SUBTRANSLATION; find the right messagetype, etc
                messagetype = newnode.enhancedget(structure_level[structure_index][SUBTRANSLATION])
                if not messagetype:
                    raise botslib.TranslationNotFoundError(_(u'Could not find SUBTRANSLATION "%(sub)s" in (sub)message.'),
                                                            {'sub':structure_level[structure_index][SUBTRANSLATION]})
                messagetype = self._manipulatemessagetype(messagetype,inode)
                try:
                    defmessage = grammar.grammarread(self.__class__.__name__,messagetype)
                except ImportError:
                    raisenovalidmapping_error = True
                    if hasattr(self.defmessage.module,'getmessagetype'):
                        messagetype2 = botslib.runscript(self.defmessage.module,self.defmessage.grammarname,'getmessagetype',editype=self.__class__.__name__,messagetype=messagetype)
                        if messagetype2:
                            try:
                                defmessage = grammar.grammarread(self.__class__.__name__,messagetype2)
                                raisenovalidmapping_error = False
                            except ImportError:
                                pass
                    if raisenovalidmapping_error:
                        raise botslib.TranslationNotFoundError(_(u'No (valid) grammar for editype "%(editype)s" messagetype "%(messagetype)s".'),
                                                                {'editype':self.__class__.__name__,'messagetype':messagetype})
                self.messagecount += 1
                self.messagetypetxt = _(u'Message nr %(count)s, type %(type)s, '%{'count':self.messagecount,'type':messagetype})
                current_edi_record = self._parse(structure_level=defmessage.structure[0][LEVEL],inode=newnode)
                newnode.queries = {'messagetype':messagetype}       #copy messagetype into 1st segment of subtranslation (eg UNH, ST)
                self.checkmessage(newnode,defmessage,subtranslation=True)      #check the results of the subtranslation
                #~ end SUBTRANSLATION
                self.messagetypetxt = ''
                # get_next_edi_record is still False; we are trying to match the last (not matched) record from the SUBTRANSLATION (named 'current_edi_record').
            else:
                if LEVEL in structure_level[structure_index]:        #if header, go parse segmentgroup (recursive)
                    current_edi_record = self._parse(structure_level=structure_level[structure_index][LEVEL],inode=newnode)
                    # get_next_edi_record is still False; the current_edi_record that was not matched in lower segmentgroups is still being parsed.
                else:
                    get_next_edi_record = True
                #accomodate for UNS = UNS construction
                if structure_level[structure_index][MIN]==structure_level[structure_index][MAX]==countnrofoccurences:
                    #~ print 'tabel',structure_level[structure_index][ID],'message',current_edi_record[ID][VALUE],structure_index,structure_end
                    if structure_index +1 == structure_end:
                        pass
                    else:
                        structure_index += 1
                        countnrofoccurences = 0

    @staticmethod
    def _manipulatemessagetype(messagetype,inode):
        ''' default: just return messagetype. ''' 
        return messagetype


    def _readcontent_edifile(self):
        ''' read content of edi file to memory.
        '''
        botsglobal.logger.debug(u'read edi file "%(filename)s".',self.ta_info)
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
                ta_info['bots_accessenvelope']=self.root   #give mappingscript access to envelope
                yield self._getmessagefromenvelope(eachmessage,ta_info)
            if self.defmessage.nextmessage2 is not None:        #edifact needs nextmessage2...OK
                first = True
                for eachmessage in self.getloop(*self.defmessage.nextmessage2):
                    if first:
                        self.root.processqueries({},len(self.defmessage.nextmessage2))
                        first = False
                    ta_info = self.ta_info.copy()
                    ta_info.update(eachmessage.queries)
                    ta_info['bots_accessenvelope']=self.root   #give mappingscript access to envelope
                    yield self._getmessagefromenvelope(eachmessage,ta_info)
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
                    ta_info['bots_accessenvelope']=self.root      #give mappingscript access to envelope
                    yield self._getmessagefromenvelope(newroot,ta_info)
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
                    ta_info['bots_accessenvelope']=self.root       #give mappingscript access to envelope
                    yield self._getmessagefromenvelope(newroot,ta_info)
        else:   #no split up indicated in grammar;
            if self.root.record or self.ta_info['pass_all']:    #if contains root-record or explicitly indicated (csv): pass whole tree
                ta_info = self.ta_info.copy()
                ta_info.update(self.root.queries)
                ta_info['bots_accessenvelope']=self.root   #give mappingscript access to envelop
                yield self._getmessagefromenvelope(self.root,ta_info)
            else:   #pass nodes under root one by one
                for child in self.root.children:
                    ta_info = self.ta_info.copy()
                    ta_info.update(child.queries)
                    ta_info['bots_accessenvelope']=self.root   #give mappingscript access to envelope
                    yield self._getmessagefromenvelope(child,ta_info)
                    
    def _getmessagefromenvelope(self,inode,ta_info):
        ''' Get a edi-message (inmessage-object) from node in tree.
            is used in splitting edi-messages.'''
        classtocall = globals()[self.__class__.__name__]
        messagefromenvelope = classtocall(ta_info)
        messagefromenvelope.root = inode
        return messagefromenvelope


class fixed(Inmessage):
    ''' class for record of fixed length.'''
    def _readcontent_edifile(self):
        ''' read content of edi file to memory.
        '''
        botsglobal.logger.debug(u'read edi file "%(filename)s".',self.ta_info)
        self.filehandler = botslib.opendata(filename=self.ta_info['filename'],mode='rb',charset=self.ta_info['charset'],errors=self.ta_info['checkcharsetin'])

    def _lex(self):
        ''' lexes file with fixed lex_records to list of lex_records (self.lex_records).'''
        linenr = 0
        startrecordid = self.ta_info['startrecordID']
        endrecordid = self.ta_info['endrecordID']
        for line in self.filehandler:
            linenr += 1
            if not line.isspace():
                line = line.rstrip('\r\n')
                self.lex_records += [ [{VALUE:line[startrecordid:endrecordid].strip(),LIN:linenr,POS:0,FIXEDLINE:line}] ]    #append record to recordlist

    def _parsefields(self,lex_record,record_definition):
        ''' Parse fields from one fixed message-record and check length of the fixed record.
        '''
        record2build = {} #start with empty dict
        fixedrecord = lex_record[ID][FIXEDLINE]  #shortcut to fixed incoming record
        lenfixed = len(fixedrecord)
        recordlength = record_definition[F_LENGTH]
        if recordlength != lenfixed:
            if recordlength > lenfixed and self.ta_info['checkfixedrecordtooshort']:
                raise botslib.InMessageError(_(u'[S52] line %(line)s: Record "%(record)s" too short; is %(pos)s pos, defined is %(defpos)s pos.'),
                                                line=lex_record[ID][LIN],record=lex_record[ID][VALUE],pos=lenfixed,defpos=recordlength)
            if recordlength < lenfixed and self.ta_info['checkfixedrecordtoolong']:
                raise botslib.InMessageError(_(u'[S53] line %(line)s: Record "%(record)s" too long; is %(pos)s pos, defined is %(defpos)s pos.'),
                                                line=lex_record[ID][LIN],record=lex_record[ID][VALUE],pos=lenfixed,defpos=recordlength)
        pos = 0
        for field_definition in record_definition[FIELDS]:
            value = fixedrecord[pos:pos+field_definition[LENGTH]].strip()   #copy string to avoid memory problem
            if value:
                record2build[field_definition[ID]] = value
            pos += field_definition[LENGTH]
        return record2build


class idoc(fixed):
    ''' class for idoc ediobjects.
        for incoming the same as fixed.
        SAP does strip all empty fields for record; is catered for in grammar.defaultsyntax
    '''
    pass
    

class var(Inmessage):
    ''' abstract class for edi-objects with lex_records of variabele length.'''
    def _lex(self):
        ''' lexes file with variable lex_records to list of lex_records, fields and subfields (build self.lex_records).'''
        record_sep  = self.ta_info['record_sep']
        mode_inrecord = 0  # 1 indicates: lexing in record, 0 is lexing 'between lex_records'.
        field_sep   = self.ta_info['field_sep'] + self.ta_info['record_tag_sep']    #for tradacoms; field_sep and record_tag_sep have same function.
        sfield_sep  = self.ta_info['sfield_sep']
        rep_sep     = self.ta_info['reserve']
        sfield      = 0 # 1: subfield, 0: not a subfield, 2:repeat
        quote_char  = self.ta_info['quote_char']  #typical fo csv. example with quote_char ":  ,"1523",TEXT,"123", 
        mode_quote  = 0    #0=not in quote, 1=in quote
        mode_2quote = 0    #status within mode_quote. 0=just another char within quote, 1=met 2nd quote char; might be end of quote OR escaping of another quote-char.
        escape      = self.ta_info['escape']      #char after escape-char is not interpreted as separator
        mode_escape = 0    #0=not escaping, 1=escaping
        skip_char   = self.ta_info['skip_char']   #chars to ignore/skip/discard. eg edifact: if wrapped to 80pos lines and <CR/LF> at end of segment
        record      = []   #gather the content of a record
        value       = u''  #gather the content of (sub)field; the current token
        valueline   = 1    #record line of token
        valuepos    = 1    #record position of token in line
        countline   = 1    #count number of lines; start with 1
        countpos    = 0    #count position/number of chars within line

        for char in self.rawinput:    #get next char
            #just count number lines/position; no action.
            if char == u'\n':
                countline += 1      #count line
                countpos = 0        #position back to 0
            else:
                countpos += 1       #position within line
            #lexing within a quote; note that quote-char works as escape-char within a quote
            if mode_quote:
                if mode_2quote:
                    mode_2quote = 0
                    if char == quote_char: #after quote-char another quote-char: used to escape quote_char:
                        value += char    #append quote_char
                        continue
                    else: #quote is ended:
                        mode_quote = 0
                        #continue parsing of this char
                elif mode_escape:        #tricky: escaping a quote char
                    mode_escape = 0
                    value += char
                    continue
                elif char == quote_char:    #either end-quote or escaping quote_char,we do not know yet
                    mode_2quote = 1
                    continue
                elif char == escape:
                    mode_escape = 1
                    continue
                else:                       #we are in quote, just append char to token
                    value += char
                    continue
            #handle char 'between' lex_records. 
            if not mode_inrecord:
                if char.isspace():  #if space: ignor char, get next char. note: whitespace = ' \t\n\r\v\f'
                    continue
                mode_inrecord = 1   #not whitespace so a new record is started
            #check if char needs to be skipped. In csv these chars could be in a quote; in eg edifact chars will be skipped, even if after escape sign.
            if char in skip_char:
                continue
            #in escaped_mode: char after escape sign is appended to token 
            if mode_escape:
                mode_escape = 0
                value += char
                continue
            #if no char in token: this is a new token, get line and pos for (new) token
            if not value:        
                valueline = countline
                valuepos = countpos
            #for csv: handle new quote value. New quote value only makes sense for new field (value is empty) or field contains only whitespace 
            if char == quote_char and (not value or value.isspace()):
                mode_quote = 1
                continue
            if char == escape:
                mode_escape = 1
                continue
            #end of (sub)field. Note: first field of composite is marked as 'field'
            if char in field_sep:
                record += [{VALUE:value,SFIELD:sfield,LIN:valueline,POS:valuepos}]    #write current token to record
                value = u''
                sfield = 0      #new token is field
                continue
            #end of (sub)field. Note: first field of composite is marked as 'field'
            if char == sfield_sep:
                record += [{VALUE:value,SFIELD:sfield,LIN:valueline,POS:valuepos}]    #write current token to record
                value = u''
                sfield = 1        #new token is sub-field
                continue
            if char == rep_sep:
                record += [{VALUE:value,SFIELD:sfield,LIN:valueline,POS:valuepos}]    #write current token to record
                value = u''
                sfield = 2        #new token is sub-field
                continue
            #end of record
            if char in record_sep:
                record += [{VALUE:value,SFIELD:sfield,LIN:valueline,POS:valuepos}]    #write current token to record
                self.lex_records += [record]    #write record to recordlist
                record = []
                mode_inrecord = 0    #    
                value = u''
                sfield = 0      #new token is field 
                continue
            value += char    #just a char: append char to value
        #end of for-loop. all characters have been processed.
        #in a perfect world, value should always be empty now, but:
        #it appears a csv record is not always closed properly, so force the closing of the last record of csv file:
        if mode_inrecord and isinstance(self,csv) and self.ta_info['allow_lastrecordnotclosedproperly']:
            record += [{VALUE:value,SFIELD:sfield,LIN:valueline,POS:valuepos}]    #append element in record
            self.lex_records += [record]    #write record to recordlist
        else:
            leftover = value.strip('\x00\x1a')
            if leftover:
                raise botslib.InMessageError(_(u'[A51]: Found non-valid data at end of edi file; probably a problem with separators or message structure: "%(leftover)s".'),
                                                {'leftover':leftover})

    def _parsefields(self,lex_record,record_definition):
        ''' Identify the fields in inmessage-record using the record_definition from the grammar
            Build a record (dictionary; field-IDs are unique within record) and return this.
        '''
        list_of_fields_in_record_definition = record_definition[FIELDS]
        if record_definition[ID] == 'ISA' and isinstance(self,x12):    #isa is an exception: no strip()
            is_x12_ISA = True
        else:
            is_x12_ISA = False
        record2build = {}         #record that is build from lex_record using ID's from record_definition
        tindex = -1     #elementcounter; composites count as one
        #~ tsubindex = 0     #sub-element counter within composite; for files that are OK: init when compostie is detected. This init is for error (field is lexed as subfield but is not.) 20130222: catch UnboundLocalError now
        #********loop over all fields present in this record of edi file
        #********identify the lexed fields in grammar, and build a dict with (fieldID:value)
        for lex_field in lex_record:
            value = lex_field[VALUE].strip() if not is_x12_ISA else lex_field[VALUE][:]                        
            #*********use info of lexer: what is preceding separator (field, sub-field, repeat) 
            if not lex_field[SFIELD]:       #preceded by field-separator
                try:
                    tindex += 1                 #use next field
                    field_definition = list_of_fields_in_record_definition[tindex]
                except IndexError:
                    self.add2errorlist(_(u'[F19] line %(line)s pos %(pos)s: Record "%(record)s" too many fields in record; unknown field "%(content)s".\n')%
                                        {'content':lex_field[VALUE],'line':lex_field[LIN],'pos':lex_field[POS],'record':self.mpathformat(record_definition[MPATH])})
                    continue
                if field_definition[MAXREPEAT] == 1: #definition says: not repeating 
                    if field_definition[ISFIELD]:    #definition says: field       +E+
                        if value:
                            record2build[field_definition[ID]] = value
                    else:                                      #definition says: subfield    +E:S+
                        tsubindex = 0
                        list_of_subfields_in_record_definition = list_of_fields_in_record_definition[tindex][SUBFIELDS]
                        sub_field_in_record_definition = list_of_subfields_in_record_definition[tsubindex]
                        if value:
                            record2build[sub_field_in_record_definition[ID]] = value
                else:   #definition says: repeating 
                    if field_definition[ISFIELD]:      #definition says: field      +E*R+
                        record2build[field_definition[ID]] = [value]
                    else:                                        #definition says: subfield   +E:S*R:S+
                        tsubindex = 0
                        list_of_subfields_in_record_definition = list_of_fields_in_record_definition[tindex][SUBFIELDS]
                        sub_field_in_record_definition = list_of_subfields_in_record_definition[tsubindex]
                        record2build[field_definition[ID]] = [{sub_field_in_record_definition[ID]:value},]
            elif lex_field[SFIELD] == 1:    #preceded by sub-field separator
                try:
                    tsubindex += 1
                    sub_field_in_record_definition = list_of_subfields_in_record_definition[tsubindex]
                except (TypeError,UnboundLocalError):       #field has no SUBFIELDS, or unexpected subfield
                    self.add2errorlist(_(u'[F17] line %(line)s pos %(pos)s: Record "%(record)s" expect field but "%(content)s" is a subfield.\n')%
                                        {'content':lex_field[VALUE],'line':lex_field[LIN],'pos':lex_field[POS],'record':self.mpathformat(record_definition[MPATH])})
                    continue
                except IndexError:      #tsubindex is not in the subfields
                    self.add2errorlist(_(u'[F18] line %(line)s pos %(pos)s: Record "%(record)s" too many subfields in composite; unknown subfield "%(content)s".\n')%
                                          {'content':lex_field[VALUE],'line':lex_field[LIN],'pos':lex_field[POS],'record':self.mpathformat(record_definition[MPATH])})
                    continue
                if field_definition[MAXREPEAT] == 1: #definition says: not repeating   +E:S+
                    if value:
                        record2build[sub_field_in_record_definition[ID]] = value
                else:                                          #definition says: repeating       +E:S*R:S+
                    record2build[field_definition[ID]][-1][sub_field_in_record_definition[ID]] = value
            else:                         #  preceded by repeat separator
                #check if repeating!
                if field_definition[MAXREPEAT] == 1:
                    self.add2errorlist(_(u'[F??] line %(line)s pos %(pos)s: Record "%(record)s" expect not-repeating elemen, but "%(content)s" is repeating.\n')%
                                          {'content':lex_field[VALUE],'line':lex_field[LIN],'pos':lex_field[POS],'record':self.mpathformat(record_definition[MPATH])})
                    continue
                if field_definition[ISFIELD]:      #definition says: field      +E*R+
                    record2build[field_definition[ID]].append(value)
                else:                                        #definition says: first subfield   +E:S*R:S+
                    tsubindex = 0
                    list_of_subfields_in_record_definition = list_of_fields_in_record_definition[tindex][SUBFIELDS]
                    sub_field_in_record_definition = list_of_subfields_in_record_definition[tsubindex]
                    record2build[field_definition[ID]].append({sub_field_in_record_definition[ID]:value})
        return record2build
        
class csv(var):
    ''' class for ediobjects with Comma Separated Values'''
    def _lex(self):
        super(csv,self)._lex()
        if self.ta_info['skip_firstline']:
            # if it is an integer, skip that many lines
            # if True, skip just the first line
            if isinstance(self.ta_info['skip_firstline'],int):
                del self.lex_records[0:self.ta_info['skip_firstline']]
            else:
                del self.lex_records[0]
        if self.ta_info['noBOTSID']:    #if read lex_records contain no BOTSID: add it
            botsid = self.defmessage.structure[0][ID]   #add the recordname as BOTSID
            for lex_record in self.lex_records:
                lex_record[0:0] = [{VALUE: botsid, POS: 0, LIN: 0, SFIELD: 0}]

class excel(csv):
    def initfromfile(self):
        ''' initialisation from an excel file.
            file is first converted to csv using python module xlrd
        '''
        try:
            self.xlrd = __import__('xlrd')
        except ImportError:
            raise ImportError(_(u'Dependency failure: editype "excel" requires python library "xlrd".'))
        import csv
        import StringIO
        
        self.messagegrammarread()
        self.ta_info['charset'] = self.defmessage.syntax['charset']      #always use charset of edi file.
        if self.ta_info['escape']:
            doublequote = False
        else:
            doublequote = True
        
        botsglobal.logger.debug(u'read edi file "%(filename)s".',self.ta_info)
        #xlrd reads excel file; python's csv modules write this to file-like StringIO (as utf-8); read StringIO as self.rawinput; decode this (utf-8->unicode)
        infilename = botslib.abspathdata(self.ta_info['filename'])
        try:
            xlsdata = self.read_xls(infilename)
        except:
            txt = botslib.txtexc()
            botsglobal.logger.error(_(u'Excel extraction failed, may not be an Excel file? Error:\n%(txt)s'),
                                            {'txt':txt})
            raise botslib.InMessageError(_(u'Excel extraction failed, may not be an Excel file? Error:\n%(txt)s'),
                                            {'txt':txt})
        rawinputfile = StringIO.StringIO()
        csvout = csv.writer(rawinputfile, quotechar=self.ta_info['quote_char'], delimiter=self.ta_info['field_sep'], doublequote=doublequote, escapechar=self.ta_info['escape'])
        csvout.writerows( map(self.utf8ize, xlsdata) )
        rawinputfile.seek(0)
        self.rawinput = rawinputfile.read()
        rawinputfile.close()
        self.rawinput = self.rawinput.decode('utf-8')
        #start lexing and parsing as csv
        self._lex()
        if hasattr(self,'rawinput'):
            del self.rawinput
        self.root = node.Node()  #make root Node None.
        self.iternextrecord = iter(self.lex_records)
        leftover = self._parse(structure_level=self.defmessage.structure,inode=self.root)
        if leftover:
            raise botslib.InMessageError(_(u'[A52]: Found non-valid data at end of excel file: "%(leftover)s".'),
                                            {'leftover':leftover})
        del self.lex_records
        self.checkmessage(self.root,self.defmessage)

    def read_xls(self,infilename):
        # Read excel first sheet into a 2-d array
        book       = self.xlrd.open_workbook(infilename)
        sheet      = book.sheet_by_index(0)
        formatter  = lambda(t,v): self.format_excelval(book,t,v,False)
        xlsdata = []
        for row in range(sheet.nrows):
            (types, values) = (sheet.row_types(row), sheet.row_values(row))
            xlsdata.append(map(formatter, zip(types, values)))
        return xlsdata
    #-------------------------------------------------------------------------------
    def format_excelval(self,book,datatype,value,wanttupledate):
        #  Convert excel data for some data types
        if datatype == 2:
            if value == int(value):
                value = int(value)
        elif datatype == 3:
            datetuple = self.xlrd.xldate_as_tuple(value, book.datemode)
            value = datetuple if wanttupledate else self.tupledate_to_isodate(datetuple)
        elif datatype == 5:
            value = self.xlrd.error_text_from_code[value]
        return value
    #-------------------------------------------------------------------------------
    def tupledate_to_isodate(self,tupledate):
        # Turns a gregorian (year, month, day, hour, minute, nearest_second) into a
        # standard YYYY-MM-DDTHH:MM:SS ISO date.
        (y,m,d, hh,mm,ss) = tupledate
        nonzero = lambda n: n != 0
        datestring = "%04d-%02d-%02d"  % (y,m,d)    if filter(nonzero,(y,m,d)) else ''
        timestring = "T%02d:%02d:%02d" % (hh,mm,ss) if filter(nonzero,(hh,mm,ss)) or not datestring else ''
        return datestring+timestring
    #-------------------------------------------------------------------------------
    def utf8ize(self,l):
        # Make string-like things into utf-8, leave other things alone
        return [unicode(s).encode('utf-8') if hasattr(s,'encode') else s for s in l]


class edifact(var):
    ''' class for edifact inmessage objects.'''
    @staticmethod
    def _manipulatemessagetype(messagetype,inode):
        ''' default: just return messagetype. ''' 
        return messagetype.replace('.','_')      #older edifact messages have eg 90.1 as version...does not match with python imports...so convert this

    def _readcontent_edifile(self):
        ''' read content of edifact file in memory.
            is read as binary. In _sniff determine charset; then decode according to charset
        '''
        botsglobal.logger.debug(u'read edi file "%(filename)s".',self.ta_info)
        self.rawinput = botslib.readdata(filename=self.ta_info['filename'])     #read as binary

    def _sniff(self):
        ''' examine a read edifact file for syntax parameters and correctness: eg parse UNA, find UNB, get charset and version
            problem (as UNA sets characters.):
            1. sometimes edi files are appended, leading to multiple UNA/UNB in one file
            2. sometimes block format is used
            If 1 & 2 are mixed, this coudl lead to situation where UNA-string has CR/LF in it. Bots does not support this (crazy) situation.
            Note: in real world have seen files with multiple UNA. UNA always sets for 1 UNB.
            Bots assumes: UNA-string has NO extra CR/LF in it, never.
        '''
        try:
            count = 0
            #**************find first non-whitespace character
            while self.rawinput[count].isspace():         
                count += 1
            #**************check if UNA
            if self.rawinput[count:count+3] == 'UNA':
                has_una_string = True
                #extra check: UNA length. So: find UNB, calculate UNA-length. But: further on the UNB is already checked; this error is not too good...
                count += 3
                for field in ['sfield_sep','field_sep','decimaal','escape','reserve','record_sep']:
                    self.ta_info[field] = self.rawinput[count]
                    count += 1
                #UNA-string is done; loop untill next not-space char
                while self.rawinput[count].isspace():         
                    count += 1
                self.rawinput = self.rawinput[count:]  #rawinput does not contains UNA anymore. have to skip this, as parser does not parse UNA
                count = 0   #reset counter to start of new rawinput
            else:
                has_una_string = False
        except IndexError:
            raise botslib.InMessageError(_(u'[A53]: Edifact file contains only whitespace.'))   #plus some border cases; not possible if mailbag is used.
            
        #what if seperators are in skip_char? or is this to theoretical
        #**************expect UNB
        #loop over rawinput to extract segmenttag, used seperators, etc. 
        count2 = 0
        found_tag = ''
        found_charset = ''
        for char in self.rawinput[count:count+20]:
            if char in self.ta_info['skip_char']:
                continue
            if count2 <= 2:
                found_tag += char
            elif count2 == 3:
                found_field_sep = char
                if found_tag != 'UNB':
                    raise botslib.InMessageError(_(u'[A54]: Found no "UNB" at the start of edifact file.'))  #also: UNA too short. not possible if mailbag is used.
            elif count2 <= 7:
                found_charset += char
            elif count2 == 8:
                found_sfield_sep = char
            else:
                self.ta_info['version'] = char
                break
            count2 += 1
        else:
            #if arrive here: to many <cr/lf>?  
            raise botslib.InMessageError(_(u'[A55]: Problems with UNB-segment; encountered too many <CR/LF>.'))
        
        #set and/or verify seperators
        if has_una_string:
            if found_field_sep != self.ta_info['field_sep'] or found_sfield_sep != self.ta_info['sfield_sep']:
                #~ print found_field_sep, self.ta_info['field_sep'], found_sfield_sep == self.ta_info['sfield_sep']:
                raise botslib.InMessageError(_(u'[A56]: Separators used in edifact file differ from values indicated in UNA-segment.'))
        else:
            if found_field_sep == '+' and found_sfield_sep == ':':     #assume standard/UNOA separators.
                self.ta_info['sfield_sep'] = ':'
                self.ta_info['field_sep'] = '+'
                self.ta_info['decimaal'] = '.'
                self.ta_info['escape'] = '?'
                self.ta_info['reserve'] = '*'
                self.ta_info['record_sep'] = "'"
            elif found_field_sep == '\x1D' and found_sfield_sep == '\x1F':     #check if UNOB separators are used
                self.ta_info['sfield_sep'] = '\x1F'
                self.ta_info['field_sep'] = '\x1D'
                self.ta_info['decimaal'] = '.'
                self.ta_info['escape'] = ''
                self.ta_info['reserve'] = '*'
                self.ta_info['record_sep'] = '\x1C'
            else:
                raise botslib.InMessageError(_(u'[A57]: Edifact file with non-standard separators. An UNA segment should be used.'))
                    
        #*********** decode the file (to unicode)
        try:
            self.rawinput = self.rawinput.decode(found_charset,self.ta_info['checkcharsetin'])
            self.ta_info['charset'] = found_charset
        except LookupError:
            raise botslib.InMessageError(_(u'[A58]: Edifact file has unknown characterset "%(charset)s".'),
                                            {'charset':found_charset})
        except UnicodeDecodeError, msg:
            raise botslib.InMessageError(_(u'[A59]: Edifact file has not allowed characters at/after file-position %(content)s.'),
                                            {'content':msg[2]})
        if self.ta_info['version'] < '4':     #repeat char only for version >= 4
            self.ta_info['reserve'] = ''


    def checkenvelope(self):
        ''' check envelopes (UNB-UNZ counters & references, UNH-UNT counters & references etc)
        '''
        for nodeunb in self.getloop({'BOTSID':'UNB'}):
            botsglobal.logmap.debug(u'Start parsing edifact envelopes')
            unbreference = nodeunb.get({'BOTSID':'UNB','0020':None})
            unzreference = nodeunb.get({'BOTSID':'UNB'},{'BOTSID':'UNZ','0020':None})
            if unbreference and unzreference and unbreference != unzreference:
                self.add2errorlist(_(u'[E01]: UNB-reference is "%(unbreference)s"; should be equal to UNZ-reference "%(unzreference)s".\n')%{'unbreference':unbreference,'unzreference':unzreference})
            unzcount = nodeunb.get({'BOTSID':'UNB'},{'BOTSID':'UNZ','0036':None})
            messagecount = len(nodeunb.children) - 1
            try:
                if int(unzcount) != messagecount:
                    self.add2errorlist(_(u'[E02]: Count of messages in UNZ is %(unzcount)s; should be equal to number of messages %(messagecount)s.\n')%{'unzcount':unzcount,'messagecount':messagecount})
            except:
                self.add2errorlist(_(u'[E03]: Count of messages in UNZ is invalid: "%(count)s".\n')%{'count':unzcount})
            for nodeunh in nodeunb.getloop({'BOTSID':'UNB'},{'BOTSID':'UNH'}):
                unhreference = nodeunh.get({'BOTSID':'UNH','0062':None})
                untreference = nodeunh.get({'BOTSID':'UNH'},{'BOTSID':'UNT','0062':None})
                if unhreference and untreference and unhreference != untreference:
                    self.add2errorlist(_(u'[E04]: UNH-reference is "%(unhreference)s"; should be equal to UNT-reference "%(untreference)s".\n')%{'unhreference':unhreference,'untreference':untreference})
                untcount = nodeunh.get({'BOTSID':'UNH'},{'BOTSID':'UNT','0074':None})
                segmentcount = nodeunh.getcount()
                try:
                    if int(untcount) != segmentcount:
                        self.add2errorlist(_(u'[E05]: Segmentcount in UNT is %(untcount)s; should be equal to number of segments %(segmentcount)s.\n')%{'untcount':untcount,'segmentcount':segmentcount})
                except:
                    self.add2errorlist(_(u'[E06]: Count of segments in UNT is invalid: "%(count)s".\n')%{'count':untcount})
            for nodeung in nodeunb.getloop({'BOTSID':'UNB'},{'BOTSID':'UNG'}):
                ungreference = nodeung.get({'BOTSID':'UNG','0048':None})
                unereference = nodeung.get({'BOTSID':'UNG'},{'BOTSID':'UNE','0048':None})
                if ungreference and unereference and ungreference != unereference:
                    self.add2errorlist(_(u'[E07]: UNG-reference is "%(ungreference)s"; should be equal to UNE-reference "%(unereference)s".\n')%{'ungreference':ungreference,'unereference':unereference})
                unecount = nodeung.get({'BOTSID':'UNG'},{'BOTSID':'UNE','0060':None})
                groupcount = len(nodeung.children) - 1
                try:
                    if int(unecount) != groupcount:
                        self.add2errorlist(_(u'[E08]: Groupcount in UNE is %(unecount)s; should be equal to number of groups %(groupcount)s.\n')%{'unecount':unecount,'groupcount':groupcount})
                except:
                    self.add2errorlist(_(u'[E09]: Groupcount in UNE is invalid: "%(count)s".\n')%{'count':unecount})
                for nodeunh in nodeung.getloop({'BOTSID':'UNG'},{'BOTSID':'UNH'}):
                    unhreference = nodeunh.get({'BOTSID':'UNH','0062':None})
                    untreference = nodeunh.get({'BOTSID':'UNH'},{'BOTSID':'UNT','0062':None})
                    if unhreference and untreference and unhreference != untreference:
                        self.add2errorlist(_(u'[E10]: UNH-reference is "%(unhreference)s"; should be equal to UNT-reference "%(untreference)s".\n')%{'unhreference':unhreference,'untreference':untreference})
                    untcount = nodeunh.get({'BOTSID':'UNH'},{'BOTSID':'UNT','0074':None})
                    segmentcount = nodeunh.getcount()
                    try:
                        if int(untcount) != segmentcount:
                            self.add2errorlist(_(u'[E11]: Segmentcount in UNT is %(untcount)s; should be equal to number of segments %(segmentcount)s.\n')%{'untcount':untcount,'segmentcount':segmentcount})
                    except:
                        self.add2errorlist(_(u'[E12]: Count of segments in UNT is invalid: "%(count)s".\n')%{'count':untcount})
            botsglobal.logmap.debug(u'Parsing edifact envelopes is OK')

    def handleconfirm(self,ta_fromfile,error):
        ''' generates CONTRL messages.
            done at end of edifact file handling.
            for now: only called if no parser errors in interchange: no 'error'-CONTRL is generated.
            AFAICS generating error-CONTRL would not be hard...
            parameter 'error' is not used now.
        '''
        #global check if confirmrules use 'send-edifact-CONTRL' at all. Check is only done once per bots-run. Reason: performance; CONTRL-message is not that much used.
        confirmtype = 'send-edifact-CONTRL'
        if not hasattr(self.__class__,'send_edifact_CONTRL'):
            self.__class__.send_edifact_CONTRL = botslib.globalcheckconfirmrules(confirmtype)
        if not self.__class__.send_edifact_CONTRL:
            return
        editype = self.__class__.__name__
        for nodeunb in self.getloop({'BOTSID':'UNB'}):
            sender = nodeunb.get({'BOTSID':'UNB','S002.0004':None})
            receiver = nodeunb.get({'BOTSID':'UNB','S003.0010':None})
            nr_message_to_confirm = 0
            messages_not_confirm = []
            for nodeunh in nodeunb.getloop({'BOTSID':'UNB'},{'BOTSID':'UNH'}):
                messagetype=nodeunh.queries['messagetype']
                #no CONTRL for CONTRL or APERAK message; check if CONTRL should be send via confirmrules
                if messagetype[:6] in ['CONTRL','APERAK'] or not botslib.checkconfirmrules(confirmtype,idroute=self.ta_info['idroute'],idchannel=self.ta_info['fromchannel'],
                                                                                                frompartner=sender,topartner=receiver,editype=editype,messagetype=messagetype):
                    messages_not_confirm.append(nodeunh)
                else:
                    nr_message_to_confirm += 1
            if not nr_message_to_confirm:
                continue
            #remove message not to beconfirmed from tree (is destructive, but this is end of file processing anyway.
            for message_not_confirm in messages_not_confirm:
                nodeunb.children.remove(message_not_confirm)
            #check if there is a user mappingscript
            tscript,toeditype,tomessagetype = botslib.lookup_translation(fromeditype=editype,frommessagetype='CONTRL',frompartner=receiver,topartner=sender,alt='')
            if not tscript:
                tomessagetype = 'CONTRL22UNEAN002'  #default messagetype for CONTRL
                translationscript = None
            else:
                translationscript,scriptfilename = botslib.botsimport('mappings',editype + '.' + tscript)  #import the mappingscript
            #generate CONTRL-message. One received interchange->one CONTRL-message
            reference = str(botslib.unique('messagecounter'))
            ta_confirmation = ta_fromfile.copyta(status=TRANSLATED)
            filename = str(ta_confirmation.idta)
            out = outmessage.outmessage_init(editype=editype,messagetype=tomessagetype,filename=filename,reference=reference,statust=OK)    #make outmessage object
            out.ta_info['frompartner'] = receiver   #reverse!
            out.ta_info['topartner'] = sender       #reverse!
            if translationscript and hasattr(translationscript,'main'):
                botslib.runscript(translationscript,scriptfilename,'main',inn=self,out=out)
            else:
                #default mapping script for CONTRL
                out.put({'BOTSID':'UNH','0062':reference,'S009.0065':'CONTRL','S009.0052':'2','S009.0054':'2','S009.0051':'UN','S009.0057':'EAN002'})
                out.put({'BOTSID':'UNH'},{'BOTSID':'UCI','0083':'7'})
                out.put({'BOTSID':'UNH'},{'BOTSID':'UCI','0020':nodeunb.get({'BOTSID':'UNB','0020':None})})
                out.put({'BOTSID':'UNH'},{'BOTSID':'UCI','S002.0004':sender})     #not reverse!
                out.put({'BOTSID':'UNH'},{'BOTSID':'UCI','S002.0007':nodeunb.get({'BOTSID':'UNB','S002.0007':None})})
                out.put({'BOTSID':'UNH'},{'BOTSID':'UCI','S002.0014':nodeunb.get({'BOTSID':'UNB','S002.0014':None})})
                out.put({'BOTSID':'UNH'},{'BOTSID':'UCI','S002.0042':nodeunb.get({'BOTSID':'UNB','S002.0042':None})})
                out.put({'BOTSID':'UNH'},{'BOTSID':'UCI','S003.0010':receiver})   #not reverse!
                out.put({'BOTSID':'UNH'},{'BOTSID':'UCI','S003.0007':nodeunb.get({'BOTSID':'UNB','S003.0007':None})})
                out.put({'BOTSID':'UNH'},{'BOTSID':'UCI','S003.0014':nodeunb.get({'BOTSID':'UNB','S003.0014':None})})
                out.put({'BOTSID':'UNH'},{'BOTSID':'UCI','S003.0042':nodeunb.get({'BOTSID':'UNB','S003.0042':None})})
                for nodeunh in nodeunb.getloop({'BOTSID':'UNB'},{'BOTSID':'UNH'}):
                    lou = out.putloop({'BOTSID':'UNH'},{'BOTSID':'UCM'})
                    lou.put({'BOTSID':'UCM','0083':'7'})
                    lou.put({'BOTSID':'UCM','0062':nodeunh.get({'BOTSID':'UNH','0062':None})})
                    lou.put({'BOTSID':'UCM','S009.0065':nodeunh.get({'BOTSID':'UNH','S009.0065':None})})
                    lou.put({'BOTSID':'UCM','S009.0052':nodeunh.get({'BOTSID':'UNH','S009.0052':None})})
                    lou.put({'BOTSID':'UCM','S009.0054':nodeunh.get({'BOTSID':'UNH','S009.0054':None})})
                    lou.put({'BOTSID':'UCM','S009.0051':nodeunh.get({'BOTSID':'UNH','S009.0051':None})})
                    lou.put({'BOTSID':'UCM','S009.0057':nodeunh.get({'BOTSID':'UNH','S009.0057':None})})
                out.put({'BOTSID':'UNH'},{'BOTSID':'UNT','0074':out.getcount()+1,'0062':reference})  #last line (counts the segments produced in out-message)
                if translationscript and hasattr(translationscript,'change'):       #user mapping script that only changes the default mapping
                    botslib.runscript(translationscript,scriptfilename,'change',inn=self,out=out)
            #write tomessage (result of translation)
            out.writeall()
            botsglobal.logger.debug(u'Send edifact confirmation (CONTRL) route "%(route)s" fromchannel "%(fromchannel)s" frompartner "%(frompartner)s" topartner "%(topartner)s".',
                                    {'route':self.ta_info['idroute'],'fromchannel':self.ta_info['fromchannel'],'frompartner':receiver,'topartner':sender})
            self.ta_info.update(confirmtype=confirmtype,confirmed=True,confirmasked = True,confirmidta=ta_confirmation.idta)  #this info is used in transform.py to update the ta.....ugly...
            ta_confirmation.update(**out.ta_info)    #update ta for confirmation
            

class x12(var):
    ''' class for x12 inmessage objects.'''
    @staticmethod
    def _manipulatemessagetype(messagetype,inode):
        ''' x12 also needs field from GS record to identify correct messagetype '''
        return messagetype +  inode.record['GS08']

    def _sniff(self):
        ''' examine a file for syntax parameters and correctness of protocol
            eg parse ISA, get charset and version
        '''
        count = 0
        version = ''
        recordID = ''
        rawinput = self.rawinput[:200].lstrip()
        for char in rawinput:
            if char in '\r\n' and count != 105: #pos 105: is record_sep, could be \r\n
                continue
            count += 1
            if count <= 3:
                recordID += char
            elif count == 4:
                self.ta_info['field_sep'] = char
                if recordID != 'ISA':
                    raise botslib.InMessageError(_(u'[A60]: Expect "ISA", found "%(content)s". Probably no x12?'),
                                                {'content':self.rawinput[:7]})   #not with mailbon
            elif count in [7,18,21,32,35,51,54,70]:   #extra checks for fixed ISA. Not when mailbag.
                if char != self.ta_info['field_sep']:
                    raise botslib.InMessageError(_(u'[A63]: Non-valid ISA header; position %(pos)s of ISA is "%(foundchar)s", expect here element separator "%(field_sep)s".'),
                                                    {'pos':str(count),'foundchar':char,'field_sep':self.ta_info['field_sep']})
            elif count < 84:
                continue
            elif count <= 89:
                version += char
            elif count == 105:
                self.ta_info['sfield_sep'] = char
            elif count == 106:
                self.ta_info['record_sep'] = char
                break
        else: 
            #if arrive here: not not reach count == 106. 
            if count == 0:
                raise botslib.InMessageError(_(u'[A61]: Edi file contains only whitespace.'))  #not with mailbag
            else:
                raise botslib.InMessageError(_(u'[A62]: expect X12 file but envelope is not right.'))
        if version < '004030':  #not used before this version
            self.ta_info['reserve'] = ''    
        self.ta_info['skip_char'] = self.ta_info['skip_char'].replace(self.ta_info['record_sep'],'') #if <CR> is segment terminator: cannot be in the skip_char-string!

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
                self.add2errorlist(_(u'[E13]: ISA-reference is "%(isareference)s"; should be equal to IEA-reference "%(ieareference)s".\n')%{'isareference':isareference,'ieareference':ieareference})
            ieacount = nodeisa.get({'BOTSID':'ISA'},{'BOTSID':'IEA','IEA01':None})
            groupcount = nodeisa.getcountoccurrences({'BOTSID':'ISA'},{'BOTSID':'GS'})
            try:
                if int(ieacount) != groupcount:
                    self.add2errorlist(_(u'[E14]: Count in IEA-IEA01 is %(ieacount)s; should be equal to number of groups %(groupcount)s.\n')%{'ieacount':ieacount,'groupcount':groupcount})
            except:
                self.add2errorlist(_(u'[E15]: Count of messages in IEA is invalid: "%(count)s".\n')%{'count':ieacount})
            for nodegs in nodeisa.getloop({'BOTSID':'ISA'},{'BOTSID':'GS'}):
                sender = nodegs.get({'BOTSID':'GS','GS02':None})
                receiver = nodegs.get({'BOTSID':'GS','GS03':None})
                gsqualifier = nodegs.get({'BOTSID':'GS','GS01':None})
                gsreference = nodegs.get({'BOTSID':'GS','GS06':None})
                gsversion = nodegs.get({'BOTSID':'GS','GS08':None})
                gereference = nodegs.get({'BOTSID':'GS'},{'BOTSID':'GE','GE02':None})
                if gsreference and gereference and gsreference != gereference:
                    self.add2errorlist(_(u'[E16]: GS-reference is "%(gsreference)s"; should be equal to GE-reference "%(gereference)s".\n')%{'gsreference':gsreference,'gereference':gereference})
                gecount = nodegs.get({'BOTSID':'GS'},{'BOTSID':'GE','GE01':None})
                messagecount = len(nodegs.children) - 1
                try:
                    if int(gecount) != messagecount:
                        self.add2errorlist(_(u'[E17]: Count in GE-GE01 is %(gecount)s; should be equal to number of transactions: %(messagecount)s.\n')%{'gecount':gecount,'messagecount':messagecount})
                except:
                    self.add2errorlist(_(u'[E18]: Count of messages in GE is invalid: "%(count)s".\n')%{'count':gecount})
                self.confirmationlist.append({'gsqualifier':gsqualifier,'gsreference':gsreference,'gecount':gecount,'sender':sender,'receiver':receiver,'STlist':[]})   #gather information about functional group (GS-GE)
                for nodest in nodegs.getloop({'BOTSID':'GS'},{'BOTSID':'ST'}):
                    stqualifier = nodest.get({'BOTSID':'ST','ST01':None})
                    streference = nodest.get({'BOTSID':'ST','ST02':None})
                    sereference = nodest.get({'BOTSID':'ST'},{'BOTSID':'SE','SE02':None})
                    #referencefields are numerical; should I compare values??
                    if streference and sereference and streference != sereference:
                        self.add2errorlist(_(u'[E19]: ST-reference is "%(streference)s"; should be equal to SE-reference "%(sereference)s".\n')%{'streference':streference,'sereference':sereference})
                    secount = nodest.get({'BOTSID':'ST'},{'BOTSID':'SE','SE01':None})
                    segmentcount = nodest.getcount()
                    try:
                        if int(secount) != segmentcount:
                            self.add2errorlist(_(u'[E20]: Count in SE-SE01 is %(secount)s; should be equal to number of segments %(segmentcount)s.\n')%{'secount':secount,'segmentcount':segmentcount})
                    except:
                        self.add2errorlist(_(u'[E21]: Count of segments in SE is invalid: "%(count)s".\n')%{'count':secount})
                    self.confirmationlist[-1]['STlist'].append({'streference':streference,'stqualifier':stqualifier,'gsversion':gsversion})   #add info per message to functional group
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
                #gather full messagetype:
                messagetype = ''
                for key in ['stqualifier','gsversion']:
                    if message_received[key]:
                        messagetype += message_received[key]
                if botslib.checkconfirmrules('send-x12-997',idroute=self.ta_info['idroute'],idchannel=self.ta_info['fromchannel'],
                                                frompartner=confirmation['sender'],topartner=confirmation['receiver'],
                                                editype='x12',messagetype=messagetype):
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
            out.ta_info['frompartner'] = confirmation['receiver']   #sender and receiver are swapped for sending 997!
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
            botsglobal.logger.debug(u'Send x12 confirmation (997) route "%(route)s" fromchannel "%(fromchannel)s" frompartner "%(frompartner)s" topartner "%(topartner)s".',
                    {'route':self.ta_info['idroute'],'fromchannel':self.ta_info['fromchannel'],'frompartner':confirmation['receiver'],'topartner':confirmation['sender']})
            self.ta_info.update(confirmtype='send-x12-997',confirmed=True,confirmasked = True,confirmidta=ta_confirmation.idta)  #this info is used in transform.py to update the ta.....ugly...
            ta_confirmation.update(statust=OK,**out.ta_info)    #update ta for confirmation


class tradacoms(var):
    def checkenvelope(self):
        for nodestx in self.getloop({'BOTSID':'STX'}):
            botsglobal.logmap.debug(u'Start parsing tradacoms envelopes')
            endcount = nodestx.get({'BOTSID':'STX'},{'BOTSID':'END','NMST':None})
            messagecount = len(nodestx.children) - 1
            try:
                if int(endcount) != messagecount:
                    self.add2errorlist(_(u'[E22]: Count in END is %(endcount)s; should be equal to number of messages %(messagecount)s.\n')%{'endcount':endcount,'messagecount':messagecount})
            except:
                self.add2errorlist(_(u'[E23]: Count of messages in END is invalid: "%(count)s".\n')%{'count':endcount})
            firstmessage = True
            for nodemhd in nodestx.getloop({'BOTSID':'STX'},{'BOTSID':'MHD'}):
                if firstmessage:    #
                    nodestx.queries = {'messagetype':nodemhd.queries['messagetype']}
                    firstmessage = False
                mtrcount = nodemhd.get({'BOTSID':'MHD'},{'BOTSID':'MTR','NOSG':None})
                segmentcount = nodemhd.getcount()
                try:
                    if int(mtrcount) != segmentcount:
                        self.add2errorlist(_(u'[E24]: Count in MTR is %(mtrcount)s; should be equal to number of segments %(segmentcount)s.\n')%{'mtrcount':mtrcount,'segmentcount':segmentcount})
                except:
                    self.add2errorlist(_(u'[E25]: Count of segments in MTR is invalid: "%(count)s".\n')%{'count':mtrcount})
            botsglobal.logmap.debug(u'Parsing tradacoms envelopes is OK')


class xml(Inmessage):
    ''' class for ediobjects in XML. Uses ElementTree'''
    def initfromfile(self):
        botsglobal.logger.debug(u'read edi file "%(filename)s".',self.ta_info)
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
                    raise botslib.InMessageError(_(u'Invalid search parameters in xml mailbag.'))
                #~ print 'search' ,item
                found = etree.find(item['xpath'])
                if found is not None:
                    #~ print '    found'
                    if 'content' in item and found.text != item['content']:
                        continue
                    self.ta_info['messagetype'] = item['messagetype']
                    #~ print '    found right messagedefinition'
                    break
            else:
                raise botslib.InMessageError(_(u'Could not find right xml messagetype for mailbag.'))

            self.messagegrammarread()
        else:
            self.messagegrammarread()
            parser = ET.XMLParser()
            for key,value in self.ta_info['extra_character_entity'].items():
                parser.entity[key] = value
            etree =  ET.ElementTree()   #ElementTree: lexes, parses, makes etree; etree is quite similar to bots-node trees but conversion is needed
            etreeroot = etree.parse(filename, parser)
        self._handle_empty(etreeroot)
        self.stack = [self.defmessage.structure[0],]     #stack to track where we are in stucture of grammar
        self.root = self._etree2botstree(etreeroot)  #convert etree to bots-nodes-tree
        self.checkmessage(self.root,self.defmessage)

    def _handle_empty(self,xmlnode):
        if xmlnode.text:
            xmlnode.text = xmlnode.text.strip()
        for key,value in xmlnode.items():
            xmlnode.attrib[key] = value.strip()
        for xmlchildnode in xmlnode:   #for every node in mpathtree
            self._handle_empty(xmlchildnode)
            
    def _etree2botstree(self,xmlnode):
        ''' recursive. '''
        newnode = node.Node(record=self._etreenode2botstreenode(xmlnode))
        for xmlchildnode in xmlnode:   #for every node in mpathtree
            entitytype = self._entitytype(xmlchildnode)
            if not entitytype:  #is a field, or unknown that looks like a field
                ## remark for generating grammars: empty strings should generate a field here
                if xmlchildnode.text:
                    newnode.record[xmlchildnode.tag] = xmlchildnode.text      #add as a field
                for key,value in xmlchildnode.items():   #convert the xml-attributes of this 'xml-filed' to fields in dict with attributemarker.
                    if value:
                        newnode.record[xmlchildnode.tag + self.ta_info['attributemarker'] + key] = value      #add as a field
            elif entitytype==1:  #is a record according to grammar
                newnode.append(self._etree2botstree(xmlchildnode))           #add as a node/record
                self.stack.pop()    #handled the xmlnode, so remove it from the stack
            else:   #is a record, but not in grammar
                if self.ta_info['checkunknownentities']:
                    self.add2errorlist(_(u'[S02]%(linpos)s: Unknown xml-tag "%(recordunkown)s" (within "%(record)s") in message.\n')%
                                        {'linpos':newnode.linpos(),'recordunkown':xmlchildnode.tag,'record':newnode.record['BOTSID']})
                continue
        return newnode

    def _etreenode2botstreenode(self,xmlnode):
        ''' build a basic dict from xml-node. Add BOTSID, xml-attributes (of 'record'), xmlnode.text as BOTSCONTENT.'''
        build = dict((xmlnode.tag + self.ta_info['attributemarker'] + key,value) for key,value in xmlnode.items() if value)   #convert xml attributes to fields.
        build['BOTSID'] = xmlnode.tag
        if xmlnode.text:
            build['BOTSCONTENT'] = xmlnode.text
        return build

    def _entitytype(self,xmlchildnode):
        ''' check if xmlchildnode is field (or record)'''
        structure_level = self.stack[-1]
        if LEVEL in structure_level:
            for structure_record in structure_level[LEVEL]:   #find xmlchildnode in structure
                if xmlchildnode.tag == structure_record[ID]:
                    self.stack.append(structure_record)
                    return 1
        #tag not in structure. Check for children; Return 2 if has children
        if len(xmlchildnode):
            return 2
        return 0

class xmlnocheck(xml):
    ''' class for ediobjects in XML. Uses ElementTree'''
    def checkmessage(self,node_instance,defmessage,subtranslation=False):
        pass

    def _entitytype(self,xmlchildnode):
        if len(xmlchildnode):
            self.stack.append(xmlchildnode.tag)
            return 1
        return 0

class json(Inmessage):
    def initfromfile(self):
        self.messagegrammarread()
        self._readcontent_edifile()

        jsonobject = simplejson.loads(self.rawinput)
        del self.rawinput
        if isinstance(jsonobject,list):
            self.root = node.Node()  #initialise empty node.
            self.root.children = self._dojsonlist(jsonobject,self._getrootid())   #fill root with children
            for child in self.root.children:
                if not child.record:    #sanity test: the children must have content
                    raise botslib.InMessageError(_(u'[J51]: No usable content.'))
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
                raise botslib.InMessageError(_(u'[J52]: No usable content.'))
            self.checkmessage(self.root,self.defmessage)
        else:
            #root in JSON is neither dict or list.
            raise botslib.InMessageError(_(u'[J53]: Content must be a "list" or "object".'))

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
                raise botslib.InMessageError(_(u'[J54]: List content in must be a "object".'))
        return lijst

    def _dojsonobject(self,jsonobject,name):
        thisnode = node.Node(record={'BOTSID':name})  #initialise empty node.
        for key,value in jsonobject.items():
            if value is None:
                continue
            elif isinstance(value,basestring):  #json field; map to field in node.record
                ## for generating grammars: empty strings should generate a field 
                if value and not value.isspace():   #use only if string has a value.
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
                    raise botslib.InMessageError(_(u'[J55]: Key "%(key)s" value "%(value)s": is not string, list or dict.'),
                                                    {'key':key,'value':value})
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
    #20120101 depreciated. use class db
    pass


class db(Inmessage):
    ''' For database connector.
        the database-object is unpickled, and passed to the mappingscript.
    '''
    def initfromfile(self):
        botsglobal.logger.debug(u'read edi file "%(filename)s".',self.ta_info)
        filehandler = botslib.opendata(filename=self.ta_info['filename'],mode='rb')
        self.root = pickle.load(filehandler)
        filehandler.close()

    def nextmessage(self):
        yield self


class raw(Inmessage):
    ''' the file object is just read and passed to the mappingscript.
    '''
    def initfromfile(self):
        botsglobal.logger.debug(u'read edi file "%(filename)s".',self.ta_info)
        filehandler = botslib.opendata(filename=self.ta_info['filename'],mode='rb')
        self.root = filehandler.read()
        filehandler.close()

    def nextmessage(self):
        yield self
