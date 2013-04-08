from django.utils.translation import ugettext as _
#bots-modules
import botslib
import node
import botsglobal
from botsconfig import *


class Message(object):
    ''' abstract class; represents a edi message.
        is subclassed as outmessage or inmessage object.
    '''
    def __init__(self):
        self.recordnumber = 0                #segment counter. Is not used for UNT of SE record; some editypes want sequential recordnumbering
        self.errorlist = []                #to gather all (non-fatal) errors in the edi file.
        self.messagetypetxt = ''
        self.messagecount = 0

    def add2errorlist(self,errortxt):
        self.errorlist.append(self.messagetypetxt + errortxt)
        if len(self.errorlist) >= botsglobal.ini.getint('settings','max_number_errors',10) :
            raise botslib.MessageError(_(u'At least $max_number_errors errors:\n$errorlist'),max_number_errors=len(self.errorlist), errorlist=''.join(self.errorlist))

    @staticmethod
    def display(lex_records):
        '''for debugging lexed records.'''
        for lex_record in lex_records:
            counter = 0
            for veld in lex_record:
                if counter == 0:
                    print '%s    (Record-id)'%(veld[VALUE])
                else:
                    if veld[SFIELD] == 0:
                        print '    %s    (veld)'%(veld[VALUE])
                    elif veld[SFIELD] == 1:
                        print '        %s    (sub)'%(veld[VALUE])
                    elif veld[SFIELD] == 2:
                        print '        %s    (rep)'%(veld[VALUE])
                    else:
                        print '    %s    (???)'%(veld[VALUE])
                counter += 1

    @staticmethod
    def mpathformat(mpath):
        ''' mpath is like: [['UNH'], ['NAD']]
        '''
        return '-'.join([record[0] for record in mpath])
        
    def checkmessage(self,node_instance,grammar,subtranslation=False):
        ''' The node tree is check, sorted, fields are formatted etc.
            For checking: translation & subtranslation
            parameter subtranslation only used for reporting
        '''
        #checks the root of grammar-structure with root of node tree:
        #check message against grammar (so far only minimal tests have been done during processing)
        #some different cases:
        #- empy root.record, root.children filled:
        #  - edifact, x12, tradacoms: each child is an envelope. Check each envelope. (use mailbag to have one UNB per node-tree here)
        #  - csv nobotsid: each child is a record. Check all records in one check
        #  - xml, json:
        # root.record filled, root.children filled: outgoing messages.
        #~ self.root.display() #show tree of nodes (for protocol debugging)
        if node_instance.record:        #root record contains information; write whole tree in one time
            self._checkonemessage(node_instance,grammar,subtranslation)
        else:
            for childnode in node_instance.children:
                self._checkonemessage(childnode,grammar,subtranslation)

        if self.errorlist and not subtranslation:
            raise botslib.MessageError(_(u'$errorlist'),errorlist=''.join(self.errorlist))

    def _checkonemessage(self,node_instance,grammar,subtranslation):
        structure = grammar.structure
        if node_instance.record['BOTSID'] != structure[0][ID]:
            raise botslib.MessageError(_(u'[G50]: Grammar "$grammar" starts with record "$grammarroot"; but while reading edi-file found start-record "$root".'),root=node_instance.record['BOTSID'],grammarroot=structure[0][ID],grammar=grammar.grammarname)
        self._checkifrecordsingrammar(node_instance,structure[0],grammar.grammarname)
        self._canonicaltree(node_instance,structure[0])
        if not subtranslation and botsglobal.ini.getboolean('settings','readrecorddebug',False):       #should the content of the message (the records read) be logged.
            self._logmessagecontent(node_instance)

    def _checkifrecordsingrammar(self,node_instance,structure,grammarname):
        ''' check for every node if in grammar
            recursive
        '''
        deletelist = []       #list of records not in the grammar; these records are deleted at end of function
        self._checkiffieldsingrammar(node_instance,structure)     #check if fields are known in grammar
        if 'messagetype' in node_instance.queries:   #determine if SUBTRANSLATION starts; do not check (is already checked)
            return
        if node_instance.children and LEVEL not in structure:            #if record has children, but these are not in the grammar
            if self.ta_info['checkunknownentities']:
                self.add2errorlist(_(u'[S01]%(linpos)s: Record "%(record)s" in message has children, but these are not in grammar "%(grammar)s". Found record "%(xx)s".\n')%
                                    {'linpos':node_instance.linpos(),'record':node_instance.record['BOTSID'],'grammar':grammarname,'xx':node_instance.children[0].record['BOTSID']})
            node_instance.children = []
            return
        for childnode in node_instance.children:          #for every record/childnode:
            for record_definition in structure[LEVEL]:                   #search in grammar-records
                if childnode.record['BOTSID'] == record_definition[ID]:
                    #found record in grammar
                    #check recursive:
                    self._checkifrecordsingrammar(childnode,record_definition,grammarname)
                    break    #record/childnode is in gramar; go to check next record/childnode
            else:   #record/childnode in not in grammar
                if self.ta_info['checkunknownentities']:
                    self.add2errorlist(_(u'[S02]%(linpos)s: Unknown record "%(record)s" in message.\n')%
                                        {'linpos':node_instance.linpos(),'record':childnode.record['BOTSID']})
                deletelist.append(childnode)
        for child in deletelist:
            node_instance.children.remove(child)


    def _checkiffieldsingrammar(self,node_instance,record_definition):
        ''' checks for every field in record if field exists in record_definition (from grammar).
            for inmessage of type (var,fixed,??) this is not needed 
        '''
        deletelist = []
        for field in node_instance.record.keys():     #check every field in the record
            if field == 'BOTSIDnr':     #BOTSIDnr is not in grammar, so skip check
                continue
            for field_definition in record_definition[FIELDS]:
                if field_definition[ISFIELD]:    #if field (no composite)
                    if field == field_definition[ID]:
                        break
                else:   #if composite
                    if field_definition[MAXREPEAT] == 1:    #if composite is non-repeating
                        for grammarsubfield in field_definition[SUBFIELDS]:   #loop subfields
                            if field == grammarsubfield[ID]:
                                break   #break out of grammarsubfield-for-loop ->goto break out of field_definition-for-loop
                        else:
                            continue    #nothing found; continue with next gammarfield
                        break   #break out of field_definition-for-loop
                    else: #composite is repeating
                        if field != field_definition[ID]:   #first check compositeID
                            continue
                        break
                        #TODO
                        #check for all fields in reperating composite the content
                        #~ for content_dict in node_instance.record[field]:    #content is a list of dicts
                            #~ for field2 in content_dict.keys():              #for every field in this dict
                                #~ for grammarsubfield in field_definition[SUBFIELDS]:   #loop subfields to search field
                                    #~ if field == grammarsubfield[ID]:
                                        #~ break
                                #~ else:
            else:           #not found in grammar
                if self.ta_info['checkunknownentities']:
                    self.add2errorlist(_(u'[F01]%(linpos)s: Record: "%(mpath)s" has unknown field "%(field)s".\n')%
                                            {'linpos':node_instance.linpos(),'field':field,'mpath':self.mpathformat(record_definition[MPATH])})
                deletelist.append(field)
        for field in deletelist:
            del node_instance.record[field]

    def _canonicaltree(self,node_instance,structure,headerrecordnumber=0):
        ''' For nodes: check min and max occurence; sort the records conform grammar
            parameter 'headerrecordnumber' is used in subclassing this function.
        '''
        sortednodelist = []
        self._canonicalfields(node_instance,structure,headerrecordnumber)    #handle fields of this record
        if LEVEL in structure:
            for record_definition in structure[LEVEL]:  #for every record_definition (in grammar) of this level
                count = 0                           #count number of occurences of record
                for childnode in node_instance.children:            #for every node in mpathtree; SPEED: delete nodes from list when found
                    if childnode.record['BOTSID'] != record_definition[ID] or childnode.record['BOTSIDnr'] != record_definition[BOTSIDNR]:   #if it is not the right NODE":
                        continue
                    count += 1
                    self._canonicaltree(childnode,record_definition,self.recordnumber)         #use rest of index in deeper level
                    sortednodelist.append(childnode)
                if record_definition[MIN] > count:
                    self.add2errorlist(_(u'[S03]%(linpos)s: Record "%(mpath)s" occurs %(count)d times, min is %(mincount)d.\n')%
                                        {'linpos':node_instance.linpos(),'mpath':self.mpathformat(record_definition[MPATH]),'count':count,'mincount':record_definition[MIN]})
                if record_definition[MAX] < count:
                    self.add2errorlist(_(u'[S04]%(linpos)s: Record "%(mpath)s" occurs %(count)d times, max is %(maxcount)d.\n')%
                                        {'linpos':node_instance.linpos(),'mpath':self.mpathformat(record_definition[MPATH]),'count':count,'maxcount':record_definition[MAX]})
            node_instance.children = sortednodelist
        #only relevant for inmessages
        if QUERIES in structure:
            node_instance.get_queries_from_edi(structure)

    def _canonicalfields(self,node_instance,record_definition,headerrecordnumber):
        ''' For fields: check M/C; format the fields. Fields are not sorted (a dict can not be sorted).
            Fields are never added.
        '''
        noderecord = node_instance.record
        for field_definition in record_definition[FIELDS]:       #loop over fields in grammar
            if field_definition[ISFIELD]:    #if field (no composite)
                if field_definition[MAXREPEAT] == 1:    #if non-repeating
                    value = noderecord.get(field_definition[ID])
                    if not value:
                        if field_definition[MANDATORY]:
                            self.add2errorlist(_(u'[F02]%(linpos)s: Record "%(mpath)s" field "%(field)s" is mandatory.\n')%
                                                {'linpos':node_instance.linpos(),'mpath':self.mpathformat(record_definition[MPATH]),'field':field_definition[ID]})
                        continue
                    noderecord[field_definition[ID]] = self._formatfield(value,field_definition,record_definition,node_instance)
                else: #repeating field; a list of values; if repeating element was empty the value is ''
                    valuelist = noderecord.get(field_definition[ID])
                    if not valuelist:
                        if field_definition[MANDATORY]:
                            self.add2errorlist(_(u'[F02]%(linpos)s: Record "%(mpath)s" field "%(field)s" is mandatory.\n')%
                                                {'linpos':node_instance.linpos(),'mpath':self.mpathformat(record_definition[MPATH]),'field':field_definition[ID]})
                        continue
                    if not isinstance(valuelist,list):
                        self.add2errorlist(_(u'[FXX]%(linpos)s: Record "%(mpath)s" field "%(field)s" should be a list.\n')%
                                            {'linpos':node_instance.linpos(),'mpath':self.mpathformat(record_definition[MPATH]),'field':field_definition[ID]})
                        continue
                    if len(valuelist) > field_definition[MAXREPEAT]:
                        self.add2errorlist(_(u'[FXX]%(linpos)s: Record "%(mpath)s" repeating composite "%(field)s" occurs %(occurs)s times, max is %(max)s.\n')%
                                            {'linpos':node_instance.linpos(),'mpath':self.mpathformat(record_definition[MPATH]),'field':field_definition[ID],
                                             'occurs':len(valuelist),'max':field_definition[MAXREPEAT]})
                    newlist = []
                    for value in valuelist:
                        newlist.append(self._formatfield(value,field_definition,record_definition,node_instance))
                    noderecord[field_definition[ID]] = newlist
            else:               #if composite: loop over subfields in grammar
                if field_definition[MAXREPEAT] == 1:    #if non-repeating compostie
                    #first check if there is any data att all in this composite
                    for grammarsubfield in field_definition[SUBFIELDS]:
                        if noderecord.get(grammarsubfield[ID]):
                            break   #composite has data.
                    else:           #if composite has no data
                        if field_definition[MANDATORY]:
                            self.add2errorlist(_(u'[F03]%(linpos)s: Record "%(mpath)s" composite "%(field)s" is mandatory.\n')%
                                                {'linpos':node_instance.linpos(),'mpath':self.mpathformat(record_definition[MPATH]),'field':field_definition[ID]})
                        continue    #there is no data in compisite, and composite is conditional: composite is OK
                    #there is data in the composite!
                    for grammarsubfield in field_definition[SUBFIELDS]:   #loop subfields
                        value = noderecord.get(grammarsubfield[ID])
                        if not value:
                            if grammarsubfield[MANDATORY]:
                                self.add2errorlist(_(u'[F04]%(linpos)s: Record "%(mpath)s" subfield "%(field)s" is mandatory.\n')%
                                                    {'linpos':node_instance.linpos(),'mpath':self.mpathformat(record_definition[MPATH]),'field':grammarsubfield[ID]})
                            continue
                        noderecord[grammarsubfield[ID]] = self._formatfield(value,grammarsubfield,record_definition,node_instance)
                else:   #if repeating composite
                    #first check if there is any data at all in this composite
                    valuelist = noderecord.get(field_definition[ID])
                    if not valuelist:
                        if field_definition[MANDATORY]:
                            self.add2errorlist(_(u'[F02]%(linpos)s: Record "%(mpath)s" repeating composite "%(field)s" is mandatory.\n')%
                                                {'linpos':node_instance.linpos(),'mpath':self.mpathformat(record_definition[MPATH]),'field':field_definition[ID]})
                        continue
                    if not isinstance(valuelist,list):
                        self.add2errorlist(_(u'[FXX]%(linpos)s: Record "%(mpath)s" field "%(field)s" should be a list.\n')%
                                            {'linpos':node_instance.linpos(),'mpath':self.mpathformat(record_definition[MPATH]),'field':field_definition[ID]})
                        continue
                    if len(valuelist) > field_definition[MAXREPEAT]:
                        self.add2errorlist(_(u'[FXX]%(linpos)s: Record "%(mpath)s" repeating composite "%(field)s" occurs %(occurs)s times, max is %(max)s.\n')%
                                            {'linpos':node_instance.linpos(),'mpath':self.mpathformat(record_definition[MPATH]),'field':field_definition[ID],
                                             'occurs':len(valuelist),'max':field_definition[MAXREPEAT]})
                    #is a list of composites; each composite is a dict.
                    #loop over composites.
                    #first check if there is data in the composite
                    #if so, check M/C
                    for comp in valuelist:
                        for grammarsubfield in field_definition[SUBFIELDS]:
                            if comp.get(grammarsubfield[ID]):
                                break   #composite has data.
                        else:           #if composite has no data
                            if field_definition[MANDATORY]:
                                self.add2errorlist(_(u'[FXX]%(linpos)s: Record "%(mpath)s" composite "%(field)s" is mandatory.\n')%
                                                    {'linpos':node_instance.linpos(),'mpath':self.mpathformat(record_definition[MPATH]),'field':field_definition[ID]})
                            continue    #there is no data in compisite, and composite is conditional: composite is OK
                        #there is data in the composite!
                        for grammarsubfield in field_definition[SUBFIELDS]:   #loop subfields
                            value = comp.get(grammarsubfield[ID])
                            if not value:
                                if grammarsubfield[MANDATORY]:
                                    self.add2errorlist(_(u'[F04]%(linpos)s: Record "%(mpath)s" subfield "%(field)s" is mandatory.\n')%
                                                        {'linpos':node_instance.linpos(),'mpath':self.mpathformat(record_definition[MPATH]),'field':grammarsubfield[ID]})
                                continue
                            comp[grammarsubfield[ID]] = self._formatfield(value,grammarsubfield,record_definition,node_instance)


    def _logmessagecontent(self,node_instance):
        botsglobal.logger.debug(u'record "%s":',node_instance.record['BOTSID'])
        self._logfieldcontent(node_instance.record)    #handle fields of this record
        for child in node_instance.children:
            self._logmessagecontent(child)

    @staticmethod
    def _logfieldcontent(noderecord):
        for key,value in noderecord.items():
            if key not in ['BOTSID','BOTSIDnr']:
                botsglobal.logger.debug(u'    "%s" : "%s"',key,value)

    #***************************************************************************
    #* methods below pass call to node.Node ************************************
    #***************************************************************************
    def getrecord(self,*mpaths):
        if self.root.record is None:
            raise botslib.MappingRootError(_(u'getrecord($mpath): "root" of incoming message is empty; either split messages or use inn.getloop'),mpath=mpaths)
        return self.root.getrecord(*mpaths)

    def change(self,where,change):
        ''' query tree (self.root) with where; if found replace with change; return True if change, return False if not changed.'''
        if self.root.record is None:
            raise botslib.MappingRootError(_(u'change($where,$change): "root" of incoming message is empty; either split messages or use inn.getloop'),where=where,change=change)
        return self.root.change(where,change)

    def delete(self,*mpaths):
        ''' query tree (self.root) with mpath; delete if found. return True if deleted, return False if not deleted.'''
        if self.root.record is None:
            raise botslib.MappingRootError(_(u'delete($mpath): "root" of incoming message is empty; either split messages or use inn.getloop'),mpath=mpaths)
        return self.root.delete(*mpaths)

    def get(self,*mpaths):
        ''' query tree (self.root) with mpath; get value (string); get None if not found.'''
        if self.root.record is None:
            raise botslib.MappingRootError(_(u'get($mpath): "root" of incoming message is empty; either split messages or use inn.getloop'),mpath=mpaths)
        return self.root.get(*mpaths)

    def getnozero(self,*mpaths):
        ''' like get, returns None is value is zero (0) or not numeric.
            Is sometimes usefull in mapping.'''
        if self.root.record is None:
            raise botslib.MappingRootError(_(u'get($mpath): "root" of incoming message is empty; either split messages or use inn.getloop'),mpath=mpaths)
        return self.root.getnozero(*mpaths)

    def getcount(self):
        ''' count number of nodes in self.root. Number of nodes is number of records.'''
        return self.root.getcount()

    def getcountoccurrences(self,*mpaths):
        ''' count number of nodes in self.root. Number of nodes is number of records.'''
        return len(list(self.getloop(*mpaths)))

    def getcountsum(self,*mpaths):
        ''' return the sum for all values found in mpath. Eg total number of ordered quantities.'''
        if self.root.record is None:
            raise botslib.MappingRootError(_(u'get($mpath): "root" of incoming message is empty; either split messages or use inn.getloop'),mpath=mpaths)
        return self.root.getcountsum(*mpaths)

    def getloop(self,*mpaths):
        ''' query tree with mpath; generates all the nodes. Is typically used as: for record in inn.get(mpath):
        '''
        if self.root.record:    #self.root is a real root
            for terug in self.root.getloop(*mpaths): #search recursive for rest of mpaths
                yield terug
        else:   #self.root is dummy root
            for childnode in self.root.children:
                for terug in childnode.getloop(*mpaths): #search recursive for rest of mpaths
                    yield terug

    def put(self,*mpaths,**kwargs):
        if self.root.record is None and self.root.children:
            raise botslib.MappingRootError(_(u'put($mpath): "root" of outgoing message is empty; use out.putloop'),mpath=mpaths)
        return self.root.put(*mpaths,**kwargs)

    def putloop(self,*mpaths):
        if not self.root.record:    #no input yet, and start with a putloop(): dummy root
            if len(mpaths) == 1:
                self.root.append(node.Node(record=mpaths[0]))
                return self.root.children[-1]
            else:
                raise botslib.MappingRootError(_(u'putloop($mpath): mpath too long???'),mpath=mpaths)
        return self.root.putloop(*mpaths)

    def sort(self,*mpaths):
        if self.root.record is None:
            raise botslib.MappingRootError(_(u'get($mpath): "root" of message is empty; either split messages or use inn.getloop'),mpath=mpaths)
        self.root.sort(*mpaths)
