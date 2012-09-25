try:
    import cdecimal as decimal
except ImportError:
    import decimal
import copy
from django.utils.translation import ugettext as _
import botslib
import botsglobal
from botsconfig import *


class Node(object):
    ''' Node class for building trees in inmessage and outmessage
    '''
    def __init__(self,record=None,botsidnr=None):
        self.record = record    #record is a dict with fields
        if self.record:
            if not 'BOTSIDnr' in self.record:
                if botsidnr:
                    self.record['BOTSIDnr'] = botsidnr
                else:
                    self.record['BOTSIDnr'] = u'1'
        self.children = []
        self._queries = None

    def append(self,childnode):
        '''append child to node'''
        self.children += [childnode]

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
                    raise botslib.MappingFormatError(_(u'member in list $mpath must be dict or tuple (in enhancedget).'),mpath=mpath)
                if found:
                    collect += found
            return collect
        else:
            raise botslib.MappingFormatError(_(u'must be dict, list or tuple: enhancedget($mpath)'),mpath=mpaths)

    def get_queries_from_edi(self,structurerecord):
        ''' extract information from edifile using QUERIES in grammar.structure; information will be placed in ta_info and in db-ta
        '''
        tmpdict = {}
        #~ print 'get_queries_from_edi', structurerecord[QUERIES]
        for key,value in structurerecord[QUERIES].items():
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
            raise botslib.MappingFormatError(_(u'parameter "where" must be tuple: getrecord($mpath)'),mpath=mpaths)
        for part in mpaths:
            if not isinstance(part,dict):
                raise botslib.MappingFormatError(_(u'parameter "mpaths" must be dicts in a tuple: getrecord($mpath)'),mpath=mpaths)
            if not 'BOTSID' in part:
                raise botslib.MappingFormatError(_(u'section without "BOTSID": getrecord($mpath)'),mpath=mpaths)
            for key,value in part.iteritems():
                if  not isinstance(key,basestring):
                    raise botslib.MappingFormatError(_(u'keys must be strings: getrecord($mpath)'),mpath=mpaths)
                if  not isinstance(value,basestring):
                    raise botslib.MappingFormatError(_(u'values must be strings: getrecord($mpath)'),mpath=mpaths)
            if not 'BOTSIDnr' in part:
                part['BOTSIDnr'] = u'1'
        #go get it!
        terug =  self._getrecordcore(*mpaths)
        botsglobal.logmap.debug(u'"%s" for getrecord%s',str(terug),str(mpaths))
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
            raise botslib.MappingFormatError(_(u'parameter "where" must be tuple: change(where=$where,change=$change)'),where=where,change=change)
        for part in where:
            if not isinstance(part,dict):
                raise botslib.MappingFormatError(_(u'parameter "where" must be dicts in a tuple: change(where=$where,change=$change)'),where=where,change=change)
            if not 'BOTSID' in part:
                raise botslib.MappingFormatError(_(u'section without "BOTSID": change(where=$where,change=$change)'),where=where,change=change)
            for key,value in part.iteritems():
                if  not isinstance(key,basestring):
                    raise botslib.MappingFormatError(_(u'keys must be strings: change(where=$where,change=$change)'),where=where,change=change)
                if  not isinstance(value,basestring):
                    raise botslib.MappingFormatError(_(u'values must be strings: change(where=$where,change=$change)'),where=where,change=change)
            if not 'BOTSIDnr' in part:
                part['BOTSIDnr'] = u'1'
        #sanity check 'change' parameter
        if not change or not isinstance(change,dict):
            raise botslib.MappingFormatError(_(u'parameter "change" must be dict: change(where=$where,change=$change)'),where=where,change=change)
        change.pop('BOTSID','nep')  #remove 'BOTSID' from change. BOTSID can not be changed
        change.pop('BOTSIDnr','nep')  #remove 'BOTSIDnr' from change. BOTSIDnr can not be changed
        for key,value in change.iteritems():
            if  not isinstance(key,basestring):
                raise botslib.MappingFormatError(_(u'keys in "change" must be strings: change(where=$where,change=$change)'),where=where,change=change)
            if  not isinstance(value,basestring) and value is not None:     #if None, item is deleted
                raise botslib.MappingFormatError(_(u'values in "change" must be strings or "None": change(where=$where,change=$change)'),where=where,change=change)
        #go get it!
        terug =  self._changecore(where,change)
        botsglobal.logmap.debug(u'"%s" for change(where=%s,change=%s)',terug,str(where),str(change))
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
            raise botslib.MappingFormatError(_(u'must be dicts in tuple: delete($mpath)'),mpath=mpaths)
        if len(mpaths) ==1:
            raise botslib.MappingFormatError(_(u'only one dict: not allowed. Use different solution: delete($mpath)'),mpath=mpaths)
        for part in mpaths:
            if not isinstance(part,dict):
                raise botslib.MappingFormatError(_(u'must be dicts in tuple: delete($mpath)'),mpath=mpaths)
            if not 'BOTSID' in part:
                raise botslib.MappingFormatError(_(u'section without "BOTSID": delete($mpath)'),mpath=mpaths)
            for key,value in part.iteritems():
                if  not isinstance(key,basestring):
                    raise botslib.MappingFormatError(_(u'keys must be strings: delete($mpath)'),mpath=mpaths)
                if  not isinstance(value,basestring):
                    raise botslib.MappingFormatError(_(u'values must be strings: delete($mpath)'),mpath=mpaths)
            if not 'BOTSIDnr' in part:
                part['BOTSIDnr'] = u'1'
        #go get it!
        terug =  bool(self._deletecore(*mpaths))
        botsglobal.logmap.debug(u'"%s" for delete%s',terug,str(mpaths))
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
        #sanity check of mpaths. None only allowed in last section of Mpath; first checks all parts except last one
        if not mpaths or not isinstance(mpaths,tuple):
            raise botslib.MappingFormatError(_(u'must be dicts in tuple: get($mpath)'),mpath=mpaths)
        for part in mpaths[:-1]:
            if not isinstance(part,dict):
                raise botslib.MappingFormatError(_(u'must be dicts in tuple: get($mpath)'),mpath=mpaths)
            if not 'BOTSID' in part:
                raise botslib.MappingFormatError(_(u'section without "BOTSID": get($mpath)'),mpath=mpaths)
            for key,value in part.iteritems():
                if  not isinstance(key,basestring):
                    raise botslib.MappingFormatError(_(u'keys must be strings: get($mpath)'),mpath=mpaths)
                if  not isinstance(value,basestring):
                    raise botslib.MappingFormatError(_(u'values must be strings: get($mpath)'),mpath=mpaths)
            if not 'BOTSIDnr' in part:
                part['BOTSIDnr'] = u'1'
        #sanity check of mpaths: None only allowed in last section of Mpath; check last part
        if not isinstance(mpaths[-1],dict):
            raise botslib.MappingFormatError(_(u'must be dicts in tuple: get($mpath)'),mpath=mpaths)
        if not 'BOTSID' in mpaths[-1]:
            raise botslib.MappingFormatError(_(u'last section without "BOTSID": get($mpath)'),mpath=mpaths)
        count = 0
        for key,value in mpaths[-1].iteritems():
            if  not isinstance(key,basestring):
                raise botslib.MappingFormatError(_(u'keys must be strings in last section: get($mpath)'),mpath=mpaths)
            if value is None:
                count += 1
            elif not isinstance(value,basestring):
                raise botslib.MappingFormatError(_(u'values must be strings (or none) in last section: get($mpath)'),mpath=mpaths)
        if count > 1:
            raise botslib.MappingFormatError(_(u'max one "None" in last section: get($mpath)'),mpath=mpaths)
        if not 'BOTSIDnr' in mpaths[-1]:
            mpaths[-1]['BOTSIDnr'] = u'1'
        #go get it!
        terug =  self._getcore(*mpaths)
        botsglobal.logmap.debug(u'"%s" for get%s',terug,str(mpaths))
        return terug

    def _getcore(self,*mpaths):
        terug = 1 #if there is no 'None' in the mpath, but everything is matched, 1 is returned (like True)
        for key,value in mpaths[0].iteritems():          #check all items in mpath;
            if key not in self.record:
                return None         #does not match/is not right node
            if not value is None:   #regular value (string), so compare
                if value != self.record[key]:
                    return None     #does not match/is not right node
                continue            #matches, so continue to check other items
            #item has None-value; remember this value because this might be the right node
            terug = self.record[key][:]    #copy to avoid memory problems
        else:   #all parts are matched and OK.
            if len(mpaths) == 1:    #mpath is exhausted; so we are there!!!
                return terug        #either the remembered value is returned or 1 (as a boolean, indicated 'found)
            else:
                for childnode in self.children:
                    terug =  childnode._getcore(*mpaths[1:]) #search recursive for rest of mpaths
                    if terug:
                        return terug
                else:   #no child has given a valid return
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
        mpathscopy = copy.deepcopy(mpaths)
        for key,value in mpaths[-1].items():
            if value is None:
                del mpathscopy[-1][key]
        for i in self.getloop(*mpathscopy):
            value = i.get(mpaths[-1])
            if value:
                count += decimal.Decimal(value)
        return unicode(count)

    def getloop(self,*mpaths):
        ''' generator. Returns one by one the nodes as indicated in mpath
        '''
        #sanity check of mpaths
        if not mpaths or not isinstance(mpaths,tuple):
            raise botslib.MappingFormatError(_(u'must be dicts in tuple: getloop($mpath)'),mpath=mpaths)
        for part in mpaths:
            if not isinstance(part,dict):
                raise botslib.MappingFormatError(_(u'must be dicts in tuple: getloop($mpath)'),mpath=mpaths)
            if not 'BOTSID' in part:
                raise botslib.MappingFormatError(_(u'section without "BOTSID": getloop($mpath)'),mpath=mpaths)
            for key,value in part.iteritems():
                if  not isinstance(key,basestring):
                    raise botslib.MappingFormatError(_(u'keys must be strings: getloop($mpath)'),mpath=mpaths)
                if  not isinstance(value,basestring):
                    raise botslib.MappingFormatError(_(u'values must be strings: getloop($mpath)'),mpath=mpaths)
            if not 'BOTSIDnr' in part:
                part['BOTSIDnr'] = u'1'

        for terug in self._getloopcore(*mpaths):
            botsglobal.logmap.debug(u'getloop %s returns "%s".',mpaths,terug.record)
            yield terug

    def _getloopcore(self,*mpaths):
        ''' recursive part of getloop()
        '''
        for key,value in mpaths[0].iteritems():
            if not key in self.record or value != self.record[key]:
                return
        else:   #all items are checked and OK.
            if len(mpaths) == 1:
                yield self      #found!
            else:
                for childnode in self.children:
                    for terug in childnode._getloopcore(*mpaths[1:]): #search recursive for rest of mpaths
                        yield terug
        return

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
            raise botslib.MappingFormatError(_(u'must be dicts in tuple: put($mpath)'),mpath=mpaths)
        for part in mpaths:
            if not isinstance(part,dict):
                raise botslib.MappingFormatError(_(u'must be dicts in tuple: put($mpath)'),mpath=mpaths)
            if not 'BOTSID' in part:
                raise botslib.MappingFormatError(_(u'section without "BOTSID": put($mpath)'),mpath=mpaths)
            for key,value in part.iteritems():
                if value is None:
                    botsglobal.logmap.debug(u'"None" in put %s.',str(mpaths))
                    return False
                if  not isinstance(key,basestring):
                    raise botslib.MappingFormatError(_(u'keys must be strings: put($mpath)'),mpath=mpaths)
                if kwargs and 'strip' in kwargs and kwargs['strip'] == False:
                    part[key] = unicode(value)          #used for fixed ISA header of x12
                else:
                    part[key] = unicode(value).strip()  #leading and trailing spaces are stripped from the values
            if not 'BOTSIDnr' in part:
                part['BOTSIDnr'] = u'1'

        if self._sameoccurence(mpaths[0]):
            self._putcore(*mpaths[1:])
        else:
            raise botslib.MappingRootError(_(u'error in root put "$mpath".'),mpath=mpaths[0])
        botsglobal.logmap.debug(u'"True" for put %s',str(mpaths))
        return True

    def _putcore(self,*mpaths):
        if not mpaths:  #newmpath is exhausted, stop searching.
            return True
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
            raise botslib.MappingFormatError(_(u'must be dicts in tuple: putloop($mpath)'),mpath=mpaths)
        for part in mpaths:
            if not isinstance(part,dict):
                raise botslib.MappingFormatError(_(u'must be dicts in tuple: putloop($mpath)'),mpath=mpaths)
            if not 'BOTSID' in part:
                raise botslib.MappingFormatError(_(u'section without "BOTSID": putloop($mpath)'),mpath=mpaths)
            for key,value in part.iteritems():
                if  not isinstance(key,basestring):
                    raise botslib.MappingFormatError(_(u'keys must be strings: putloop($mpath)'),mpath=mpaths)
                if value is None:
                    return False
                #~ if  not isinstance(value,basestring):
                    #~ raise botslib.MappingFormatError(_(u'values must be strings in putloop%s'%(str(mpaths)))
                part[key] = unicode(value).strip()
            if not 'BOTSIDnr' in part:
                part['BOTSIDnr'] = u'1'
        if self._sameoccurence(mpaths[0]):
            if len(mpaths)==1:
                return self
            return self._putloopcore(*mpaths[1:])
        else:
            raise botslib.MappingRootError(_(u'error in root putloop "$mpath".'),mpath=mpaths[0])

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

    def _nodecompare(self,node2compare):
        ''' helper function for sort '''
        return node2compare.get(*self.comparekey)

    def sort(self,*mpaths):
        ''' sort nodes. eg in mappingscript:     inn.sort({'BOTSID':'UNH'},{'BOTSID':'LIN','C212.7140':None})
            This will sort the LIN segments by article number.
        '''
        self.comparekey = mpaths[1:]
        self.children.sort(key=self._nodecompare)

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
