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
    def display(records):
        '''for debugging lexed records.'''
        for record in records:
            counter = 0
            for veld in record:
                if counter == 0:
                    print '%s    (Record-id)'%(veld[VALUE])
                else:
                    if veld[SFIELD]:
                        print '        %s    (sub)'%(veld[VALUE])
                    else:
                        print '    %s    (veld)'%(veld[VALUE])
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
            for structure_record in structure[LEVEL]:                   #search in grammar-records
                if childnode.record['BOTSID'] == structure_record[ID]:
                    #found record in grammar
                    #check recursive:
                    self._checkifrecordsingrammar(childnode,structure_record,grammarname)
                    break    #record/childnode is in gramar; go to check next record/childnode
            else:   #record/childnode in not in grammar
                if self.ta_info['checkunknownentities']:
                    self.add2errorlist(_(u'[S02]%(linpos)s: Unknown record "%(record)s" in message.\n')%
                                        {'linpos':node_instance.linpos(),'record':childnode.record['BOTSID']})
                deletelist.append(childnode)
        for child in deletelist:
            node_instance.children.remove(child)


    def _checkiffieldsingrammar(self,node_instance,structure_record):
        ''' checks for every field in record if field exists in structure_record (from grammar).
        '''
        deletelist = []
        for field in node_instance.record.keys():     #check every field in the record
            if field == 'BOTSIDnr':     #is not in grammar, so skip check
                continue
            for grammarfield in structure_record[FIELDS]:
                if grammarfield[ISFIELD]:    #if field (no composite)
                    if field == grammarfield[ID]:
                        break
                else:   #if composite
                    for grammarsubfield in grammarfield[SUBFIELDS]:   #loop subfields
                        if field == grammarsubfield[ID]:
                            break   #break out of grammarsubfield-for-loop ->goto break out of grammarfield-for-loop
                    else:
                        continue    #nothing found; continue with next gammarfield
                    break   #break out of grammarfield-for-loop
            else:
                if self.ta_info['checkunknownentities']:
                    self.add2errorlist(_(u'[F01]%(linpos)s: Record: "%(mpath)s" has unknown field "%(field)s".\n')%
                                            {'linpos':node_instance.linpos(),'field':field,'mpath':self.mpathformat(structure_record[MPATH])})
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
            for structure_record in structure[LEVEL]:  #for every structure_record (in grammar) of this level
                count = 0                           #count number of occurences of record
                for childnode in node_instance.children:            #for every node in mpathtree; SPEED: delete nodes from list when found
                    if childnode.record['BOTSID'] != structure_record[ID] or childnode.record['BOTSIDnr'] != structure_record[BOTSIDNR]:   #if it is not the right NODE":
                        continue
                    count += 1
                    self._canonicaltree(childnode,structure_record,self.recordnumber)         #use rest of index in deeper level
                    sortednodelist.append(childnode)
                if structure_record[MIN] > count:
                    self.add2errorlist(_(u'[S03]%(linpos)s: Record "%(mpath)s" occurs %(count)d times, min is %(mincount)d.\n')%
                                        {'linpos':node_instance.linpos(),'mpath':self.mpathformat(structure_record[MPATH]),'count':count,'mincount':structure_record[MIN]})
                if structure_record[MAX] < count:
                    self.add2errorlist(_(u'[S04]%(linpos)s: Record "%(mpath)s" occurs %(count)d times, max is %(maxcount)d.\n')%
                                        {'linpos':node_instance.linpos(),'mpath':self.mpathformat(structure_record[MPATH]),'count':count,'maxcount':structure_record[MAX]})
            node_instance.children = sortednodelist
        #only relevant for inmessages
        if QUERIES in structure:
            node_instance.get_queries_from_edi(structure)

    def _canonicalfields(self,node_instance,structure_record,headerrecordnumber):
        ''' For fields: check M/C; format the fields. Fields are not sorted (a dict can not be sorted).
            Fields are never added.
        '''
        noderecord = node_instance.record
        for grammarfield in structure_record[FIELDS]:       #loop over fields in grammar
            if grammarfield[ISFIELD]:    #if field (no composite)
                value = noderecord.get(grammarfield[ID])
                if not value:
                    if grammarfield[MANDATORY]:
                        self.add2errorlist(_(u'[F02]%(linpos)s: Record "%(mpath)s" field "%(field)s" is mandatory.\n')%
                                            {'linpos':node_instance.linpos(),'mpath':self.mpathformat(structure_record[MPATH]),'field':grammarfield[ID]})
                    continue
                noderecord[grammarfield[ID]] = self._formatfield(value,grammarfield,structure_record,node_instance)
            else:               #if composite: loop over subfields in grammar
                #first check if there is any data att all in this composite
                for grammarsubfield in grammarfield[SUBFIELDS]:
                    if noderecord.get(grammarsubfield[ID]):
                        break   #composite has data.
                else:           #if composite has no data
                    if grammarfield[MANDATORY]:
                        self.add2errorlist(_(u'[F03]%(linpos)s: Record "%(mpath)s" composite "%(field)s" is mandatory.\n')%
                                            {'linpos':node_instance.linpos(),'mpath':self.mpathformat(structure_record[MPATH]),'field':grammarfield[ID]})
                    continue    #there is no data in compisite, and composite is conditional: composite is OK
                #there is data in the composite!
                for grammarsubfield in grammarfield[SUBFIELDS]:   #loop subfields
                    value = noderecord.get(grammarsubfield[ID])
                    if not value:
                        if grammarsubfield[MANDATORY]:
                            self.add2errorlist(_(u'[F04]%(linpos)s: Record "%(mpath)s" subfield "%(field)s" is mandatory.\n')%
                                                {'linpos':node_instance.linpos(),'mpath':self.mpathformat(structure_record[MPATH]),'field':grammarsubfield[ID]})
                        continue
                    noderecord[grammarsubfield[ID]] = self._formatfield(value,grammarsubfield,structure_record,node_instance)

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
