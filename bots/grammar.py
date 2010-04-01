import copy
import botslib
import botsglobal
from botsconfig import *

def grammarread(editype,grammarname):
    ''' despatch function for class Grammar or subclass
        read whole grammar
    '''
    botsglobal.logger.debug(u'read grammar for editype "%s", messagetype "%s".',editype,grammarname)
    try:
        classtocall = globals()[editype]
    except KeyError:
        raise botslib.GrammarEdiTypeNotKnownError(editype)
    terug = classtocall('grammars',editype,grammarname)
    terug.initsyntax(includedefault=True)
    terug.initrestofgrammar()
    botsglobal.logger.debug(u'finished reading grammar for editype "%s", messagetype "%s".',editype,grammarname)
    return terug
    
def syntaxread(soortpythonfile,editype,grammarname):
    ''' despatch function for class Grammar or subclass
        read only grammar
    '''
    try:
        classtocall = globals()[editype]
    except KeyError:
        raise botslib.GrammarEdiTypeNotKnownError(editype)
    terug = classtocall(soortpythonfile,editype,grammarname)
    terug.initsyntax(includedefault=False)
    return terug

class Grammar(object):
    ''' Class for translation grammar. The grammar is used in reading or writing an edi file.
        Description of the grammar file: see user manual.
        The grammar is read from the grammar file.
        The information in a grammar is checked and manipulated.
        
        structure of self.grammar:
            is a list of dict
            attributes of dict: see header.py
            -   ID       record id
            -   MIN      min #occurences record or group
            -   MAX      max #occurences record of group
            -   COUNT    added after read
            -   MPATH    mpath of record (only record-ids). added after read
            -   FIELDS   tuple of the fields in record. Added ather read from separate record.py-file
            -   LEVEL    child-records
        structure of fields:
            fields is tuple of (field or subfield)
            field is tuple of (ID, MANDATORY, LENGTH, FORMAT)
            subfield is tuple of (ID, MANDATORY, tuple of fields)
    '''
    _checkstructurerequired=True
    
    def __init__(self,soortpythonfile,editype,grammarname):
        #***********import grammar-file. Grammar file has several grammar parts , eg 'structure'and 'recorddefs'. 
        #***********every grammar part is in a module is either the grammar part itself or a import from another module.
        #***********every module is read once, using python import-machinery.
        #***********if a structure of recorddef has been read, Bots remembers this and skip most of the checks
        self.module,self.grammarname = botslib.botsimport(soortpythonfile,editype + '.' + grammarname)
        
    def initsyntax(self,includedefault):
        ''' Update default syntax from class with syntax read from grammar. '''
        if includedefault:
            self.syntax = copy.deepcopy(self.__class__.defaultsyntax)  #copy syntax from class data
        else:
            self.syntax = {}
        try:
            syntaxfromgrammar = getattr(self.module, 'syntax')
        except AttributeError:
            pass    #there is no syntax in the grammar, is OK.
        else:
            if not isinstance(syntaxfromgrammar,dict):
                raise botslib.GrammarError(u'Grammar "$grammar": syntax is not a dict{}.',grammar=self.grammarname)
            self.syntax.update(syntaxfromgrammar)
        
    def initrestofgrammar(self):
        try:    
            self.nextmessage = getattr(self.module, 'nextmessage')
        except AttributeError:  #if grammarpart does not exist set to None; test required grammarpart elsewhere
            self.nextmessage = None
        try:    
            self.nextmessage2 = getattr(self.module, 'nextmessage2')
            if self.nextmessage is None:
                raise botslib.GrammarError(u'Grammar "$grammar": if nextmessage2: nextmessage has to be used.',grammar=self.grammarname)
        except AttributeError:  #if grammarpart does not exist set to None; test required grammarpart elsewhere
            self.nextmessage2 = None
        try:    
            self.nextmessageblock = getattr(self.module, 'nextmessageblock')
            if self.nextmessage:
                raise botslib.GrammarError(u'Grammar "$grammar": nextmessageblock and nextmessage not both allowed.',grammar=self.grammarname)
        except AttributeError:  #if grammarpart does not exist set to None; test required grammarpart elsewhere
            self.nextmessageblock = None
        if self._checkstructurerequired:
            self._dostructure()
            self._dorecorddefs()
            self._linkrecorddefs2structure(self.structure)
            if self.syntax['noBOTSID'] and len(self.recorddefs) != 1:
                raise botslib.GrammarError(u'Grammar "$grammar": if syntax["noBOTSID"]: there can be only one record in recorddefs.',grammar=self.grammarname)
            if self.nextmessageblock is not None and len(self.recorddefs) != 1:
                raise botslib.GrammarError(u'Grammar "$grammar": if nextmessageblock: there can be only one record in recorddefs.',grammar=self.grammarname)

    def _dorecorddefs(self):
        ''' 1. check the recorddefinitions for validity.
            2. adapt in field-records: normalise length lists, set bool ISFIELD, etc
            3. remember that recorddef is checked and adapted (so when grammar is read again, no checking/adapt needed)
        '''
        try:    
            recorddefsfromgrammar = getattr(self.module, 'recorddefs')
        except AttributeError:  #if grammarpart does not exist set to None; test required grammarpart elsewhere
            raise botslib.GrammarError(u'Grammar "$grammar": no recorddefs.',grammar=self.grammarname)
        self.recorddefs = copy.deepcopy(recorddefsfromgrammar)
        if not isinstance(self.recorddefs,dict):
            raise botslib.GrammarError(u'Grammar "$grammar": recorddefs is not a dict{}.',grammar=self.grammarname)
        for recordID ,fields in self.recorddefs.iteritems():
            for field in fields:    #check if field 'BOTSID' is present:
                if field[ID] == 'BOTSID':
                    break
            else:   #so there is no field 'BOTSID' in record
                raise botslib.GrammarFieldError(u'Grammar "$grammar", record "$record": no field BOTSID.',grammar=self.grammarname,record=recordID)
            if not isinstance(recordID,basestring):
                raise botslib.GrammarFieldError(u'Grammar "$grammar", record "$record": is not a string.',grammar=self.grammarname,record=recordID)
            if not recordID:
                raise botslib.GrammarFieldError(u'Grammar "$grammar", record "$record": recordID with empty string.',grammar=self.grammarname,record=recordID)
            if not isinstance(fields,list):
                raise botslib.GrammarFieldError(u'Grammar "$grammar", record "$record": no correct fields found.',grammar=self.grammarname,record=recordID)
            if isinstance(self,xml) or isinstance(self,json):
                if len (fields) < 1:
                    raise botslib.GrammarFieldError(u'Grammar "$grammar", record "$record": too few fields.',grammar=self.grammarname,record=recordID)
            else:
                if len (fields) < 2:
                    raise botslib.GrammarFieldError(u'Grammar "$grammar", record "$record": too few fields.',grammar=self.grammarname,record=recordID)
            for field in fields:
                self._checkfield(field,recordID)
                if not field[ISFIELD]:  # if composite
                    for sfield in field[SUBFIELDS]:
                        self._checkfield(sfield,recordID)
        #~ recorddefset.add(id(self.recorddefs))    #remember that this recorddef has already been checked
        
    def _checkfield(self,field,recordID):
        #'normalise' field: make list equal length
        if len(field) == 3:  # that is: composite
            field +=[None,False,None,None,'A']
            #~ field[ISFIELD] = 
        elif len(field) == 4:               # that is: field (not a composite)
            field +=[True,0,0,'A']
            #~ field[ISFIELD] = True
            #~ field[MINLENGTH] = 0
        elif len(field) == 8:               # this happens when there are errors in a table and table is read again
            raise botslib.GrammarFieldError(u'Grammar "$grammar": error in grammar; error is already reported in this run.',grammar=self.grammarname)
        else:
            raise botslib.GrammarFieldError(u'Grammar "$grammar", record "$record", field "$field": list has invalid number of arguments.',grammar=self.grammarname,record=recordID,field=field[ID])
        if not isinstance(field[ID],basestring) or not field[ID]:
            raise botslib.GrammarFieldError(u'Grammar "$grammar", record "$record", field "$field": fieldID has to be a string.',grammar=self.grammarname,record=recordID,field=field[ID])
        if not isinstance(field[MANDATORY],basestring):
            raise botslib.GrammarFieldError(u'Grammar "$grammar", record "$record", field "$field": mandatory/conditional has to be a string.',grammar=self.grammarname,record=recordID,field=field[ID])
        if not field[MANDATORY] or field[MANDATORY] not in ['M','C']:
            raise botslib.GrammarFieldError(u'Grammar "$grammar", record "$record", field "$field": mandatory/conditional must be "M" or "C".',grammar=self.grammarname,record=recordID,field=field[ID])
        if field[ISFIELD]:  # that is: field, and not a composite
            #get MINLENGTH (from tuple or if fixed
            if isinstance(field[LENGTH],tuple):
                if not isinstance(field[LENGTH][0],int) and not isinstance(field[LENGTH][0],float):
                    raise botslib.GrammarFieldError(u'Grammar "$grammar", record "$record", field "$field": min length "$min" has to be a number.',grammar=self.grammarname,record=recordID,field=field[ID],min=field[LENGTH])
                if not isinstance(field[LENGTH][1],int) and not isinstance(field[LENGTH][1],float):
                    raise botslib.GrammarFieldError(u'Grammar "$grammar", record "$record", field "$field": max length "$max" has to be a number.',grammar=self.grammarname,record=recordID,field=field[ID],max=field[LENGTH])
                if field[LENGTH][0] > field[LENGTH][1]:
                    raise botslib.GrammarFieldError(u'Grammar "$grammar", record "$record", field "$field": min length "$min" must be > max length "$max".',grammar=self.grammarname,record=recordID,field=field[ID],min=field[LENGTH][0],max=field[LENGTH][1])
                field[MINLENGTH]=field[LENGTH][0]
                field[LENGTH]=field[LENGTH][1]
            elif isinstance(field[LENGTH],int) or isinstance(field[LENGTH],float):
                if isinstance(self,fixed):
                    field[MINLENGTH]=field[LENGTH]
            else:
                raise botslib.GrammarFieldError(u'Grammar "$grammar", record "$record", field "$field": length "$len" has to be number or (min,max).',grammar=self.grammarname,record=recordID,field=field[ID],len=field[LENGTH])
            if field[LENGTH] < 1:
                raise botslib.GrammarFieldError(u'Grammar "$grammar", record "$record", field "$field": length "$len" has to be at least 1.',grammar=self.grammarname,record=recordID,field=field[ID],len=field[LENGTH])
            if field[MINLENGTH] < 0:
                raise botslib.GrammarFieldError(u'Grammar "$grammar", record "$record", field "$field": minlength "$len" has to be at least 0.',grammar=self.grammarname,record=recordID,field=field[ID],len=field[LENGTH])
            #format
            if not isinstance(field[FORMAT],basestring):
                raise botslib.GrammarFieldError(u'Grammar "$grammar", record "$record", field "$field": format "$format" has to be a string.',grammar=self.grammarname,record=recordID,field=field[ID],format=field[FORMAT])
            self._manipulatefieldformat(field,recordID)
            #~ if field[FORMAT] in ['N','I','R']:
            if field[BFORMAT] in ['N','I','R']:
                if isinstance(field[LENGTH],float):
                    field[DECIMALS] = int( round((field[LENGTH]-int(field[LENGTH]))*10) )  #fill DECIMALS
                    field[LENGTH] = int( round(field[LENGTH]))
                    if field[DECIMALS] >= field[LENGTH]:
                        raise botslib.GrammarFieldError(u'Grammar "$grammar", record "$record", field "$field": field length "$len" has to be greater that nr of decimals "$decimals".',grammar=self.grammarname,record=recordID,field=field[ID],len=field[LENGTH],decimals=field[DECIMALS])
                if isinstance(field[MINLENGTH],float):
                    field[MINLENGTH] = int( round(field[MINLENGTH]))
            else:   #if format 'R', A, D, T
                if isinstance(field[LENGTH],float):
                    raise botslib.GrammarFieldError(u'Grammar "$grammar", record "$record", field "$field": if format "$format", no length "$len".',grammar=self.grammarname,record=recordID,field=field[ID],format=field[FORMAT],len=field[LENGTH])
                if isinstance(field[MINLENGTH],float):
                    raise botslib.GrammarFieldError(u'Grammar "$grammar", record "$record", field "$field": if format "$format", no minlength "$len".',grammar=self.grammarname,record=recordID,field=field[ID],format=field[FORMAT],len=field[MINLENGTH])
        else:       #check composite
            if not isinstance(field[SUBFIELDS],list):
                raise botslib.GrammarFieldError(u'Grammar "$grammar", record "$record", field "$field": is a composite field, has to have subfields.',grammar=self.grammarname,record=recordID,field=field[ID])
            if len(field[SUBFIELDS]) < 2:
                raise botslib.GrammarFieldError(u'Grammar "$grammar", record "$record", field "$field" has < 2 sfields.',grammar=self.grammarname,record=recordID,field=field[ID])
            
    def _linkrecorddefs2structure(self,structure):
        ''' recursive
            for each record in structure: add the pointer to the right recorddefinition.
        '''
        for i in structure:
            try:
                i[FIELDS] = self.recorddefs[i[ID]]
            except KeyError:
                raise botslib.GrammarError(u'Grammar "$grammar": in recorddef no record "$record".',grammar=self.grammarname,record=i[ID])
            if LEVEL in i:
                self._linkrecorddefs2structure(i[LEVEL])

    def _dostructure(self):
        ''' 1. check the structure for validity.
            2. adapt in structure: Add keys: mpath, count
            3. remember that structure is checked and adapted (so when grammar is read again, no checking/adapt needed)
        '''
        try:    
            structurefromgrammar = getattr(self.module, 'structure')
        except AttributeError:  #if grammarpart does not exist set to None; test required grammarpart elsewhere
            raise botslib.GrammarError(u'Grammar "$grammar": no structure, is required.',grammar=self.grammarname)
        self.structure = copy.deepcopy(structurefromgrammar)
        if len(self.structure) != 1:                        #every structure has only 1 root!!
            raise botslib.GrammarError(u'Grammar "$grammar", in structure: only one root record allowed.',grammar=self.grammarname)
        self._checkstructure(self.structure,[])
        if self.syntax['checkcollision']:
            self._checkbackcollision(self.structure)
            self._checknestedcollision(self.structure)
            self._checkbotscollision(self.structure)

    def _checkstructure(self,structure,mpath):
        ''' Recursive
            1.   Checks sanity of structure.All kinds of things are checked
            2.   Add keys: mpath, count
        '''
        if not isinstance(structure,list):
            raise botslib.GrammarError(u'Grammar "$grammar", in structure, at "$mpath": not a list.',grammar=self.grammarname,mpath=mpath)
        for i in structure:
            if not isinstance(i,dict):
                raise botslib.GrammarError(u'Grammar "$grammar", in structure, at "$mpath": record should be a dict: "$record".',grammar=self.grammarname,mpath=mpath,record=i)
            if ID not in i:
                raise botslib.GrammarError(u'Grammar "$grammar", in structure, at "$mpath": record without ID: "$record".',grammar=self.grammarname,mpath=mpath,record=i)
            if not isinstance(i[ID],basestring):
                raise botslib.GrammarError(u'Grammar "$grammar", in structure, at "$mpath": recordID of record is not a string: "$record".',grammar=self.grammarname,mpath=mpath,record=i)
            if not i[ID]:   
                raise botslib.GrammarError(u'Grammar "$grammar", in structure, at "$mpath": recordID of record is empty: "$record".',grammar=self.grammarname,mpath=mpath,record=i)
            if MIN not in i:
                raise botslib.GrammarError(u'Grammar "$grammar", in structure, at "$mpath": record without MIN: "$record".',grammar=self.grammarname,mpath=mpath,record=i)
            if MAX not in i:
                raise botslib.GrammarError(u'Grammar "$grammar", in structure, at "$mpath": record without MAX: "$record".',grammar=self.grammarname,mpath=mpath,record=i)
            if not isinstance(i[MIN],int):
                raise botslib.GrammarError(u'Grammar "$grammar", in structure, at "$mpath": record where MIN is not whole number: "$record".',grammar=self.grammarname,mpath=mpath,record=i)
            if not isinstance(i[MAX],int):
                raise botslib.GrammarError(u'Grammar "$grammar", in structure, at "$mpath": record where MAX is not whole number: "$record".',grammar=self.grammarname,mpath=mpath,record=i)
            if i[MIN] > i[MAX]:
                raise botslib.GrammarError(u'Grammar "$grammar", in structure, at "$mpath": record where MIN > MAX: "$record".',grammar=self.grammarname,mpath=mpath,record=str(i)[:100])
            i[MPATH]=mpath+[[i[ID]]]
            i[COUNT]=0
            if LEVEL in i:
                self._checkstructure(i[LEVEL],i[MPATH])
                
    def _checkbackcollision(self,structure,collision=None):
        ''' Recursive.
            Check if grammar has collision problem.
            A message with collision problems is ambigious.
        '''
        headerissave = False
        if not collision:
            collision=[]
        for i in structure:
            #~ print 'check back',i[MPATH], 'with',collision
            if i[ID] in collision:
                raise botslib.GrammarError(u'Grammar "$grammar", in structure: back-collision detected at record "$mpath".',grammar=self.grammarname,mpath=i[MPATH])
            if i[MIN]:
                collision = []
                headerissave = True
            collision.append(i[ID])
            if LEVEL in i:
                returncollision,returnheaderissave = self._checkbackcollision(i[LEVEL],[i[ID]])
                collision.extend(returncollision)
                if returnheaderissave:  #if one of segment(groups) is required, there is always a segment after the header segment; so remove header from nowcollision:
                    collision.remove(i[ID])
        return collision,headerissave    #collision is used to update on higher level; cleared indicates the header segment can not collide anymore

    def _checkbotscollision(self,structure,collision=None):
        ''' Recursive.
            Within one level: no twice the same tag. Bots can not handle this.
        '''
        if not collision:
            collision=[]
        for i in structure:
            if i[ID] in collision:
                raise botslib.GrammarError(u'Grammar "$grammar", in structure: bots-collision detected at record "$mpath".',grammar=self.grammarname,mpath=i[MPATH])
            collision.append(i[ID])
            if LEVEL in i:
                self._checkbotscollision(i[LEVEL])
        return

    def _checknestedcollision(self,structure,collision=None):
        ''' Recursive.
            Check if grammar has collision problem.
            A message with collision problems is ambigious.
        '''
        if not collision:
            levelcollision = []
        else:
            levelcollision = collision[:]
        for i in reversed(structure):
            checkthissegment = True
            if LEVEL in i:
                checkthissegment = self._checknestedcollision(i[LEVEL],levelcollision + [i[ID]])
            #~ print 'check nested',checkthissegment, i[MPATH], 'with',levelcollision
            if checkthissegment and i[ID] in levelcollision:
                raise botslib.GrammarError(u'Grammar "$grammar", in structure: nesting collision detected at record "$mpath".',grammar=self.grammarname,mpath=i[MPATH])
            if i[MIN]:
                levelcollision = []   #enmpty uppercollision
        return bool(levelcollision)


    def display(self,structure,level=0):
        ''' Draw grammar, with indentation for levels.
            For debugging.
        '''
        for i in structure:
            print 'Record: ',i[MPATH]
            for field in i[FIELDS]:
                print '    Field: ',field
            if LEVEL in i:
                self.display(i[LEVEL],level+1)

    formatconvert = {
        'A':'A',
        'AN':'A',
        'D':'D',
        'DT':'D',
        'T':'T',
        'TM':'T',
        'N':'N',
        'I':'I',
        'R':'R',
        }
    def _manipulatefieldformat(self,field,recordID):
        try:
            field[BFORMAT] = self.formatconvert[field[FORMAT]]
        except KeyError:
            raise botslib.GrammarFieldError(u'Grammar "$grammar", record "$record", field "$field": format "$format" has to be one of "$keys".',grammar=self.grammarname,record=recordID,field=field[ID],format=field[FORMAT],keys=self.formatconvert.keys())

#the grammar subclasses, equivalent to the editypes Bots can handle.
#contains the defaultsyntax
class test(Grammar):
    defaultsyntax = {
        'checkcollision':True,
        'noBOTSID':False,
        }
        
class csv(Grammar):
    defaultsyntax = {
        'acceptspaceinnumfield':True,   #only really used in fixed formats
        'add_crlfafterrecord_sep':'',
        'charset':'utf-8',
        'checkcharsetin':'strict', #strict, ignore or botsreplace (replace with char as set in bots.ini).
        'checkcharsetout':'strict', #strict, ignore or botsreplace (replace with char as set in bots.ini).
        'checkcollision':True,
        'checkunknownentities': True,
        'contenttype':'text/csv',
        'decimaal':'.',
        'envelope':'',
        'escape':"",
        'field_sep':':',
        'forcequote':'1',    #(if quote_char is set) 0:no force: only quote if neccesary:1:always force: 2:??etcetc
        'lengthnumericbare':False,
        'merge':True,
        'noBOTSID':False,
        'pass_all':True,
        'quote_char':"'",
        'record_sep':"\r\n",
        'record_tag_sep':"",    #Tradacoms/GTDI
        'reserve':'',
        'sfield_sep':'',
        'skip_char':'',
        'skip_firstline':False,
        'stripfield_sep':False, #safe choice, as csv is no real standard
        'triad':'',
        }
        
class fixed(Grammar):
    defaultsyntax = {
        'acceptspaceinnumfield':True,   #only really used in fixed formats
        'add_crlfafterrecord_sep':'',
        'charset':'us-ascii',
        'checkcharsetin':'strict', #strict, ignore or botsreplace (replace with char as set in bots.ini).
        'checkcharsetout':'strict', #strict, ignore or botsreplace (replace with char as set in bots.ini).
        'checkcollision':True,
        'checkfixedrecordtoolong':True,
        'checkfixedrecordtooshort':False,
        'checkunknownentities': True,
        'contenttype':'text/plain',
        'decimaal':'.',
        'endrecordID':3,
        'envelope':'',
        'escape':'',
        'field_sep':'',
        'forcequote':'', #(if quote_char is set) 0:no force: only quote if neccesary:1:always force: 2:??etcetc
        'lengthnumericbare':False,
        'merge':True,
        'noBOTSID':False,
        'pass_all':False,
        'quote_char':"",
        'record_sep':"\r\n",
        'record_tag_sep':"",    #Tradacoms/GTDI
        'reserve':'',
        'sfield_sep':'',
        'skip_char':'',
        'startrecordID':0,
        'stripfield_sep':False,
        'triad':'',
        }
        
class idoc(fixed):
    defaultsyntax = {
        'acceptspaceinnumfield':True,   #only really used in fixed formats
        'add_crlfafterrecord_sep':'',
        'automaticcount':True,
        'charset':'us-ascii',
        'checkcharsetin':'strict', #strict, ignore or botsreplace (replace with char as set in bots.ini).
        'checkcharsetout':'strict', #strict, ignore or botsreplace (replace with char as set in bots.ini).
        'checkcollision':True,
        'checkfixedrecordtoolong':False,
        'checkfixedrecordtooshort':False,
        'checkunknownentities': True,
        'contenttype':'text/plain',
        'decimaal':'.',
        'endrecordID':10,
        'envelope':'',
        'escape':'',
        'field_sep':'',
        'forcequote':'', #(if quote_char is set) 0:no force: only quote if neccesary:1:always force: 2:??etcetc
        'lengthnumericbare':False,
        'merge':False,
        'noBOTSID':False,
        'pass_all':False,
        'quote_char':"",
        'record_sep':"\r\n",
        'record_tag_sep':"",    #Tradacoms/GTDI
        'reserve':'',
        'sfield_sep':'',
        'skip_char':'',
        'startrecordID':0,
        'stripfield_sep':False,
        'triad':'',
        'MANDT':'0',
        'DOCNUM':'0',
        }
        
class xml(Grammar):
    defaultsyntax = {
        'add_crlfafterrecord_sep':'',
        'acceptspaceinnumfield':True,   #only really used in fixed formats
        'attributemarker':'__',
        'charset':'utf-8',
        'checkcharsetin':'strict', #strict, ignore or botsreplace (replace with char as set in bots.ini).
        'checkcharsetout':'strict', #strict, ignore or botsreplace (replace with char as set in bots.ini).
        'checkcollision':False,
        'checkunknownentities': True,   #??changed later
        'contenttype':'text/xml ',
        'decimaal':'.',
        'DOCTYPE':'',                   #doctype declaration to use in xml header. DOCTYPE = 'mydoctype SYSTEM "mydoctype.dtd"'  will lead to: <!DOCTYPE mydoctype SYSTEM "mydoctype.dtd">
        'envelope':'',
        'extra_character_entity':{},    #additional character entities to resolve when parsing XML; mostly html character entities. Not in python 2.4. Example: {'euro':u'','nbsp':unichr(160),'apos':u'\u0027'}
        'escape':'',
        'field_sep':'',
        'flattenxml': False,            #not used anymore
        'forcequote':'',                #(if quote_char is set) 0:no force: only quote if neccesary:1:always force: 2:??etcetc
        'indented':False,               #False: xml output is one string (no cr/lf); True: xml output is indented/human readable
        'lengthnumericbare':False,
        'merge':False,
        'noBOTSID':False,
        'pass_all':False,
        'processing_instructions': None,    #to generate processing instruction in xml prolog. is a list, consisting of tuples, each tuple consists of type of instruction and text for instruction.
                                            #Example: processing_instructions': [('xml-stylesheet' ,'href="mystylesheet.xsl" type="text/xml"'),('type-of-ppi' ,'attr1="value1" attr2="value2"')]  
                                            #leads to this output in xml-file:  <?xml-stylesheet href="mystylesheet.xsl" type="text/xml"?><?type-of-ppi attr1="value1" attr2="value2"?>
        'quote_char':"",
        'record_sep':"",
        'record_tag_sep':"",    #Tradacoms/GTDI
        'reserve':'',
        'sfield_sep':'',
        'skip_char':'',
        'standalone':None,      #as used in xml prolog; values: 'yes' , 'no' or None (not used)
        'stripfield_sep':False,
        'triad':'',
        'version':'1.0',        #as used in xml prolog
        }
class xmlnocheck(xml):
    _checkstructurerequired=False
    defaultsyntax = {
        'add_crlfafterrecord_sep':'',
        'acceptspaceinnumfield':True,   #only really used in fixed formats
        'attributemarker':'__',
        'charset':'utf-8',
        'checkcharsetin':'strict', #strict, ignore or botsreplace (replace with char as set in bots.ini).
        'checkcharsetout':'strict', #strict, ignore or botsreplace (replace with char as set in bots.ini).
        'checkcollision':False,
        'checkunknownentities': False,
        'contenttype':'text/xml ',
        'decimaal':'.',
        'DOCTYPE':'',                   #doctype declaration to use in xml header. DOCTYPE = 'mydoctype SYSTEM "mydoctype.dtd"'  will lead to: <!DOCTYPE mydoctype SYSTEM "mydoctype.dtd">
        'envelope':'',
        'escape':'',
        'extra_character_entity':{},    #additional character entities to resolve when parsing XML; mostly html character entities. Not in python 2.4. Example: {'euro':u'','nbsp':unichr(160),'apos':u'\u0027'}
        'field_sep':'',
        'flattenxml': False,            #not used anymore
        'forcequote':'',                #(if quote_char is set) 0:no force: only quote if neccesary:1:always force: 2:??etcetc
        'indented':False,               #False: xml output is one string (no cr/lf); True: xml output is indented/human readable
        'lengthnumericbare':False,
        'merge':False,
        'noBOTSID':False,
        'pass_all':False,
        'processing_instructions': None,    #to generate processing instruction in xml prolog. is a list, consisting of tuples, each tuple consists of type of instruction and text for instruction.
                                            #Example: processing_instructions': [('xml-stylesheet' ,'href="mystylesheet.xsl" type="text/xml"'),('type-of-ppi' ,'attr1="value1" attr2="value2"')]  
                                            #leads to this output in xml-file:  <?xml-stylesheet href="mystylesheet.xsl" type="text/xml"?><?type-of-ppi attr1="value1" attr2="value2"?>
        'quote_char':"",
        'record_sep':"",
        'record_tag_sep':"",    #Tradacoms/GTDI
        'reserve':'',
        'sfield_sep':'',
        'skip_char':'',
        'standalone':None,      #as used in xml prolog; values: 'yes' , 'no' or None (not used)
        'stripfield_sep':False,
        'triad':'',
        'version':'1.0',        #as used in xml prolog
        }
        
class template(Grammar):
    _checkstructurerequired=False
    
    defaultsyntax = { \
        'add_crlfafterrecord_sep':'',
        'charset':'utf-8',
        'checkcharsetin':'strict', #strict, ignore or botsreplace (replace with char as set in bots.ini).
        'checkcharsetout':'strict', #strict, ignore or botsreplace (replace with char as set in bots.ini).
        'checkcollision':False,
        'contenttype':'text/xml',
        'checkunknownentities': True,
        'decimaal':'.',
        'envelope':'template',
        'envelope-template':'',
        'escape':'',
        'field_sep':'',
        'forcequote':'',    #(if quote_char is set) 0:no force: only quote if neccesary:1:always force: 2:??etcetc
        'lengthnumericbare':False,
        'merge':True,
        'noBOTSID':False,
        'output':'xhtml-strict',
        'quote_char':"",
        'pass_all':False,
        'record_sep':"",
        'record_tag_sep':"",    #Tradacoms/GTDI
        'reserve':'',
        'sfield_sep':'',
        'skip_char':'',
        'stripfield_sep':False,
        'triad':'',
        }
        
class edifact(Grammar):
    defaultsyntax = {
        'add_crlfafterrecord_sep':'\r\n',
        'acceptspaceinnumfield':True,   #only really used in fixed formats
        'charset':'UNOA',
        'checkcharsetin':'strict', #strict, ignore or botsreplace (replace with char as set in bots.ini).
        'checkcharsetout':'strict', #strict, ignore or botsreplace (replace with char as set in bots.ini).
        'checkcollision':True,
        'checkunknownentities': True,
        'contenttype':'application/EDIFACT',
        'decimaal':'.',
        'envelope':'edifact',
        'escape':'?',
        'field_sep':'+',
        'forcequote':'',    #(if quote_char is set) 0:no force: only quote if neccesary:1:always force: 2:??etcetc
        'forceUNA' : False,
        'lengthnumericbare':True,
        'merge':True,
        'noBOTSID':False,
        'pass_all':False,
        'quote_char':'',
        'record_sep':"'",
        'record_tag_sep':"",    #Tradacoms/GTDI
        'reserve':'*',
        'sfield_sep':':',
        'skip_char':'\r\n',
        'stripfield_sep':True,
        'triad':'',
        'version':'3',
        'UNB.S002.0007':'14',
        'UNB.S003.0007':'14',
        'UNB.0035':'0',
        }
    formatconvert = {
        'A':'A',
        'AN':'A',
        'N':'R',
        }

class x12(Grammar):
    defaultsyntax = {
        'add_crlfafterrecord_sep':'\r\n',
        'acceptspaceinnumfield':True,   #only really used in fixed formats
        'charset':'us-ascii',
        'checkcharsetin':'strict', #strict, ignore or botsreplace (replace with char as set in bots.ini).
        'checkcharsetout':'strict', #strict, ignore or botsreplace (replace with char as set in bots.ini).
        'checkcollision':True,
        'checkunknownentities': True,
        'contenttype':'application/X12',
        'decimaal':'.',
        'envelope':'x12',
        'escape':'',
        'field_sep':'*',
        'forcequote':'',    #(if quote_char is set) 0:no force: only quote if neccesary:1:always force: 2:??etcetc
        'functionalgroup'    :  'XX',
        'lengthnumericbare':True,
        'merge':True,
        'noBOTSID':False,
        'pass_all':False,
        'quote_char':'',
        'record_sep':"~",
        'record_tag_sep':"",    #Tradacoms/GTDI
        'replacechar':'',       #if separator found, replace by this character; if replacechar is an empty string: raie error
        'reserve':'^',
        'sfield_sep':'>',    #advised '\'?
        'skip_char':'\r\n',
        'stripfield_sep':True,
        'triad':'',
        'version':'00000',
        'ISA01':'00',
        'ISA02':'          ',
        'ISA03':'00',
        'ISA04':'          ',
        'ISA05':'01',
        'ISA07':'01',
        'ISA11':'U',
        'ISA14':'1',
        'ISA15':'P',
        'GS07':'X',
        }
    formatconvert = {
        'AN':'A',
        'DT':'D',
        'TM':'T',
        'N':'I',
        'N0':'I',
        'N1':'I',
        'N2':'I',
        'N3':'I',
        'N4':'I',
        'N5':'I',
        'N6':'I',
        'N7':'I',
        'N8':'I',
        'N9':'I',
        'R':'R',
        'B':'A',
        'ID':'A',
        }
    def _manipulatefieldformat(self,field,recordID):
        super(x12,self)._manipulatefieldformat(field,recordID)
        if field[BFORMAT]=='I':
            if field[FORMAT][1:]:
                field[DECIMALS] = int(field[FORMAT][1])
            else:
                field[DECIMALS] = 0

class json(Grammar):
    defaultsyntax = {
        'add_crlfafterrecord_sep':'',
        'acceptspaceinnumfield':True,   #only really used in fixed formats
        'charset':'utf-8',
        'checkcharsetin':'strict', #strict, ignore or botsreplace (replace with char as set in bots.ini).
        'checkcharsetout':'strict', #strict, ignore or botsreplace (replace with char as set in bots.ini).
        'checkcollision':False,
        'checkunknownentities': True,   #??changed later
        'contenttype':'text/xml ',
        'decimaal':'.',
        'defaultBOTSIDroot':'ROOT',
        'envelope':'',
        'escape':'',
        'field_sep':'',
        'forcequote':'',
        'indented':False,               #False:  output is one string (no cr/lf); True:  output is indented/human readable
        'lengthnumericbare':False,
        'merge':False,
        'noBOTSID':False,
        'pass_all':False,
        'quote_char':"",
        'record_sep':"",
        'record_tag_sep':"",    #Tradacoms/GTDI
        'reserve':'',
        'sfield_sep':'',
        'skip_char':'',
        'stripfield_sep':False,
        'triad':'',
        }
class jsonnocheck(json):
    _checkstructurerequired=False
    defaultsyntax = {
        'add_crlfafterrecord_sep':'',
        'acceptspaceinnumfield':True,   #only really used in fixed formats
        'charset':'utf-8',
        'checkcharsetin':'strict', #strict, ignore or botsreplace (replace with char as set in bots.ini).
        'checkcharsetout':'strict', #strict, ignore or botsreplace (replace with char as set in bots.ini).
        'checkcollision':False,
        'checkunknownentities': False,
        'contenttype':'text/xml ',
        'decimaal':'.',
        'defaultBOTSIDroot':'ROOT',
        'envelope':'',
        'escape':'',
        'field_sep':'',
        'forcequote':'',
        'indented':False,               #False:  output is one string (no cr/lf); True: output is indented/human readable
        'lengthnumericbare':False,
        'merge':False,
        'noBOTSID':False,
        'pass_all':False,
        'quote_char':"",
        'record_sep':"",
        'record_tag_sep':"",    #Tradacoms/GTDI
        'reserve':'',
        'sfield_sep':'',
        'skip_char':'',
        'stripfield_sep':False,
        'triad':'',
        }
class tradacoms(Grammar):
    defaultsyntax = {
        'add_crlfafterrecord_sep':'\n',
        'acceptspaceinnumfield':True,   #only really used in fixed formats
        'charset':'us-ascii',
        'checkcharsetin':'strict', #strict, ignore or botsreplace (replace with char as set in bots.ini).
        'checkcharsetout':'strict', #strict, ignore or botsreplace (replace with char as set in bots.ini).
        'checkcollision':True,
        'checkunknownentities': True,
        'contenttype':'application/text',
        'decimaal':'.',
        'envelope':'tradacoms',
        'escape':'?',
        'field_sep':'+',
        'forcequote':'',    #(if quote_char is set) 0:no force: only quote if neccesary:1:always force: 2:??etcetc
        'indented':False,               #False:  output is one string (no cr/lf); True:  output is indented/human readable
        'lengthnumericbare':True,
        'merge':False,
        'noBOTSID':False,
        'pass_all':False,
        'quote_char':'',
        'record_sep':"'",
        'record_tag_sep':"=",    #Tradacoms/GTDI
        'reserve':'',
        'sfield_sep':':',
        'skip_char':'\r\n',
        'stripfield_sep':True,
        'triad':'',
        'STX.STDS1':'ANA',
        'STX.STDS2':'1',
        'STX.FROM.02':'',
        'STX.UNTO.02':'',
        'STX.APRF':'',
        'STX.PRCD':'',
        }
    formatconvert = {
        'X':'A',
        '9':'R',
        '9V9':'I',
        }

class database(jsonnocheck):
    pass
