from django.utils.translation import ugettext as _
#bots-modules
import botslib
import node
from botsconfig import *


class Message(object):
    ''' abstract class; represents a edi message.
        is subclassed as outmessage or inmessage object.
    '''
    def __init__(self):
        self.recordnumber=0                #segment counter. Is not used for UNT of SE record; some editypes want sequential recordnumbering

    def kill(self):
        """ explicitly del big attributes....."""
        if hasattr(self,'ta_info'): del self.ta_info
        if hasattr(self,'root'): del self.root
        if hasattr(self,'defmessage'): del self.defmessage
        if hasattr(self,'records'): del self.records
        if hasattr(self,'rawinput'): del self.rawinput

    @staticmethod
    def display(records):
        '''for debugging lexed records.'''
        for record in records:
            t = 0
            for veld in record:
                if t==0:
                    print '%s    (Record-id)'%(veld[VALUE])
                else:
                    if veld[SFIELD]:
                        print '        %s    (sub)'%(veld[VALUE])
                    else:
                        print '    %s    (veld)'%(veld[VALUE])
                t += 1

    def change(self,where,change):
        ''' query tree (self.root) with where; if found replace with change; return True if change, return False if not changed.'''
        if self.root.record is None:
            raise botslib.MappingRootError(_(u'change($where,$change"): "root" of incoming message is empty; either split messages or use inn.getloop'),where=where,change=change)
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
        count = 0 
        for value in self.getloop(*mpaths):
            count += 1
        return count

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
                self.root.append(node.Node(mpaths[0]))
                return self.root.children[-1]
            else: #TODO: what if self.root.record is None and len(mpaths) > 1?
                raise botslib.MappingRootError(_(u'putloop($mpath): mpath too long???'),mpath=mpaths)
        return self.root.putloop(*mpaths)

    def sort(self,*mpaths):
        if self.root.record is None:
            raise botslib.MappingRootError(_(u'get($mpath): "root" of message is empty; either split messages or use inn.getloop'),mpath=mpaths)
        self.root.sort(*mpaths)
        
    def normalisetree(self,node):
        ''' The node tree is check, sorted, fields are formatted etc.
            Always use this method before writing output.
        '''
        self._checktree(node,self.defmessage.structure[0])
        #~ node.display()
        self._canonicaltree(node,self.defmessage.structure[0])
        
    def _checktree(self,tree,structure):
        ''' checks tree with table:
            -   all records should be in table at the right place in hierarchy
            -   for each record, all fields should be in grammar
            This function checks the root of grammar-structure with root of node tree
        '''
        if tree.record['BOTSID'] == structure[ID]:
            #check tree recursively with structure
            self._checktreecore(tree,structure)  
        else:
            raise botslib.MessageError(_(u'Grammar "$grammar" has (root)record "$grammarroot"; found "$root".'),root=tree.record['BOTSID'],grammarroot=structure[ID],grammar=self.defmessage.grammarname)
            
    def _checktreecore(self,node,structure):
        ''' recursive
        '''
        deletelist=[]
        self._checkfields(node.record,structure)
        if node.children and not LEVEL in structure:
            if self.ta_info['checkunknownentities']:
                raise botslib.MessageError(_(u'Record "$record" in message has children, but grammar "$grammar" not. Found "$xx".'),record=node.record['BOTSID'],grammar=self.defmessage.grammarname,xx=node.children[0].record['BOTSID'])
            node.children=[]
            return
        for childnode in node.children:          #for every node:
            for structure_record in structure[LEVEL]:           #search in grammar-records
                if childnode.record['BOTSID'] == structure_record[ID]:   #if found right structure_record
                    #check children recursive
                    self._checktreecore(childnode,structure_record)
                    break    #check next mpathnode
            else:   #checked all structure_record in grammar, but nothing found
                if self.ta_info['checkunknownentities']:
                    raise botslib.MessageError(_(u'Record "$record" in message not in structure of grammar "$grammar". Whole record: "$content".'),record=childnode.record['BOTSID'],grammar=self.defmessage.grammarname,content=childnode.record)
                deletelist.append(childnode)
        for child in deletelist:
            node.children.remove(child)
                

    def _checkfields(self,record,structure_record):
        ''' checks for every field in record if field exists in structure_record (from grammar).
        '''
        deletelist=[]
        for field in record.keys():          #all fields in record should exist in structure_record
            for grammarfield in structure_record[FIELDS]:
                if grammarfield[ISFIELD]:    #if field (no composite)
                    if field == grammarfield[ID]:
                        break
                else:   #if composite
                    for grammarsubfield in grammarfield[SUBFIELDS]:   #loop subfields
                        if field == grammarsubfield[ID]:
                            break
                    else:
                        continue
                    break
            else:
                if self.ta_info['checkunknownentities']:
                    raise botslib.MessageError(_(u'Record: "$mpath" field "$field" does not exist.'),field=field,mpath=structure_record[MPATH])
                deletelist.append(field)
        for field in deletelist:
            del record[field]
                
    def _canonicaltree(self,node,structure,headerrecordnumber=0):
        ''' For nodes: check min and max occurence; sort the records conform grammar
        '''
        sortednodelist = []
        self._canonicalfields(node.record,structure,headerrecordnumber)    #handle fields of this record
        if LEVEL in structure:
            for structure_record in structure[LEVEL]:  #for structure_record of this level in grammar
                count = 0                           #count number of occurences of record
                for childnode in node.children:            #for every node in mpathtree; SPEED: delete nodes from list when found
                    if childnode.record['BOTSID'] != structure_record[ID]:   #if it is not the right NODE":
                        continue
                    count += 1
                    self._canonicaltree(childnode,structure_record,self.recordnumber)         #use rest of index in deeper level
                    sortednodelist.append(childnode)
                if structure_record[MIN] > count:
                    raise botslib.MessageError(_(u'Record "$mpath" mandatory but not present.'),mpath=structure_record[MPATH])
                if structure_record[MAX] < count:
                    raise botslib.MessageError(_(u'Record "$mpath" occurs to often ($count times).'),mpath=structure_record[MPATH],count=count)
            node.children=sortednodelist
            if hasattr(self,'get_queries_from_edi'):
                self.get_queries_from_edi(node,structure)

    def _canonicalfields(self,noderecord,structure_record,headerrecordnumber):
        ''' For fields: check M/C; format the fields. Fields are not sorted (a dict can not be sorted).
            Fields are never added.
        '''
        for grammarfield in structure_record[FIELDS]:
            if grammarfield[ISFIELD]:    #if field (no composite)
                value = noderecord.get(grammarfield[ID])
                #~ print '(message)field',noderecord,grammarfield
                if not value:
                    #~ print 'field',grammarfield[ID], 'has no value'
                    if grammarfield[MANDATORY] == 'M':
                        raise botslib.MessageError(_(u'Record "$mpath" field "$field" is mandatory.'),mpath=structure_record[MPATH],field=grammarfield[ID])
                    continue
                #~ print 'field',grammarfield[ID], 'value', value
                noderecord[grammarfield[ID]] = self._formatfield(value,grammarfield,structure_record)
            else:               #if composite
                for grammarsubfield in grammarfield[SUBFIELDS]:   #loop subfields to see if data in composite
                    if noderecord.get(grammarsubfield[ID]):
                        break   #composite has data.
                else:           #composite has no data
                    if grammarfield[MANDATORY]=='M':
                        raise botslib.MessageError(_(u'Record "$mpath" composite "$field" is mandatory.'),mpath=structure_record[MPATH],field=grammarfield[ID])
                    continue
                #there is data in the composite!
                for grammarsubfield in grammarfield[SUBFIELDS]:   #loop subfields
                    value = noderecord.get(grammarsubfield[ID])
                    if not value:
                        if grammarsubfield[MANDATORY]=='M':
                            raise botslib.MessageError(_(u'Record "$mpath" subfield "$field" is mandatory: "$record".'),mpath=structure_record[MPATH],field=grammarsubfield[ID],record=noderecord)
                        continue
                    noderecord[grammarsubfield[ID]] = self._formatfield(value,grammarsubfield,structure_record)
