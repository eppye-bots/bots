try:
    import cdecimal as decimal
except ImportError:
    import decimal
from django.utils.translation import ugettext as _
import botslib
import botsglobal
from botsconfig import *


class Node(object):
    ''' Node class for building trees in inmessage and outmessage
    '''
    #slots: python optimalisation to preserve memory. Disadv.: no dynamic attr in this class
    #in tests: for normal translations less memory and faster; no effect fo one-on-one translations.
    __slots__ = ('record','children','_queries','linposarg')    
    def __init__(self,record=None,linpos=None):
        if record:
            if 'BOTSIDnr' not in record:
                record['BOTSIDnr'] = u'1'
        self.record = record    #record is a dict with fields
        self.children = []
        self.linposarg = linpos
        self._queries = None

    def linpos(self):
        if self.linposarg:
            return ' line %(lin)s pos %(pos)s'%{'lin':self.linposarg[0],'pos':self.linposarg[1]}
        else:
            return ''

    def append(self,childnode):
        '''append child to node'''
        self.children.append(childnode)

    def display(self,level=0):
        '''for debugging
            usage eg in mappingscript:     inn.root.display()
        '''
        if level == 0:
            print 'displaying all nodes in node tree:'
        print '    '*level,self.record
        for childnode in self.children:
            childnode.display(level+1)

    #********************************************************
    #*** queries ********************************************
    #********************************************************
    def _getquerie(self):
        ''' getter for queries: get queries of a node '''
        if self._queries:
            return self._queries
        else:
            return {}

    def _updatequerie(self,updatequeries):
        ''' setter for queries: set/update queries of a node with dict queries.
        '''
        if updatequeries:
            if self._queries is None:
                self._queries = updatequeries.copy()
            else:
                botslib.updateunlessset(self._queries,updatequeries)

    queries = property(_getquerie,_updatequerie)

    def processqueries(self,queries,maxlevel):
        ''' copies values for queries 'down the tree' untill right level.
            So when edi file is split up in messages,
            querie-info from higher levels is copied to message.'''
        self.queries = queries
        if self.record and not maxlevel:
            return
        for childnode in self.children:
            childnode.processqueries(self.queries,maxlevel-1)

    def displayqueries(self,level=0):
        '''for debugging
            usage: in mappingscript:     inn.root.displayqueries()
        '''
        if level == 0:
            print 'displaying queries for nodes in tree'
        print '    '*level,'node:',
        if self.record:
            print self.record['BOTSID'],
        else:
            print 'None',
        print '',
        print self.queries
        for childnode in self.children:
            childnode.displayqueries(level+1)

    def enhancedget(self,mpaths):
        ''' to get QUERIES or SUBTRANSLATION;
            mpath can be
            - dict:     do get(mpath); can not be a mpath with multiple
            - tuple:    do get(mpath); can be multiple dicts in mapth
            - list:     for each listmembr do a get(); append the results
        '''
        if isinstance(mpaths,dict):
            return self.get(mpaths)
        elif isinstance(mpaths,tuple):
            return self.get(*mpaths)
        elif isinstance(mpaths,list):
            collect = u''
            for mpath in mpaths:
                if isinstance(mpath,dict):
                    found = self.get(mpath)
                elif isinstance(mpath,tuple):
                    found = self.get(*mpath)
                else:
                    raise botslib.MappingFormatError(_(u'Member in list %(mpath)s must be dict or tuple (in enhancedget).'),{'mpath':mpaths})
                if found:
                    collect += found
            return collect
        elif callable(mpaths):
            return mpaths()
        else:
            raise botslib.MappingFormatError(_(u'Must be dict, list or tuple: enhancedget(%(mpath)s)'),{'mpath':mpaths})

    def get_queries_from_edi(self,record_definition):
        ''' extract information from edifile using QUERIES in grammar.structure; information will be placed in ta_info and in db-ta
        '''
        tmpdict = {}
        #~ print 'get_queries_from_edi', record_definition[QUERIES]
        for key,value in record_definition[QUERIES].iteritems():
            found = self.enhancedget(value)   #search in last added node
            if found is not None:
                found = found.strip()         #needed to get correct ISA-fields 
                if found:
                    tmpdict[key] = found
        self.queries = tmpdict
        #~ print 'result:',self.queries,'\n'

    #********************************************************
    #*** manipulate node.tree: get, put, change, delete etc *
    #********************************************************
    def getrecord(self,*mpaths):
        ''' get whole node record
        '''
        #sanity check of mpaths
        if not mpaths or not isinstance(mpaths,tuple):
            raise botslib.MappingFormatError(_(u'Parameter "where" must be tuple: getrecord(%(mpath)s)'),{'mpath':mpaths})
        for part in mpaths:
            if not isinstance(part,dict):
                raise botslib.MappingFormatError(_(u'Parameter "mpaths" must be dicts in a tuple: getrecord(%(mpath)s)'),{'mpath':mpaths})
            if 'BOTSID' not in part:
                raise botslib.MappingFormatError(_(u'Section without "BOTSID": getrecord(%(mpath)s)'),{'mpath':mpaths})
            for key,value in part.iteritems():
                if not isinstance(key,basestring):
                    raise botslib.MappingFormatError(_(u'Keys must be strings: getrecord(%(mpath)s)'),{'mpath':mpaths})
                if not isinstance(value,basestring):
                    raise botslib.MappingFormatError(_(u'Values must be strings: getrecord(%(mpath)s)'),{'mpath':mpaths})
            if 'BOTSIDnr' not in part:
                part['BOTSIDnr'] = u'1'
        #go get it!
        terug =  self._getrecordcore(*mpaths)
        botsglobal.logmap.debug(u'"%(terug)s" for getrecord%(mpaths)s',{'terug':str(terug),'mpaths':str(mpaths)})
        return terug

    def _getrecordcore(self,*mpaths):
        for key,value in mpaths[0].iteritems():       #check all key, value for first part of where;
            if key not in self.record or value != self.record[key]:
                return None    #no match:
        else:   #all key,value are matched.
            if len(mpaths) == 1:    #mpath is exhausted; so we are there!!! #replace values with values in 'change'; delete if None
                return self.record
            else:           #go recursive
                for childnode in self.children:
                    terug = childnode._getrecordcore(*mpaths[1:])
                    if terug:
                        return terug
                else:   #no child has given a valid return
                    return None


    def change(self,where,change):
        ''' where is used to find a node;
            change is than applied to this node
            use first matching node for 'where'.
        '''
        #sanity check of mpaths
        if not where or not isinstance(where,tuple):
            raise botslib.MappingFormatError(_(u'Parameter "where" must be tuple: change(where=%(where)s,change=%(change)s)'),
                                                {'where':where,'change':change})
        for part in where:
            if not isinstance(part,dict):
                raise botslib.MappingFormatError(_(u'Parameter "where" must be dicts in a tuple: change(where=%(where)s,change=%(change)s)'),
                                                    {'where':where,'change':change})
            if 'BOTSID' not in part:
                raise botslib.MappingFormatError(_(u'Section without "BOTSID": change(where=%(where)s,change=%(change)s)'),
                                                    {'where':where,'change':change})
            for key,value in part.iteritems():
                if not isinstance(key,basestring):
                    raise botslib.MappingFormatError(_(u'Keys must be strings: change(where=%(where)s,change=%(change)s)'),
                                                        {'where':where,'change':change})
                if not isinstance(value,basestring):
                    raise botslib.MappingFormatError(_(u'Values must be strings: change(where=%(where)s,change=%(change)s)'),
                                                        {'where':where,'change':change})
            if 'BOTSIDnr' not in part:
                part['BOTSIDnr'] = u'1'
        #sanity check 'change' parameter
        if not change or not isinstance(change,dict):
            raise botslib.MappingFormatError(_(u'Parameter "change" must be dict: change(where=%(where)s,change=%(change)s)'),
                                                {'where':where,'change':change})
        change.pop('BOTSID','nep')  #remove 'BOTSID' from change. BOTSID can not be changed
        change.pop('BOTSIDnr','nep')  #remove 'BOTSIDnr' from change. BOTSIDnr can not be changed
        for key,value in change.iteritems():
            if not isinstance(key,basestring):
                raise botslib.MappingFormatError(_(u'Keys in "change" must be strings: change(where=%(where)s,change=%(change)s)'),
                                                    {'where':where,'change':change})
            if not isinstance(value,basestring) and value is not None:     #if None, item is deleted
                raise botslib.MappingFormatError(_(u'Values in "change" must be strings or "None": change(where=%(where)s,change=%(change)s)'),
                                                    {'where':where,'change':change})
        #go get it!
        terug =  self._changecore(where,change)
        botsglobal.logmap.debug(u'"%(terug)s" for change(where=%(where)s,change=%(change)s)',{'terug':terug,'where':str(where),'change':str(change)})
        return terug

    def _changecore(self,where,change):
        for key,value in where[0].iteritems():       #check all key, value for first part of where;
            if key not in self.record or value != self.record[key]:
                return False    #no match:
        else:   #all key,value are matched.
            if len(where) == 1:    #mpath is exhausted; so we are there!!! #replace values with values in 'change'; delete if None
                for key,value in change.iteritems():
                    if value is None:
                        self.record.pop(key,'nep')
                    else:
                        self.record[key] = value
                return True
            else:           #go recursive
                for childnode in self.children:
                    if childnode._changecore(where[1:],change):
                        return True
                else:   #no child has given a valid return
                    return False


    def delete(self,*mpaths):
        ''' delete the last record of mpath if found (first: find/identify, than delete.        '''
        #sanity check of mpaths
        if not mpaths or not isinstance(mpaths,tuple):
            raise botslib.MappingFormatError(_(u'Must be dicts in tuple: delete(%(mpath)s)'),{'mpath':mpaths})
        if len(mpaths) ==1:
            raise botslib.MappingFormatError(_(u'Only one dict: not allowed. Use different solution: delete(%(mpath)s)'),{'mpath':mpaths})
        for part in mpaths:
            if not isinstance(part,dict):
                raise botslib.MappingFormatError(_(u'Must be dicts in tuple: delete(%(mpath)s)'),{'mpath':mpaths})
            if 'BOTSID' not in part:
                raise botslib.MappingFormatError(_(u'Section without "BOTSID": delete(%(mpath)s)'),{'mpath':mpaths})
            for key,value in part.iteritems():
                if not isinstance(key,basestring):
                    raise botslib.MappingFormatError(_(u'Keys must be strings: delete(%(mpath)s)'),{'mpath':mpaths})
                if not isinstance(value,basestring):
                    raise botslib.MappingFormatError(_(u'Values must be strings: delete(%(mpath)s)'),{'mpath':mpaths})
            if 'BOTSIDnr' not in part:
                part['BOTSIDnr'] = u'1'
        #go get it!
        terug =  bool(self._deletecore(*mpaths))
        botsglobal.logmap.debug(u'"%(terug)s" for delete%(mpaths)s',{'terug':terug,'mpaths':str(mpaths)})
        return terug  #return False if not removed, return True if removed

    def _deletecore(self,*mpaths):
        for key,value in mpaths[0].iteritems():          #check all items in first part of mpaths
            if key not in self.record or value != self.record[key]:
                return 0
        else:   #all items are matched
            if len(mpaths) == 1:    #mpath is exhausted; so we are there!!!
                return 2  #indicates node should be removed
            else:
                for i, childnode in enumerate(self.children):
                    terug =  childnode._deletecore(*mpaths[1:]) #search recursive for rest of mpaths
                    if terug == 2:  #indicates node should be removed
                        del self.children[i]    #remove node
                        return 1    #this indicates: deleted successfull, do not remove anymore (no removal of parents)
                    if terug:
                        return terug
                else:   #no child has given a valid return
                    return 0

    def get(self,*mpaths):
        ''' get value of a field in a record from a edi-message
            mpath is xpath-alike query to identify the record/field
            function returns 1 value; return None if nothing found.
            if more than one value can be found: first one is returned
            starts searching in current node, then deeper
        '''
        checklevel_mappingscript = getattr(botsglobal,'checklevel_mappingscript',1)
        if checklevel_mappingscript:
            #sanity check of mpaths. None only allowed in last section of Mpath; first checks all parts except last one
            if not mpaths or not isinstance(mpaths,tuple):
                raise botslib.MappingFormatError(_(u'Must be dicts in tuple: get(%(mpath)s)'),{'mpath':mpaths})
            for part in mpaths[:-1]:
                if not isinstance(part,dict):
                    raise botslib.MappingFormatError(_(u'Must be dicts in tuple: get(%(mpath)s)'),{'mpath':mpaths})
                if 'BOTSID' not in part:
                    raise botslib.MappingFormatError(_(u'Section without "BOTSID": get(%(mpath)s)'),{'mpath':mpaths})
                for key,value in part.iteritems():
                    if not isinstance(key,basestring):
                        raise botslib.MappingFormatError(_(u'Keys must be strings: get(%(mpath)s)'),{'mpath':mpaths})
                    if not isinstance(value,basestring):
                        raise botslib.MappingFormatError(_(u'Values must be strings: get(%(mpath)s)'),{'mpath':mpaths})
            #sanity check of mpaths: None only allowed in last section of Mpath; check last part
            if not isinstance(mpaths[-1],dict):
                raise botslib.MappingFormatError(_(u'Must be dicts in tuple: get(%(mpath)s)'),{'mpath':mpaths})
            if 'BOTSID' not in mpaths[-1]:
                raise botslib.MappingFormatError(_(u'Last section without "BOTSID": get(%(mpath)s)'),{'mpath':mpaths})
            count = 0
            for key,value in mpaths[-1].iteritems():
                if not isinstance(key,basestring):
                    raise botslib.MappingFormatError(_(u'Keys must be strings in last section: get(%(mpath)s)'),{'mpath':mpaths})
                if value is None:
                    count += 1
                elif not isinstance(value,basestring):
                    raise botslib.MappingFormatError(_(u'Values must be strings (or none) in last section: get(%(mpath)s)'),{'mpath':mpaths})
            if count > 1:
                raise botslib.MappingFormatError(_(u'Max one "None" in last section: get(%(mpath)s)'),{'mpath':mpaths})
            if checklevel_mappingscript == 2:
                if hasattr(botsglobal.defmessage,'structure'):
                    full_mpath = botsglobal.inmessage.root.get_full_mpath(self) + mpaths
                    #~ print 'full_mpath',full_mpath
                    if not checkmpath(botsglobal.defmessage.structure,full_mpath):
                        print 'Error in mpath',mpaths
        for part in mpaths:
            if 'BOTSIDnr' not in part:
                part['BOTSIDnr'] = u'1'
        #go get it!
        terug =  self._getcore(*mpaths)
        botsglobal.logmap.debug(u'"%(terug)s" for get%(mpaths)s',{'terug':terug,'mpaths':str(mpaths)})
        return terug

    def _getcore(self,*mpaths):
        if len(mpaths) != 1:    #node is not end-node
            for key,value in mpaths[0].iteritems():          #check all items in mpath;
                if key not in self.record or value != self.record[key]:  #does not match/is not right node
                    return None
            else:   #all items in mpath are matched and OK; recursuve search
                for childnode in self.children:
                    terug =  childnode._getcore(*mpaths[1:]) #recursive search for rest of mpaths
                    if terug is not None:
                        return terug
                else:   #nothing found in children
                    return None
        else:   #node is end-node
            terug = 1 #default return value: if there is no 'None' in the mpath, but everything is matched, 1 is returned (like True)
            for key,value in mpaths[0].iteritems():          #check all items in mpath;
                if key not in self.record:  #does not match/is not right node
                    return None
                elif value is None:   #item has None-value; remember this value because this might be the right node
                    terug = self.record[key][:]    #copy to avoid memory problems
                elif value != self.record[key]:   #compare values
                    return None     #does not match/is not right node
            else:   #all keys/values in this mpathr are matched and OK.
                return terug        #either the remembered value is returned or 1 (as a boolean, indicated 'found)


    def get_full_mpath(self,node2find):
        if self is node2find:
            return tuple()
        else:
            for child in self.children:
                mpath = child.get_full_mpath(node2find)
                if mpath is not None:
                    if self.record:
                        return ({'BOTSID':self.record['BOTSID']},) + mpath
                    else:
                        return mpath
            return None
        
    def getcount(self):
        '''count the number of nodes/records under the node/in whole tree'''
        count = 0
        if self.record:
            count += 1   #count itself
        for childnode in self.children:
            count += childnode.getcount()
        return count

    def getcountoccurrences(self,*mpaths):
        ''' count number of occurences of mpath. Eg count nr of LIN's'''
        return len(list(self.getloop(*mpaths)))

    def getcountsum(self,*mpaths):
        ''' return the sum for all values found in mpath. Eg total number of ordered quantities.'''
        count = decimal.Decimal(0)
        mpath_for_found_nod = mpaths[-1].copy
        for key,value in mpaths[-1].items():
            if value is None:
                del mpaths[-1][key]
        for i in self.getloop(*mpaths):
            value = i.get(mpath_for_found_nod)
            if value:
                count += decimal.Decimal(value)
        return unicode(count)

    def getloop(self,*mpaths):
        ''' generator. Returns one by one the nodes as indicated in mpath
        '''
        #sanity check of mpaths
        if not mpaths or not isinstance(mpaths,tuple):
            raise botslib.MappingFormatError(_(u'Must be dicts in tuple: getloop(%(mpath)s)'),{'mpath':mpaths})
        for part in mpaths:
            if not isinstance(part,dict):
                raise botslib.MappingFormatError(_(u'Must be dicts in tuple: getloop(%(mpath)s)'),{'mpath':mpaths})
            if 'BOTSID' not in part:
                raise botslib.MappingFormatError(_(u'Section without "BOTSID": getloop(%(mpath)s)'),{'mpath':mpaths})
            for key,value in part.iteritems():
                if not isinstance(key,basestring):
                    raise botslib.MappingFormatError(_(u'Keys must be strings: getloop(%(mpath)s)'),{'mpath':mpaths})
                if not isinstance(value,basestring):
                    raise botslib.MappingFormatError(_(u'Values must be strings: getloop(%(mpath)s)'),{'mpath':mpaths})
            if 'BOTSIDnr' not in part:
                part['BOTSIDnr'] = u'1'

        for terug in self._getloopcore(*mpaths):
            botsglobal.logmap.debug(u'getloop %(mpaths)s returns "%(record)s".',{'mpaths':mpaths,'record':terug.record})
            yield terug

    def _getloopcore(self,*mpaths):
        ''' recursive part of getloop()
        '''
        for key,value in mpaths[0].iteritems():
            if key not in self.record or value != self.record[key]:
                return
        else:   #all items are checked and OK.
            if len(mpaths) == 1:
                yield self      #found!
            else:
                for childnode in self.children:
                    for terug in childnode._getloopcore(*mpaths[1:]): #search recursive for rest of mpaths
                        yield terug

    def getnozero(self,*mpaths):
        ''' like get, but either return a numerical value (as string) or None. If value to return is equal to zero, None is returned.
            useful eg for fixed records, where num fields are initialised with zeroes.
        '''
        terug = self.get(*mpaths)
        try:
            value = float(terug)
        except (TypeError,ValueError):
            return None
        if value == 0:
            return None
        return terug

    def put(self,*mpaths,**kwargs):
        #sanity check of mpaths
        if not mpaths or not isinstance(mpaths,tuple):
            raise botslib.MappingFormatError(_(u'Must be dicts in tuple: put(%(mpath)s)'),{'mpath':mpaths})
        for part in mpaths:
            if not isinstance(part,dict):
                raise botslib.MappingFormatError(_(u'Must be dicts in tuple: put(%(mpath)s)'),{'mpath':mpaths})
            if 'BOTSID' not in part:
                raise botslib.MappingFormatError(_(u'Section without "BOTSID": put(%(mpath)s)'),{'mpath':mpaths})
            for key,value in part.iteritems():
                if value is None:
                    botsglobal.logmap.debug(u'"None" in put %(mpaths)s.',{'mpaths':str(mpaths)})
                    return False
                if not isinstance(key,basestring):
                    raise botslib.MappingFormatError(_(u'Keys must be strings: put(%(mpath)s)'),{'mpath':mpaths})
                if kwargs.get('strip',True):
                    part[key] = unicode(value).strip()  #leading and trailing spaces are stripped from the values
                else:
                    part[key] = unicode(value)          #used for fixed ISA header of x12
            if 'BOTSIDnr' not in part:
                part['BOTSIDnr'] = u'1'

        if self._sameoccurence(mpaths[0]):
            self._putcore(*mpaths[1:])
        else:
            raise botslib.MappingRootError(_(u'Error in root put "%(mpath)s".'),{'mpath':mpaths[0]})
        botsglobal.logmap.debug(u'"True" for put %(mpaths)s',{'mpaths':str(mpaths)})
        return True

    def _putcore(self,*mpaths):
        if not mpaths:  #newmpath is exhausted, stop searching.
            return
        for childnode in self.children:
            if childnode.record['BOTSID'] == mpaths[0]['BOTSID'] and childnode._sameoccurence(mpaths[0]):    #checking of BOTSID is also done in sameoccurance!->performance!
                childnode._putcore(*mpaths[1:])
                return
        else:   #is not present in children, so append mpath as a new node
            self.append(Node(mpaths[0]))
            self.children[-1]._putcore(*mpaths[1:])

    def putloop(self,*mpaths):
        #sanity check of mpaths
        if not mpaths or not isinstance(mpaths,tuple):
            raise botslib.MappingFormatError(_(u'Must be dicts in tuple: putloop(%(mpath)s)'),{'mpath':mpaths})
        for part in mpaths:
            if not isinstance(part,dict):
                raise botslib.MappingFormatError(_(u'Must be dicts in tuple: putloop(%(mpath)s)'),{'mpath':mpaths})
            if 'BOTSID' not in part:
                raise botslib.MappingFormatError(_(u'Section without "BOTSID": putloop(%(mpath)s)'),{'mpath':mpaths})
            for key,value in part.iteritems():
                if not isinstance(key,basestring):
                    raise botslib.MappingFormatError(_(u'Keys must be strings: putloop(%(mpath)s)'),{'mpath':mpaths})
                if value is None:
                    return False
                part[key] = unicode(value).strip()
            if 'BOTSIDnr' not in part:
                part['BOTSIDnr'] = u'1'
        if self._sameoccurence(mpaths[0]):
            if len(mpaths)==1:
                return self
            return self._putloopcore(*mpaths[1:])
        else:
            raise botslib.MappingRootError(_(u'Error in root putloop "%(mpath)s".'),{'mpath':mpaths[0]})

    def _putloopcore(self,*mpaths):
        if len(mpaths) ==1: #end of mpath reached; always make new child-node
            self.append(Node(mpaths[0]))
            return self.children[-1]
        for childnode in self.children:  #if first part of mpaths exists already in children go recursive
            if childnode.record['BOTSID'] == mpaths[0]['BOTSID'] and childnode._sameoccurence(mpaths[0]):    #checking of BOTSID is also done in sameoccurance!->performance!
                return childnode._putloopcore(*mpaths[1:])
        else:   #is not present in children, so append a child, and go recursive
            self.append(Node(mpaths[0]))
            return self.children[-1]._putloopcore(*mpaths[1:])

    def _sameoccurence(self, mpath):
        ''' checks if all items that appear in both node and mpath have the same value. If so, all new items in mpath are added to node
        '''
        for key,value in self.record.iteritems():
            if key in mpath and mpath[key] != value:
                return False
        else:    #all equal keys have same values, thus both are 'equal'.
            self.record.update(mpath)   #add items to self.record that are new
            return True

    def sort(self,*mpaths):
        ''' sort nodes. eg in mappingscript:     inn.sort({'BOTSID':'UNH'},{'BOTSID':'LIN','C212.7140':None})
            This will sort the LIN segments by article number.
        '''
        comparekey = mpaths[1:]
        self.children.sort(key=lambda s: s.get(*comparekey))

    def stripnode(self):
        ''' removes spaces from all fields in tree.
            used in alt translations where a dict is returned by mappingscript indicating the out-tree should be used as inn.
            the out-tree has been formatted already, this is not OK for fixed formats (idoc!)
        '''
        if self.record is not None:
            for key, value in self.record.iteritems():
                self.record[key] = value.strip()
        for child in self.children:
            child.stripnode()

def checkmpath(structure,mpaths):
    ''' every part of mpaths should be in structure, at right level, have right fields.'''
    mpath = mpaths[0]
    for record_definition in structure:
        if record_definition[ID] == mpath['BOTSID']:
            for key in mpath:
                for field_definition in record_definition[FIELDS]:
                    if field_definition[ISFIELD]:
                        if key == field_definition[ID]:
                            break   #check next key
                    else:
                        for grammarsubfield in field_definition[SUBFIELDS]:   #loop subfields
                            if key == grammarsubfield[ID]:
                                break   #check next key
                        else:
                            continue #checking field_defintions
                        break   #check next key
                else:   #Not found in record!
                    return False
            if mpaths[1:]:
                return checkmpath(record_definition[LEVEL],mpaths[1:])
            else:
                return True    #no more levels, all fields found
    else:
        return False
