''' Reading/lexing/parsing/splitting an edifile.'''
import StringIO
import time
import sys
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
import botslib
import botsglobal
import outmessage
import message
import node
import grammar
from botsconfig import *

def edifromfile(**ta_info):
    ''' Read,lex, parse edi-file. Is a despatch function for Inmessage and subclasses.'''
    try:
        classtocall = globals()[ta_info['editype']]  #get inmessage class to call (subclass of Inmessage)
    except KeyError:
        raise botslib.InMessageEdiTypeNotKnownError(ta_info['editype'])
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
        self.ta_info['charset'] =self.defmessage.syntax['charset']  #always use cahrset of edi file.
        self._readcontent_edifile()
        self._sniff()           #some hard-coded parsing of edi file; eg ta_info can be overruled by syntax-parameters in edi-file
        #start lexing and parsing
        self._lex()
        del self.rawinput
        #~ self.display(self.records)   #show lexed records (for protocol debugging)
        self.root = node.Node()  #make root Node None.
        result = self._parse(self.defmessage.structure,self._nextrecord(self.records),self.root)
        if result:
            raise botslib.InMessageError(u'Unknown data beyond end of message; mostly problem with separators or message structure: "$content"',content=result)
        del self.records
        #end parsing; self.root is root of a tree (of nodes).
        self.checkenvelope()
        #~ self.root.display() #show tree of nodes (for protocol debugging)
        #~ self.root.displayqueries() #show queries in tree of nodes (for protocol debugging)

    def initfromparsed(self,node):
        ''' initialisation from a tree (node is passed).
            to initialise message in an envelope
        '''
        self.root = node

    def close(self,ta_fromfile,error):
        ''' end of edi file handling.
            eg writing of confirmations etc.
        '''
        pass

    def _formatfield(self,value,grammarfield,record):
        ''' Format of a field is checked and converted if needed.
            Input: value (string), field definition.
            Output: the formatted value (string)
            Parameters of self.ta_info are used: triad, decimaal
            for fixed field: same handling; length is not checked.
        '''
        if grammarfield[BFORMAT] in ['A','D','T']:
            if isinstance(self,var):  #check length fields in variable records
                valuelength=len(value)
                if valuelength > grammarfield[LENGTH]:
                    raise botslib.InMessageFieldError(u'Record "$record" field "$field" too big (max $max): "$content".',record=record,field=grammarfield[ID],content=value,max=grammarfield[LENGTH])
                if valuelength < grammarfield[MINLENGTH]:
                    raise botslib.InMessageFieldError(u'Record "$record" field "$field" too small (min $min): "$content".',record=record,field=grammarfield[ID],content=value,min=grammarfield[MINLENGTH])
            value = value.strip()
            if grammarfield[BFORMAT] == 'A':
                pass
            elif grammarfield[BFORMAT] == 'D':
                try:
                    lenght = len(value)
                    if lenght==6:
                        time.strptime(value,'%y%m%d')
                    elif lenght==8:
                        time.strptime(value,'%Y%m%d')
                    else:
                        raise ValueError
                except ValueError:
                    raise botslib.InMessageFieldError(u'Record "$record" date field "$field" not a valid date: "$content".',record=record,field=grammarfield[ID],content=value)
            elif grammarfield[BFORMAT] == 'T':
                try:
                    lenght = len(value)
                    if lenght==4:
                        time.strptime(value,'%H%M')
                    elif lenght==6:
                        time.strptime(value,'%H%M%S')
                    elif lenght==7 or lenght==8:
                        time.strptime(value[0:6],'%H%M%S')
                        if not value[6:].isdigit():
                            raise ValueError
                    else:
                        raise ValueError
                except  ValueError:
                    raise botslib.InMessageFieldError(u'Record "$record" time field "$field" not a valid time: "$content".',record=record,field=grammarfield[ID],content=value)
        else:   #numerics (R, N, I)
            value = value.strip()
            if not value:
                if self.ta_info['acceptspaceinnumfield']:
                    value='0'
                else:
                    raise botslib.InMessageFieldError(u'Record "$record" field "$field" has numeric format but contains only space.',record=record,field=grammarfield[ID])
                #~ return ''   #when num field has spaces as content, spaces are stripped. Field should be numeric.
            if value[-1] == u'-':    #if minus-sign at the end, put it in front.
                value = value[-1] + value[:-1]
            value = value.replace(self.ta_info['triad'],u'')     #strip triad-seperators
            value = value.replace(self.ta_info['decimaal'],u'.',1) #replace decimal sign by canonical decimal sign
            if 'E' in value or 'e' in value:
                raise botslib.InMessageFieldError(u'Record "$record" field "$field" format "$format" contains exponent: "$content".',record=record,field=grammarfield[ID],content=value,format=grammarfield[BFORMAT])
            if isinstance(self,var):  #check length num fields in variable records
                if self.ta_info['lengthnumericbare']:
                    length = botslib.countunripchars(value,'-+.')
                else:
                    length = len(value)
                if length > grammarfield[LENGTH]:
                    raise botslib.InMessageFieldError(u'Record "$record" field "$field" too big (max $max): "$content".',record=record,field=grammarfield[ID],content=value,max=grammarfield[LENGTH])
                if length < grammarfield[MINLENGTH]:
                    raise botslib.InMessageFieldError(u'Record "$record" field "$field" too small (min $min): "$content".',record=record,field=grammarfield[ID],content=value,min=grammarfield[MINLENGTH])
            if grammarfield[BFORMAT] == 'I':
                if '.' in value:
                    raise botslib.InMessageFieldError(u'Record "$record" field "$field" has format "I" but contains decimal sign: "$content".',record=record,field=grammarfield[ID],content=value)
                try:    #convert to decimal in order to check validity
                    valuedecimal = float(value)
                    valuedecimal = valuedecimal / 10**grammarfield[DECIMALS]
                    value = '%.*F'%(grammarfield[DECIMALS],valuedecimal)
                except:
                    raise botslib.InMessageFieldError(u'Record "$record" numeric field "$field" has non-numerical content: "$content".',record=record,field=grammarfield[ID],content=value)
            elif grammarfield[BFORMAT] == 'N':
                lendecimal = len(value[value.find('.'):])-1
                if lendecimal != grammarfield[DECIMALS]:
                    raise botslib.InMessageFieldError(u'Record "$record" numeric field "$field" has invalid nr of decimals: "$content".',record=record,field=grammarfield[ID],content=value)
                try:    #convert to decimal in order to check validity
                    valuedecimal = float(value)
                    value = '%.*F'%(lendecimal,valuedecimal)
                except:
                    raise botslib.InMessageFieldError(u'Record "$record" numeric field "$field" has non-numerical content: "$content".',record=record,field=grammarfield[ID],content=value)
            elif grammarfield[BFORMAT] == 'R':
                lendecimal = len(value[value.find('.'):])-1
                try:    #convert to decimal in order to check validity
                    valuedecimal = float(value)
                    value = '%.*F'%(lendecimal,valuedecimal)
                except:
                    raise botslib.InMessageFieldError(u'Record "$record" numeric field "$field" has non-numerical content: "$content".',record=record,field=grammarfield[ID],content=value)
        return value

    def _parse(self,tab,_nextrecord,inode,rec2parse=None,argmessagetype=None,argnewnode=None):
        ''' parse the lexed records. validate message against grammar.
            add grammar-info to records in self.records: field-tag,mpath.
            Tab: current grammar/segmentgroup of the grammar-structure.
            Read the records one by one.
            Lookup record in tab.
            if found:
                if headersegment (tabrecord has own tab):
                    go recursive.
            if not found:
                if trailer:
                    jump back recursive, returning the unparsed record.
        '''
        for tabrec in tab:    #clear counts for tab-records (start fresh).
            tabrec[COUNT] = 0
        tabindex = 0
        tabmax = len(tab)
        if rec2parse is None:
            parsenext = True
            subparse=False
        else:   #only for subparsing
            parsenext = False
            subparse=True
        while 1:
            if parsenext:
                try:
                    rec2parse = _nextrecord.next()
                except StopIteration:   #catch when no more rec2parse.
                    rec2parse = None
                parsenext = False
            if rec2parse is None or tab[tabindex][ID] != rec2parse[ID][VALUE]:
                #for StopIteration(loop rest of grammar) or when rec2parse
                if tab[tabindex][COUNT] < tab[tabindex][MIN]:
                    try:
                        raise botslib.InMessageParseError(u'line:$line pos:$pos; record:"$record" not in grammar; looked in grammar until mandatory record: "$looked".',record=rec2parse[ID][VALUE],line=rec2parse[ID][LIN],pos=rec2parse[ID][POS],looked=tab[tabindex][MPATH])
                    except TypeError:
                        raise botslib.InMessageParseError(u'missing mandatory record at message-level: "$record"',record=tab[tabindex][MPATH])
                    #TODO: line/pos of original file in error...when this is possible,  XML?
                tabindex += 1
                if tabindex >= tabmax:  #rec2parse is not in this level. Go level up
                    return rec2parse    #return either None (for StopIteration) or the last record2parse (not found in this level)
                #continue while-loop (parsenext is false)
            else:   #if found in grammar
                tab[tabindex][COUNT] += 1
                if tab[tabindex][COUNT] > tab[tabindex][MAX]:
                    raise botslib.InMessageParseError(u'line:$line pos:$pos; too many repeats record "$record".',line=rec2parse[ID][LIN],pos=rec2parse[ID][POS],record=tab[tabindex][ID])
                if argmessagetype:  #that is, header segment of subtranslation
                    newnode = argnewnode  #use old node that is already parsed
                    newnode.queries = {'messagetype':argmessagetype}    #copy messagetype into 1st segment of subtranslation (eg UNH, ST)
                    argmessagetype=None
                else:
                    newnode = node.Node(self._parsefields(rec2parse,tab[tabindex][FIELDS]))  #make new node
                    if botsglobal.ini.getboolean('settings','readrecorddebug',False):
                        botsglobal.logger.debug(u'read record "%s" (line %s pos %s):',tab[tabindex][ID],rec2parse[ID][LIN],rec2parse[ID][POS])
                        for key,value in newnode.record.items():
                            botsglobal.logger.debug(u'    "%s" : "%s"',key,value)
                if SUBTRANSLATION in tab[tabindex]: # subparse starts here: tree is build for this messagetype; the messagetype is read from the edifile
                    messagetype = self._getmessagetype(newnode.enhancedget(tab[tabindex][SUBTRANSLATION],replace=True),inode)
                    if not messagetype:
                        raise botslib.InMessageError(u'could not find SUBTRANSLATION "$sub" in (sub)message.',sub=tab[tabindex][SUBTRANSLATION])
                    defmessage = grammar.grammarread(self.__class__.__name__,messagetype)
                    rec2parse = self._parse(defmessage.structure,_nextrecord,inode,rec2parse=rec2parse,argmessagetype=messagetype,argnewnode=newnode)
                    #~ end subparse for messagetype
                else:
                    inode.append(newnode)   #append new node to currenct node
                    if LEVEL in tab[tabindex]:        #if header, go to subgroup
                        rec2parse = self._parse(tab[tabindex][LEVEL],_nextrecord,newnode)
                        if subparse:  #back in top level of subparse: return (to motherparse)
                            return rec2parse
                    else:
                        parsenext = True
                self.get_queries_from_edi(inode.children[-1],tab[tabindex])

    def _getmessagetype(self,messagetypefromsubtranslation,inode):
        return messagetypefromsubtranslation

    def get_queries_from_edi(self,node,trecord):
        ''' extract information from edifile using QUERIES in grammar.structure; information will be placed in ta_info and in db-ta
        '''
        if QUERIES in trecord:
            tmpdict = {}
            for key,value in trecord[QUERIES].items():
                found = node.enhancedget(value)   #search in last added node
                #~ print 'query',found,value
                if found:
                    tmpdict[key] = found    #copy key to avoid memory problems
            node.queries = tmpdict

    def _readcontent_edifile(self):
        ''' read content of edi file to memory.
        '''
        #TODO test, catch exceptions
        botsglobal.logger.debug(u'read edi file "%s".',self.ta_info['filename'])
        self.rawinput = botslib.readdata(filename=self.ta_info['filename'],charset=self.ta_info['charset'],errors=self.ta_info['checkcharsetin'])

    def _sniff(self):
        ''' sniffing: hard coded parsing of edi file.
            method is specified in subclasses.
        '''
        pass

    def checkenvelope(self):
        pass

    @staticmethod
    def _nextrecord(records):
        ''' generator for records that are lexed.'''
        for record in records:
            yield record

    def nextmessage(self):
        ''' Generates each message as a separate Inmessage.
        '''
        #~ self.root.display()
        if self.defmessage.nextmessage is not None: #if nextmessage defined in grammar
            first = True
            for message in self.getloop(*self.defmessage.nextmessage):  #get node of each message
                if first:
                    self.root.processqueries({},len(self.defmessage.nextmessage))
                    first = False
                ta_info = self.ta_info.copy()
                ta_info.update(message.queries)
                #~ ta_info['botsroot']=self.root
                yield _edifromparsed(self.__class__.__name__,message,ta_info)
            if self.defmessage.nextmessage2 is not None:
                first = True
                for message in self.getloop(*self.defmessage.nextmessage2):
                    if first:
                        self.root.processqueries({},len(self.defmessage.nextmessage2))
                        first = False
                    ta_info = self.ta_info.copy()
                    ta_info.update(message.queries)
                    #~ ta_info['botsroot']=self.root
                    yield _edifromparsed(self.__class__.__name__,message,ta_info)
        elif self.defmessage.nextmessageblock is not None:
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
                    #~ ta_info['botsroot']=self.root   #give mapping script access to all information in edi file: all records
                    yield _edifromparsed(self.__class__.__name__,newroot,ta_info)
                    newroot = node.Node()  #make new empty root node.
                    oldkriterium = kriterium
                else:
                    pass    #if kriterium is the same
                newroot.append(line)
            else:
                if not first:
                    ta_info = self.ta_info.copy()
                    #~ ta_info['botsroot']=self.root
                    yield _edifromparsed(self.__class__.__name__,newroot,ta_info)
        else:   #no split up indicated in grammar; s
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
    def _lex(self):
        ''' lexes file with fixed records to list of records (self.records).'''
        linenr = 0
        startrecordID = self.ta_info['startrecordID']
        endrecordID = self.ta_info['endrecordID']
        self.rawinputfile = StringIO.StringIO(self.rawinput)    #self.rawinputfile is an iterator
        for line in self.rawinputfile:
            linenr += 1
            line=line.rstrip('\r\n')
            self.records += [ [{VALUE:line[startrecordID:endrecordID].strip(),LIN:linenr,POS:0,FIXEDLINE:line}] ]    #append record to recordlist
        self.rawinputfile.close()

    def _parsefields(self,recordEdiFile,trecord):
        ''' Parse fields from one fixed message-record (from recordEdiFile[ID][FIXEDLINE] using positions.
            fields are placed in dict, where key=field-info from grammar and value is from fixedrecord.'''
        recorddict = {} #start with empty dict
        fixedrecord = recordEdiFile[ID][FIXEDLINE]  #shortcut to fixed record we are parsing
        lenfixed = len(fixedrecord)
        recordlength = 0
        for field in trecord:   #calculate total length of record from field lengths
            recordlength += field[LENGTH]
        if recordlength > lenfixed and self.ta_info['checkfixedrecordtooshort']:
            raise botslib.InMessageParseError(u'line $line record "$record" too short; is $pos pos, defined is $defpos pos: "$content".',line=recordEdiFile[ID][LIN],record=recordEdiFile[ID][VALUE],pos=lenfixed,defpos=recordlength,content=fixedrecord)
        if recordlength < lenfixed and self.ta_info['checkfixedrecordtoolong']:
            raise botslib.InMessageParseError(u'line $line record "$record" too long; is $pos pos, defined is $defpos pos: "$content".',line=recordEdiFile[ID][LIN],record=recordEdiFile[ID][VALUE],pos=lenfixed,defpos=recordlength,content=fixedrecord)
        pos = 0
        for field in trecord:   #for fields in this record
            value = fixedrecord[pos:pos+field[LENGTH]]
            try:
                value = self._formatfield(value,field,fixedrecord)
            except botslib.InMessageFieldError:
                txt=botslib.txtexc()
                raise botslib.InMessageFieldError(u'line:$line pos:$pos: $txt',line=recordEdiFile[ID][LIN],pos=pos,txt=txt)
            if value:
                recorddict[field[ID][:]] = value #copy id string to avoid memory problem ; value is already a copy
            else:
                if field[MANDATORY]==u'M':
                    raise botslib.InMessageFieldError(u'line:$line pos:$pos; mandatory field "$field" not in record "$record".',line=recordEdiFile[ID][LIN],pos=pos,field=field[ID],record=recordEdiFile[ID][VALUE])
            pos += field[LENGTH]
            #~ if pos > lenfixed:
                #~ break
        return recorddict


class idoc(fixed):
    ''' class for idoc ediobjects.
        for incoming the same as fixed.
        SAP does strip all empty fields for record; is catered for in grammar.defaultsyntax
    '''
    def _sniff(self):
        ''' examine a read file for syntax parameters and correctness of protocol
            eg parse UNA, find UNB, get charset and version
        '''
        #goto char that is not whitespace
        for count,c in enumerate(self.rawinput):
            if not c.isspace():
                self.rawinput = self.rawinput[count:]  #here the interchange should start
                break
        else:
            raise botslib.InMessageEnvelopeError(u'edi file only contains whitespace.')
        if self.rawinput[:6] != 'EDI_DC':
            raise botslib.InMessageEnvelopeError(u'expect "EDI_DC", found "$content". Probably no SAP idoc.',content=self.rawinput[:6])


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
        mode_2quote = 0 #0=not in quote, 1=in quote
        mode_escape = 0 #0=not escaping quote, 1=escaping quote. Escape:
        mode_inrecord = 0    #indicates if lexing a record. If mode_inrecord==0: skip whitespace
        sfield = False # True: is subveld, False is geen subveld
        value = u''    #the value of the current token
        record = []
        valueline = 1    #starting line of token
        valuepos = 1    #starting position of token
        countline = 1
        countpos = 0
        #bepaal tekenset, separators etc adhv UNA/UNOB
        for c in self.rawinput:    #get next char
            if c == u'\n':    #line within file
                countline += 1
                countpos = 0            #new line, pos back to 0
                #no continue, because \n can be record separator. In edifact: catch with skip_char
            else:
                countpos += 1        #position within line
            if mode_quote:          #within a quote: quote-char is also escape-char
                if mode_2quote and c == quote_char: #thus we were escaping quote_char
                    mode_2quote = 0
                    value += c    #append quote_char
                    continue
                elif mode_2quote:   #thus is was a end-quote
                    mode_2quote = 0
                    mode_quote= 0
                    #go on parsing
                elif c==quote_char:    #either end-quote or escaping quote_char
                    mode_2quote = 1
                    continue
                elif mode_escape:        #TODO: what if escaping quote_char (wich is not advised)?
                    mode_escape = 0
                    value += c
                    continue
                elif c == escape:
                    mode_escape = 1
                    continue
                else:
                    value += c
                    continue
            if not mode_inrecord and c.isspace():   #ignore space between records.
                continue
            else:
                mode_inrecord = 1
            if c in skip_char:    #after mode_quote, but before mode_escape!!
                continue
            if mode_escape:        #always append in escaped_mode
                mode_escape = 0
                value += c
                continue
            if not value:        #if no char in token than is is a new token; so get line and pos for (the new) token
                valueline = countline
                valuepos = countpos
            if c == quote_char:
                mode_quote = 1
                continue
            if c == escape:
                mode_escape = 1
                continue
            if c in field_sep:  #for tradacoms: record_tag_sep is appended to field_sep; in lexing they have the same function
                record += [{VALUE:value,SFIELD:sfield,LIN:valueline,POS:valuepos}]    #append element in record
                value = u''
                sfield = False
                continue
            if c == sfield_sep:
                record += [{VALUE:value,SFIELD:sfield,LIN:valueline,POS:valuepos}]    #append element in record
                value = u''
                sfield = True
                continue
            if c in record_sep:
                record += [{VALUE:value,SFIELD:sfield,LIN:valueline,POS:valuepos}]    #append element in record
                self.records += [record]    #write record to recordlist
                record=[]
                value = u''
                sfield = False
                mode_inrecord=0
                continue
            value += c    #just a char: append char to value
        #end of for-loop.
        if value:
            value = value.strip('\x00\x1a')
            if value:
                raise botslib.InMessageError(u'Lex error; mostly seperator-problem or chars after interchange')
                #~ , value, 'line: ',countline, 'position: ', countpos

    def _striprecord(self,recordEdiFile):
        return [field[VALUE] for field in recordEdiFile]

    def _parsefields(self,recordEdiFile,trecord):
        ''' Check all fields in message-record with field-info in grammar
            Build a dictionary of fields (field-IDs are unique within record), and return this.
            Used by _parse
        '''
        recorddict = {}
        #****************** first: identify fields, check _formatfield
        tindex = -1
        tsubindex=0
        for rfield in recordEdiFile:    #difficult;handles both fields and sub-fields
            if rfield[SFIELD]:
                tsubindex += 1
                try:
                    field = trecord[tindex][SUBFIELDS][tsubindex]
                except TypeError:
                    raise botslib.InMessageFieldError(u'line:$line pos:$pos; expect field, is a subfield; record "$record".',line=rfield[LIN],pos=rfield[POS],record=self._striprecord(recordEdiFile))
                except IndexError:
                    raise botslib.InMessageFieldError(u'line:$line pos:$pos; too many subfields; record "$record".',line=rfield[LIN],pos=rfield[POS],record=self._striprecord(recordEdiFile))
            else:
                tindex += 1
                try:
                    field = trecord[tindex]
                except IndexError:
                    raise botslib.InMessageFieldError(u'line:$line pos:$pos; too many fields; record "$record".',line=rfield[LIN],pos=rfield[POS],record=self._striprecord(recordEdiFile))
                    #TODO: better format error; give linenr/pos;
                if not field[ISFIELD]: #if field is subfield
                    tsubindex = 0
                    field = trecord[tindex][SUBFIELDS][tsubindex]
            if rfield[VALUE]:           #if field has content: check format and add to recorddictionary
                try:
                    rfield[VALUE] = self._formatfield(rfield[VALUE],field,recordEdiFile[0][VALUE])
                except botslib.InMessageFieldError:
                    txt=botslib.txtexc()
                    raise botslib.InMessageFieldError(u'line:$line pos:$pos; $txt',line=rfield[LIN],pos=rfield[POS],txt=txt)
                recorddict[field[ID][:]]=rfield[VALUE][:]   #copy string to avoid memory problems
        #****************** then: check M/C
        for tfield in trecord:
            if tfield[ISFIELD]:  #tfield is normal field (not a composite)
                if tfield[MANDATORY]==u'M' and tfield[ID] not in recorddict:
                    raise botslib.InMessageParseError(u'line:$line mandatory field "$field" not in record.',line=recordEdiFile[0][LIN],field=tfield[ID])
            else:
                compositefilled = False
                for sfield in tfield[SUBFIELDS]:  #t[2]: subfields in grammar
                    if sfield[ID] in recorddict:
                        compositefilled = True
                        break
                if compositefilled:
                    for sfield in tfield[SUBFIELDS]:  #t[2]: subfields in grammar
                        if sfield[MANDATORY]==u'M' and sfield[ID] not in recorddict:
                            raise botslib.InMessageParseError(u'line:$line mandatory subfield "$field" not in composite.',line=recordEdiFile[0][LIN],field=sfield[ID])
                if not compositefilled and tfield[MANDATORY]==u'M':
                    raise botslib.InMessageParseError(u'line:$line mandatory composite "$field" not in record.',line=recordEdiFile[0][LIN],field=tfield[ID])
        return recorddict



class csv(var):
    ''' class for ediobjects with Comma Seperated Value'''
    def _lex(self):
        super(csv,self)._lex()
        if self.ta_info['skip_firstline']:    #if first line for CSV should be skipped (contains field names)
            del self.records[0]
        if self.ta_info['noBOTSID']:    #if read records contain no BOTSID: add it
            botsid = self.defmessage.structure[0][ID]   #add the recordname as BOTSID
            for record in self.records:
                record[0:0]=[{VALUE: botsid, POS: 0, LIN: 0, SFIELD: False}]


class edifact(var):
    ''' class for edifact inmessage objects.'''
    def _readcontent_edifile(self):
        ''' read content of edi file in memory.
            For edifact: not unicode. after sniffing unicode is used to check charset (UNOA etc)
            In sniff: determine charset; then decode according to charset
        '''
        botsglobal.logger.debug(u'read edi file "%s".',self.ta_info['filename'])
        instream = botslib.opendata(self.ta_info['filename'],'rb')
        self.rawinput = instream.read()
        instream.close()


    def _sniff(self):
        ''' examine a read file for syntax parameters and correctness of protocol
            eg parse UNA, find UNB, get charset and version
        '''
        #goto char that is alphanumeric
        for count,c in enumerate(self.rawinput):
            if c.isalnum():
                break
        else:
            raise botslib.InMessageEnvelopeError(u'edi file only contains whitespace.')
        if self.rawinput[count:count+3] == 'UNA':
            unacharset=True
            self.ta_info['sfield_sep'] = self.rawinput[count+3]
            self.ta_info['field_sep'] = self.rawinput[count+4]
            self.ta_info['decimaal'] = self.rawinput[count+5]
            self.ta_info['escape'] = self.rawinput[count+6]
            self.ta_info['reserve'] = '' #self.rawinput[count+7]    #for now: no support of repeating dataelements
            self.ta_info['record_sep'] = self.rawinput[count+8]
            #goto char that is alphanumeric
            for count2,c in enumerate(self.rawinput[count+9:]):
                if c.isalnum():
                    break
            self.rawinput = self.rawinput[count+count2+9:]  #here the interchange should start; UNA is no longer needed
        else:
            unacharset=False
            self.rawinput = self.rawinput[count:]  #here the interchange should start
        if self.rawinput[:3] != 'UNB':
            raise botslib.InMessageEnvelopeError(u'No "UNB" at the start of file. Maybe not edifact.')
        self.ta_info['charset'] = self.rawinput[4:8]
        self.ta_info['version'] = self.rawinput[9:10]
        if not unacharset:
            if self.rawinput[3:4]=='+' and self.rawinput[8:9]==':':     #assume standard seperators.
                self.ta_info['sfield_sep'] = ':'
                self.ta_info['field_sep'] = '+'
                self.ta_info['decimaal'] = '.'
                self.ta_info['escape'] = '?'
                self.ta_info['reserve'] = ''    #for now: no support of repeating dataelements
                self.ta_info['record_sep'] = "'"
            elif self.rawinput[3:4]=='\x1D' and self.rawinput[8:9]=='\x1F':     #check if UNOB seperators are used
                self.ta_info['sfield_sep'] = '\x1F'
                self.ta_info['field_sep'] = '\x1D'
                self.ta_info['decimaal'] = '.'
                self.ta_info['escape'] = ''
                self.ta_info['reserve'] = ''    #for now: no support of repeating dataelements
                self.ta_info['record_sep'] = '\x1C'
            else:
                raise botslib.InMessageCharsetError(u'edi file uses non-standard seperators - should use UNA.')
        try:
            self.rawinput = self.rawinput.decode(self.ta_info['charset'],self.ta_info['checkcharsetin'])
        except LookupError:
            raise botslib.InMessageCharsetError(u'edi file has unknown charset "$charset".',charset=self.ta_info['charset'])
        except UnicodeDecodeError, flup:
            raise botslib.InMessageCharsetError(u'not allowed chars in edi file (for translation) at/after filepos: $content',content=flup[2])



    def checkenvelope(self):
        for nodeunb in self.getloop({'BOTSID':'UNB'}):
            botsglobal.logmap.debug(u'Start parsing edifact envelopes')
            UNBreference = nodeunb.get({'BOTSID':'UNB','0020':None})
            UNZreference = nodeunb.get({'BOTSID':'UNB'},{'BOTSID':'UNZ','0020':None})
            if UNBreference != UNZreference:
                raise botslib.InMessageEnvelopeError(u'UNB-reference is "$UNBreference"; should be equal to UNZ-reference "$UNZreference".',UNBreference=UNBreference,UNZreference=UNZreference)
            UNZcount = nodeunb.get({'BOTSID':'UNB'},{'BOTSID':'UNZ','0036':None})
            messagecount = len(nodeunb.children) - 1
            if int(UNZcount) != messagecount:
                raise botslib.InMessageEnvelopeError(u'Count in messages in UNZ is $UNZcount; should be equal to number of messages $messagecount.',UNZcount=UNZcount,messagecount=messagecount)
            for nodeunh in nodeunb.getloop({'BOTSID':'UNB'},{'BOTSID':'UNH'}):
                UNHreference = nodeunh.get({'BOTSID':'UNH','0062':None})
                UNTreference = nodeunh.get({'BOTSID':'UNH'},{'BOTSID':'UNT','0062':None})
                if UNHreference != UNTreference:
                    raise botslib.InMessageEnvelopeError(u'UNH-reference is "$UNHreference"; should be equal to UNT-reference "$UNTreference".',UNHreference=UNHreference,UNTreference=UNTreference)
                UNTcount = nodeunh.get({'BOTSID':'UNH'},{'BOTSID':'UNT','0074':None})
                segmentcount = nodeunh.getcount()
                if int(UNTcount) != segmentcount:
                    raise botslib.InMessageEnvelopeError(u'Segmentcount in UNT is $UNTcount; should be equal to number of segments $segmentcount.',UNTcount=UNTcount,segmentcount=segmentcount)
            for nodeung in nodeunb.getloop({'BOTSID':'UNB'},{'BOTSID':'UNG'}):
                UNGreference = nodeung.get({'BOTSID':'UNG','0048':None})
                UNEreference = nodeung.get({'BOTSID':'UNG'},{'BOTSID':'UNE','0048':None})
                if UNGreference != UNEreference:
                    raise botslib.InMessageEnvelopeError(u'UNG-reference is "$UNGreference"; should be equal to UNE-reference "$UNEreference".',UNGreference=UNGreference,UNEreference=UNEreference)
                UNEcount = nodeung.get({'BOTSID':'UNG'},{'BOTSID':'UNE','0060':None})
                groupcount = len(nodeung.children) - 1
                if int(UNEcount) != groupcount:
                    raise botslib.InMessageEnvelopeError(u'Groupcount in UNE is $UNEcount; should be equal to number of groups $groupcount.',UNEcount=UNEcount,groupcount=groupcount)
                for nodeunh in nodeung.getloop({'BOTSID':'UNG'},{'BOTSID':'UNH'}):
                    UNHreference = nodeunh.get({'BOTSID':'UNH','0062':None})
                    UNTreference = nodeunh.get({'BOTSID':'UNH'},{'BOTSID':'UNT','0062':None})
                    if UNHreference != UNTreference:
                        raise botslib.InMessageEnvelopeError(u'UNH-reference is "$UNHreference"; should be equal to UNT-reference "$UNTreference".',UNHreference=UNHreference,UNTreference=UNTreference)
                    UNTcount = nodeunh.get({'BOTSID':'UNH'},{'BOTSID':'UNT','0074':None})
                    segmentcount = nodeunh.getcount()
                    if int(UNTcount) != segmentcount:
                        raise botslib.InMessageEnvelopeError(u'Segmentcount in UNT is $UNTcount; should be equal to number of segments $segmentcount.',UNTcount=UNTcount,segmentcount=segmentcount)
            botsglobal.logmap.debug(u'Parsing edifact envelopes is OK')

class x12(var):
    ''' class for edifact inmessage objects.'''
    def _getmessagetype(self,messagetypefromsubtranslation,inode):
        if messagetypefromsubtranslation is None:
            return None
        return messagetypefromsubtranslation +  inode.record['GS08']

    def _sniff(self):
        ''' examine a read file for syntax parameters and correctness of protocol
            eg parse UNA, find UNB, get charset and version
        '''
        #goto char that is not whitespace
        for count,c in enumerate(self.rawinput):
            if not c.isspace():
                self.rawinput = self.rawinput[count:]  #here the interchange should start
                break
        else:
            raise botslib.InMessageEnvelopeError(u'edifile only contains whitespace.')
        if self.rawinput[:3] != 'ISA':
            raise botslib.InMessageEnvelopeError(u'expect "ISA", found "$content". Probably no x12?',content=self.rawinput[:7])
        count = 0
        for c in self.rawinput[:120]:
            if c in '\r\n' and count!=105:
                continue
            count +=1
            if count==4:
                self.ta_info['field_sep'] = c
            elif count==105:
                self.ta_info['sfield_sep'] = c
            elif count==106:
                self.ta_info['record_sep'] = c
                break
        # ISA-version: if <004030: SHOULD use repeating element?
        self.ta_info['reserve']=''
        self.ta_info['skip_char'] = self.ta_info['skip_char'].replace(self.ta_info['record_sep'],'') #if <CR> is segment terminator: cannot be in the skip_char-string!
        #more ISA's in file: find IEA+

    def checkenvelope(self):
        ''' check envelopes, gather information to generate 997 '''
        self.confirmationlist = []
        #~ self.root.display()
        for nodeisa in self.getloop({'BOTSID':'ISA'}):
            botsglobal.logmap.debug(u'Start parsing X12 envelopes')
            sender = nodeisa.get({'BOTSID':'ISA','ISA06':None})
            receiver = nodeisa.get({'BOTSID':'ISA','ISA08':None})
            ISAreference = nodeisa.get({'BOTSID':'ISA','ISA13':None})
            IEAreference = nodeisa.get({'BOTSID':'ISA'},{'BOTSID':'IEA','IEA02':None})
            if ISAreference != IEAreference:
                raise botslib.InMessageEnvelopeError(u'ISA-reference is "$ISAreference"; should be equal to IEA-reference "$IEAreference".',ISAreference=ISAreference,IEAreference=IEAreference)
            IEAcount = nodeisa.get({'BOTSID':'ISA'},{'BOTSID':'IEA','IEA01':None})
            #~ groupcount = len(nodeisa.children) - 1
            groupcount = nodeisa.getcountoccurrences({'BOTSID':'ISA'},{'BOTSID':'GS'})
            if int(IEAcount) != groupcount:
                raise botslib.InMessageEnvelopeError(u'Count in IEA-IEA01 is $IEAcount; should be equal to number of groups $groupcount.',IEAcount=IEAcount,groupcount=groupcount)
            for nodegs in nodeisa.getloop({'BOTSID':'ISA'},{'BOTSID':'GS'}):
                GSqualifier = nodegs.get({'BOTSID':'GS','GS01':None})
                GSreference = nodegs.get({'BOTSID':'GS','GS06':None})
                GEreference = nodegs.get({'BOTSID':'GS'},{'BOTSID':'GE','GE02':None})
                if GSreference != GEreference:
                    raise botslib.InMessageEnvelopeError(u'GS-reference is "$GSreference"; should be equal to GE-reference "$GEreference".',GSreference=GSreference,GEreference=GEreference)
                GEcount = nodegs.get({'BOTSID':'GS'},{'BOTSID':'GE','GE01':None})
                messagecount = len(nodegs.children) - 1
                if int(GEcount) != messagecount:
                    raise botslib.InMessageEnvelopeError(u'Count in GE-GE01 is $GEcount; should be equal to number of transactions: $messagecount.',GEcount=GEcount,messagecount=messagecount)
                self.confirmationlist.append({'GSqualifier':GSqualifier,'GSreference':GSreference,'GEcount':GEcount,'sender':sender,'receiver':receiver,'STlist':[]})
                for nodest in nodegs.getloop({'BOTSID':'GS'},{'BOTSID':'ST'}):
                    STqualifier = nodest.get({'BOTSID':'ST','ST01':None})
                    STreference = nodest.get({'BOTSID':'ST','ST02':None})
                    SEreference = nodest.get({'BOTSID':'ST'},{'BOTSID':'SE','SE02':None})
                    #referencefields are numerical; should I compare values??
                    if STreference != SEreference:
                        raise botslib.InMessageEnvelopeError(u'ST-reference is "$STreference"; should be equal to SE-reference "$SEreference".',STreference=STreference,SEreference=SEreference)
                    SEcount = nodest.get({'BOTSID':'ST'},{'BOTSID':'SE','SE01':None})
                    segmentcount = nodest.getcount()
                    if int(SEcount) != segmentcount:
                        raise botslib.InMessageEnvelopeError(u'Count in SE-SE01 is $SEcount; should be equal to number of segments $segmentcount.',SEcount=SEcount,segmentcount=segmentcount)
                    self.confirmationlist[-1]['STlist'].append({'STreference':STreference,'STqualifier':STqualifier})
            botsglobal.logmap.debug(u'Parsing X12 envelopes is OK')

    def close(self,ta_fromfile,error):
        ''' end of edi file handling.
            eg writing of confirmations etc.
            send 997 messages
        '''
        if error:   #check if no error
            return
        #filter the confirmationlist
        tmpconfirmationlist = []
        for confirmation in self.confirmationlist:
            if confirmation['GSqualifier'] == 'FA': #do not generate 997 for 997
                continue
            tmpmessagelist = []
            for message in confirmation['STlist']:
                if botslib.checkconfirmrules('send-x12-997',idroute=self.ta_info['idroute'],idchannel=self.ta_info['fromchannel'],
                                                topartner=confirmation['sender'],frompartner=confirmation['receiver'],
                                                editype='x12',messagetype=message['STqualifier']):
                    tmpmessagelist.append(message)
            confirmation['STlist'] = tmpmessagelist
            if not tmpmessagelist: #if no messages/transactions in GS-GE
                continue
            tmpconfirmationlist.append(confirmation)
        self.confirmationlist = tmpconfirmationlist
        for confirmation in self.confirmationlist:
            reference=str(botslib.unique('messagecounter'))
            ta_confirmation = ta_fromfile.copyta(status=TRANSLATED,reference=reference)
            filename = str(ta_confirmation.idta)
            out = outmessage.outmessage_init(editype='x12',messagetype='997004010',filename=filename)    #make outmessage object
            out.ta_info['frompartner']=confirmation['receiver']
            out.ta_info['topartner']=confirmation['sender']
            out.put({'BOTSID':'ST','ST01':'997','ST02':reference})
            out.put({'BOTSID':'ST'},{'BOTSID':'AK1','AK101':confirmation['GSqualifier'],'AK102':confirmation['GSreference']})
            out.put({'BOTSID':'ST'},{'BOTSID':'AK9','AK901':'A','AK902':confirmation['GEcount'],'AK903':confirmation['GEcount'],'AK904':confirmation['GEcount']})
            for message in confirmation['STlist']:
                lou = out.putloop({'BOTSID':'ST'},{'BOTSID':'AK2'})
                lou.put({'BOTSID':'AK2','AK201':message['STqualifier'],'AK202':message['STreference']})
                lou.put({'BOTSID':'AK2'},{'BOTSID':'AK5','AK501':'A'})
            out.put({'BOTSID':'ST'},{'BOTSID':'SE','SE01':out.getcount()+1,'SE02':reference})  #last line (counts the segments produced in out-message)
            out.writeall()   #write tomessage (result of translation)
            botsglobal.logger.debug(u'Send x12 confirmation (997) route "%s" fromchannel "%s" frompartner "%s" topartner "%s".',
                self.ta_info['idroute'],self.ta_info['fromchannel'],confirmation['receiver'],confirmation['sender'])
            self.confirminfo = dict(confirmtype='send-x12-997',confirmed=True,confirmasked = True,confirmidta=ta_confirmation.idta)  #this info is used in transform.py to update the ta.....ugly...
            ta_confirmation.update(statust=OK,**out.ta_info)    #update ta for confirmation



class tradacoms(var):
    def checkenvelope(self):
        for nodeSTX in self.getloop({'BOTSID':'STX'}):
            botsglobal.logmap.debug(u'Start parsing tradacoms envelopes')
            ENDcount = nodeSTX.get({'BOTSID':'STX'},{'BOTSID':'END','NMST':None})
            messagecount = len(nodeSTX.children) - 1
            if int(ENDcount) != messagecount:
                raise botslib.InMessageEnvelopeError(u'Count in messages in END is $ENDcount; should be equal to number of messages $messagecount',ENDcount=ENDcount,messagecount=messagecount)
            firstmessage = True
            for nodeMHD in nodeSTX.getloop({'BOTSID':'STX'},{'BOTSID':'MHD'}):
                if firstmessage:    #
                    nodeSTX.queries = {'messagetype':nodeMHD.queries['messagetype']}
                    firstmessage = False
                MTRcount = nodeMHD.get({'BOTSID':'MHD'},{'BOTSID':'MTR','NOSG':None})
                segmentcount = nodeMHD.getcount()
                if int(MTRcount) != segmentcount:
                    raise botslib.InMessageEnvelopeError(u'Segmentcount in MTR is $MTRcount; should be equal to number of segments $segmentcount',MTRcount=MTRcount,segmentcount=segmentcount)
            botsglobal.logmap.debug(u'Parsing tradacoms envelopes is OK')


class xml(Inmessage):
    ''' class for ediobjects in XML. Uses ElementTree'''
    def initfromfile(self):
        self.stack = []
        self.defmessage = grammar.grammarread(self.ta_info['editype'],self.ta_info['messagetype'])
        botslib.updateunlessset(self.ta_info,self.defmessage.syntax)    #write values from grammar to self.ta_info - unless these values are already set eg by sniffing
        etree = self._readcontent_edifile()
        etreeroot = etree.getroot()                        #get the root of the xml-file
        #~ try:
            #~ q = etree.find('message/type')
            #~ print q.tag, q.text
        #~ except:
            #~ print 'Caught',botslib.txtexc()
        self.root = self.etree2botstree(etreeroot)
        self.normalisetree(self.root)

    def etree2botstree(self,xmlnode):
        self.stack.append(xmlnode.tag)
        newnode = node.Node(self.etreenode2botstreenode(xmlnode))
        for xmlchildnode in xmlnode:   #for every node in mpathtree
            if self.isfield(xmlchildnode):    #if no child entities: treat as 'field': this misses xml where attributes are used as fields....testing for repeating is no good...
                if xmlchildnode.text and not xmlchildnode.text.isspace(): #skip empty xml entity
                    newnode.record[xmlchildnode.tag]=xmlchildnode.text      #add as a field
                    hastxt = True
                else:
                    hastxt = False
                for key,value in xmlchildnode.items():   #convert attributes to fields.
                    if not hastxt:
                        newnode.record[xmlchildnode.tag]=''      #add empty content
                        hastxt = True
                    newnode.record[xmlchildnode.tag + self.ta_info['attributemarker'] + key]=value      #add as a field
            else:   #xmlchildnode is a record
                newnode.append(self.etree2botstree(xmlchildnode))           #add as a node/record
        #~ if botsglobal.ini.getboolean('settings','readrecorddebug',False):
            #~ botsglobal.logger.debug('read record "%s":',newnode.record['BOTSID'])
            #~ for key,value in newnode.record.items():
                #~ botsglobal.logger.debug('    "%s" : "%s"',key,value)
        self.stack.pop()
        #~ print self.stack
        return newnode

    def etreenode2botstreenode(self,xmlnode):
        ''' build a dict from xml-node'''
        build = dict((xmlnode.tag + self.ta_info['attributemarker'] + key,value) for key,value in xmlnode.items())   #convert attributes to fields.
        build['BOTSID']=xmlnode.tag     #'record' tag
        if xmlnode.text and not xmlnode.text.isspace():
            build['BOTSCONTENT']=xmlnode.text
        return build

    def isfield(self,xmlchildnode):
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
                raise botslib.InMessageParseError(u'Unknown XML-tag in "$record".',record=record)
        for str_record in str_recordlist:   #see if xmlchildnode is in structure
            #~ print '    is xmlhildnode in this level comparing',xmlchildnode.tag,str_record[0]
            if xmlchildnode.tag == str_record[0]:
                #~ print 'found'
                return False
        #xml tag not found in structure: so must be field; validity is check later on with grammar
        if len(xmlchildnode)==0:
            return True
        return False
        
    def _readcontent_edifile(self):
        ''' read content of edi file to memory.
        '''
        botsglobal.logger.debug(u'read edi file "%s".',self.ta_info['filename'])
        filename=botslib.abspathdata(self.ta_info['filename'])
        parser = ET.XMLParser()
        version = str(sys.version_info[0]) + str(sys.version_info[1])
        if version != '24':
            for key,value in self.ta_info['extra_character_entity'].items():
                parser.entity[key] = value
        e =  ET.ElementTree()   #ElementTree: lexes, parses, makes etree; etree is quite simular to bots-node trees but some conversions is needed
        e.parse(filename, parser)
        return e


class xmlnocheck(xml):
    ''' class for ediobjects in XML. Uses ElementTree'''
    def normalisetree(self,node):
        pass

    def isfield(self,xmlchildnode):
        if len(xmlchildnode)==0:
            return True
        return False

class json(Inmessage):
    def initfromfile(self):
        import simplejson
        self.defmessage = grammar.grammarread(self.ta_info['editype'],self.ta_info['messagetype'])
        botslib.updateunlessset(self.ta_info,self.defmessage.syntax)    #write values from grammar to self.ta_info - unless these values are already set eg by sniffing
        self._readcontent_edifile()
        
        jsonobject = simplejson.loads(self.rawinput)
        del self.rawinput
        if isinstance(jsonobject,list):
            self.root=node.Node()  #initialise empty node.
            self.root.children = self.dojsonlist(jsonobject,self.getrootID())   #fill root with children
            for child in self.root.children:
                if not child.record:    #sanity test: the children must have content
                    raise botslib.InMessageNoContentError(u'JSON text has no usable content.')
                self.normalisetree(child)
        elif isinstance(jsonobject,dict):
            if len(jsonobject)==1 and isinstance(jsonobject.values()[0],dict):
                # best structure: {rootid:{id2:<dict, list>}}
                self.root = self.dojsonobject(jsonobject.values()[0],jsonobject.keys()[0])
            elif len(jsonobject)==1 and isinstance(jsonobject.values()[0],list) : 
                #root dict has no name; use value from grammar for rootID; {id2:<dict, list>}
                #~ {'article': 
                    #~ [
                    #~ {'ccodeid': 'artikel', 'leftcode': 'leftcode', 'rightcode': 'rightcode'}, 
                    #~ {'ccodeid': 'artikel', 'leftcode': 'leftcode2', 'rightcode': 'rightcode'},
                    #~ ]
                #~ }
                self.root=node.Node({'BOTSID': self.getrootID()})  #initialise empty node.
                self.root.children = self.dojsonlist(jsonobject.values()[0],jsonobject.keys()[0])
            else:
                #~ print self.getrootID()
                self.root = self.dojsonobject(jsonobject,self.getrootID())
                #~ print self.root
            if not self.root:
                raise botslib.InMessageNoContentError(u'JSON text has no usable content.')
            self.normalisetree(self.root)
        else:
            #root in JSON is neither dict or list. 
            raise botslib.MessageError(u'Content in JSON file must be a "list" or "object".')

    def getrootID(self):
        return self.defmessage.structure[0][ID]

    def dojsonlist(self,jsonobject,name):
        lijst=[] #initialise empty list, used to append a listof (converted) json objects
        for i in jsonobject:
            if isinstance(i,dict):  #check list item is dict/object
                newnode = self.dojsonobject(i,name)
                if newnode:
                    lijst.append(newnode)
            elif self.ta_info['checkunknownentities']:
                raise botslib.MessageError(u'List content in JSON must be a "object".')
        return lijst

    def dojsonobject(self,jsonobject,name):
        thisnode=node.Node({})  #initialise empty node.
        for key,value in jsonobject.items():
            if value is None:
                continue
            elif isinstance(value,basestring):  #json field; map to field in node.record
                thisnode.record[key]=value
            elif isinstance(value,dict):
                newnode = self.dojsonobject(value,key)
                if newnode:
                    thisnode.append(newnode)
            elif isinstance(value,list):
                thisnode.children.extend(self.dojsonlist(value,key))
            elif isinstance(value,int) or isinstance(value,long) or isinstance(value,float):  #json field; map to field in node.record
                thisnode.record[key]=str(value)
            else:
                if self.ta_info['checkunknownentities']:
                    raise botslib.MessageError(u'Key "$key" value "$value": is not string, list or dict.',key=key,value=value)
                thisnode.record[key]=str(value)
        if not thisnode.record and not thisnode.children:
            return None #node is empty...
        thisnode.record['BOTSID']=name
        return thisnode


class jsonnocheck(json):
    def normalisetree(self,node):
        pass

    def getrootID(self):
        return self.ta_info['defaultBOTSIDroot']   #as there is no structure in grammar, use value form syntax.

class database(jsonnocheck):
    pass
