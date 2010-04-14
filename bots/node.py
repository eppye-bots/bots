import decimal
import copy
import botslib
import botsglobal
from botsconfig import *

comparekey=None

def nodecompare(node):
    global comparekey
    return node.get(*comparekey)


class Node(object):
    ''' Node class for building trees in inmessage and outmessage
    '''
    def __init__(self,record=None):
        self.record = record    #record is a dict with fields
        self.children = []
        self._queries = None

    def getquerie(self):
        ''' get  queries of a node '''
        if self._queries:
            return self._queries
        else:
            return {}

    def updatequerie(self,updatequeries):
        ''' set/update queries of a node with dict queries.
            use deepcopy to avoid memory problems
        '''
        if updatequeries:
            if self._queries is None:
                self._queries = copy.deepcopy(updatequeries)
            else:
                self._queries.update(copy.deepcopy(updatequeries))
    
    queries = property(getquerie,updatequerie)

    def processqueries(self,queries,maxlevel):
        ''' copies values for queries 'down the tree' untill right level.
            So when edi file is split up in messages,
            querie-info from higher levels is copied to message.'''
        self.queries = queries
        if self.record and not maxlevel:
            return
        for child in self.children:
            child.processqueries(self.queries,maxlevel-1)

    def append(self,node):
        '''append child to node'''
        self.children += [node]
        
    def display(self,level=0):
        '''for debugging
            usage: in mapping script:     inn.root.display()
        '''
        if level==0:
            print 'displaying all nodes in node tree:'
        print '    '*level,self.record
        for child in self.children:
            child.display(level+1)

    def displayqueries(self,level=0):
        '''for debugging
            usage: in mapping script:     inn.root.displayqueries()
        '''
        if level==0:
            print 'displaying queries for nodes in tree'
        print '    '*level,'node:',
        if self.record:
            print self.record['BOTSID'],
        else:
            print 'None',
        print '',
        print self.queries
        for child in self.children:
            child.displayqueries(level+1)

    def enhancedget(self,mpaths,replace=False):
        ''' to get QUERIES or SUBTRANSLATION while parsing edifile; 
            mpath can be 
            - dict:     do get(mpath); can not be a mpath with multiple 
            - tuple:    do get(mpath); can be multiple dicts in mapth
            - list:     for each listmembr do a get(); append the results 
            Used by:
            - QUERIES
            - SUBTRANSLATION
        '''
        if isinstance(mpaths,dict):
            return self.get(mpaths)
        elif isinstance(mpaths,tuple):
            return self.get(*mpaths)
        elif isinstance(mpaths,list):
            collect = u''
            for mpath in mpaths:
                found = self.get(mpath)
                if found:
                    if replace:
                        found = found.replace('.','_')
                    collect += found
            return collect
        else:
            raise botslib.MappingFormatError(u'must be dict, list or tuple: enhancedget($mpath)',mpath=mpaths)
        
    def change(self,where,change):
        '''         '''
        #find first matching node using 'where'. Do not look at other matching nodes (is a feature)
        #prohibit change of BOTSID?
        mpaths = where  #diff from getcore
        if not mpaths or not isinstance(mpaths,tuple):
            raise botslib.MappingFormatError(u'parameter "where" must be tuple: change(where=$where,change=$change)',where=where,change=change)
        #check: 'BOTSID' is required
        #check: all values should be strings
        for part in mpaths:
            if not isinstance(part,dict):
                raise botslib.MappingFormatError(u'parameter "where" must be dicts in a tuple: change(where=$where,change=$change)',where=where,change=change)
            if not 'BOTSID' in part:
                raise botslib.MappingFormatError(u'section without "BOTSID": change(where=$where,change=$change)',where=where,change=change)
            for key,value in part.iteritems():
                if  not isinstance(key,basestring):
                    raise botslib.MappingFormatError(u'keys must be strings: change(where=$where,change=$change)',where=where,change=change)
                if  not isinstance(value,basestring):
                    raise botslib.MappingFormatError(u'values must be strings: change(where=$where,change=$change)',where=where,change=change)
        #check change parameter
        if not change or not isinstance(change,dict):
            raise botslib.MappingFormatError(u'parameter "change" must be dict: change(where=$where,change=$change)',where=where,change=change)
        #remove 'BOTSID' from change. 
        #check: all values should be strings
        change.pop('BOTSID','nep')
        for key,value in change.iteritems():
            if  not isinstance(key,basestring):
                raise botslib.MappingFormatError(u'keys in "change" must be strings: change(where=$where,change=$change)',where=where,change=change)
            if  not isinstance(value,basestring) and value is not None:
                raise botslib.MappingFormatError(u'values in "change" must be strings or "None": change(where=$where,change=$change)',where=where,change=change)
        #go get it!
        terug =  self._changecore(where,change)
        botsglobal.logmap.debug(u'"%s" for change(where=%s,change=%s)',terug,str(where),str(change))
        return terug
        
    def _changecore(self,where,change): #diff from getcore
        mpaths = where  #diff from getcore
        mpath = mpaths[0]
        if self.record['BOTSID'] == mpath['BOTSID']: #is record-id equal to mpath-botsid? Not stricly needed, but gives much beter performance...
            for part in mpath:          #check all mpath-parts;
                if part in self.record:
                    if mpath[part] == self.record[part]:
                        continue
                    else:   #content of record-field and mpath-part do not match
                        return False
                else:   #not all parts of mpath  are in record, so no match:
                    return False
            else:   #all parts are matched, and OK. 
                if len(mpaths) == 1:    #mpath is exhausted; so we are there!!! #replace values with values in 'change'; delete if None
                    for key,value in change.iteritems():
                        if value is None:
                            self.record.pop(key,'dummy for pop')
                        else:
                            self.record[key]=value
                    return True
                else:
                    for childnode in self.children:
                        terug =  childnode._changecore(mpaths[1:],change) #search recursive for rest of mpaths #diff from getcore
                        if terug:
                            return terug
                    else:   #no child has given a valid return
                        return False
        else:   #record-id is not equal to mpath-botsid, so no match
            return False
            
        
    def delete(self,*mpaths):
        ''' delete the last record of mpath if found (first: find/identify, than delete.        '''
        if not mpaths or not isinstance(mpaths,tuple):
            raise botslib.MappingFormatError(u'must be dicts in tuple: delete($mpath)',mpath=mpaths)
        if len(mpaths) ==1:
            raise botslib.MappingFormatError(u'only one dict: not allowed. Use different solution: delete($mpath)',mpath=mpaths)
        #check: None only allowed in last section of Mpath (check firsts sections)
        #check: 'BOTSID' is required
        #check: all values should be strings
        for part in mpaths:
            if not isinstance(part,dict):
                raise botslib.MappingFormatError(u'must be dicts in tuple: delete($mpath)',mpath=mpaths)
            if not 'BOTSID' in part:
                raise botslib.MappingFormatError(u'section without "BOTSID": delete($mpath)',mpath=mpaths)
            for key,value in part.iteritems():
                if  not isinstance(key,basestring):
                    raise botslib.MappingFormatError(u'keys must be strings: delete($mpath)',mpath=mpaths)
                if  not isinstance(value,basestring):
                    raise botslib.MappingFormatError(u'values must be strings: delete($mpath)',mpath=mpaths)
        #go get it!
        terug =  bool(self._deletecore(*mpaths))
        botsglobal.logmap.debug(u'"%s" for delete%s',terug,str(mpaths))
        return terug  #return False if not removed, retunr True if removed
        
    def _deletecore(self,*mpaths):
        mpath = mpaths[0]
        if self.record['BOTSID'] == mpath['BOTSID']: #is record-id equal to mpath-botsid? Not stricly needed, but gives much beter performance...
            for part in mpath:          #check all mpath-parts;
                if part in self.record:
                    if mpath[part] == self.record[part]:
                        continue
                    else:   #content of record-field and mpath-part do not match
                        return 0
                else:   #not all parts of mpath  are in record, so no match:
                    return 0
            else:   #all parts are matched, and OK. 
                if len(mpaths) == 1:    #mpath is exhausted; so we are there!!!
                    return 2
                else:
                    for i, childnode in enumerate(self.children):
                        terug =  childnode._deletecore(*mpaths[1:]) #search recursive for rest of mpaths
                        if terug == 2:  #indicates node should be removed
                            del self.children[i]    #remove node
                            return 1    #this indicates: deleted succesfull, do not remove anymore (no removal of parents)
                        if terug:
                            return terug
                    else:   #no child has given a valid return
                        return 0
        else:   #record-id is not equal to mpath-botsid, so no match
            return 0

    def get(self,*mpaths):
        ''' get value of a field in a record from a edi-message
            mpath is xpath-alike query to identify the record/field
            function returns 1 value; return None if nothing found.
            if more than one value can be found: first one is returned
            starts searching in current node, then deeper
        '''
        if not mpaths or not isinstance(mpaths,tuple):
            raise botslib.MappingFormatError(u'must be dicts in tuple: get($mpath)',mpath=mpaths)
        for part in mpaths:
            if not isinstance(part,dict):
                raise botslib.MappingFormatError(u'must be dicts in tuple: get($mpath)',mpath=mpaths)
        #check: None only allowed in last section of Mpath (check firsts sections)
        #check: 'BOTSID' is required
        #check: all values should be strings
        for part in mpaths[:-1]:
            if not 'BOTSID' in part:
                raise botslib.MappingFormatError(u'section without "BOTSID": get($mpath)',mpath=mpaths)
            for key,value in part.iteritems():
                if  not isinstance(key,basestring):
                    raise botslib.MappingFormatError(u'keys must be strings: get($mpath)',mpath=mpaths)
                if  not isinstance(value,basestring):
                    raise botslib.MappingFormatError(u'values must be strings: get($mpath)',mpath=mpaths)
        #check: None only allowed in last section of Mpath (check last section)
        #check: 'BOTSID' is required
        #check: all values should be strings
        if not 'BOTSID' in mpaths[-1]:
            raise botslib.MappingFormatError(u'last section without "BOTSID": get($mpath)',mpath=mpaths)
        count = 0
        for key,value in mpaths[-1].iteritems():
            if  not isinstance(key,basestring):
                raise botslib.MappingFormatError(u'keys must be strings in last section: get($mpath)',mpath=mpaths)
            if value is None:
                count += 1
            elif not isinstance(value,basestring):
                raise botslib.MappingFormatError(u'values must be strings (or none) in last section: get($mpath)',mpath=mpaths)
        if count > 1:
            raise botslib.MappingFormatError(u'max one "None" in last section: get($mpath)',mpath=mpaths)
        #go get it!
        terug =  self._getcore(*mpaths)
        botsglobal.logmap.debug(u'"%s" for get%s',terug,str(mpaths))
        return terug
        
    def _getcore(self,*mpaths):
        mpath = mpaths[0]
        terug = 1 #if there is no 'None' in the mpath, but everything is matched, 1 is returned (like True)
        if self.record['BOTSID'] == mpath['BOTSID']: #is record-id equal to mpath-botsid? Not stricly needed, but gives much beter performance...
            for part in mpath:          #check all mpath-parts;
                if part in self.record:
                    if mpath[part] is None: #this is the field we are looking for; but not all matches have been made so remember value
                        terug = self.record[part][:]    #copy to avoid memory problems
                    else:   #compare values of mpath-part and recordfield 
                        if mpath[part] == self.record[part]:
                            continue
                        else:   #content of record-field and mpath-part do not match
                            return None
                else:   #not all parts of mpath  are in record, so no match:
                    return None
            else:   #all parts are matched, and OK. 
                if len(mpaths) == 1:    #mpath is exhausted; so we are there!!!
                    return terug
                else:
                    for childnode in self.children:
                        terug =  childnode._getcore(*mpaths[1:]) #search recursive for rest of mpaths
                        if terug:
                            return terug
                    else:   #no child has given a valid return
                        return None
        else:   #record-id is not equal to mpath-botsid, so no match
            return None
        
    def getcount(self):
        '''count the number of nodes/records uner the node/in whole tree'''
        count = 0
        if self.record:
            count += 1   #count itself
        for child in self.children:
            count += child.getcount()
        return count

    def getcountoccurrences(self,*mpaths):
        ''' count number of occurences of mpath. Eg count nr of LIN's'''
        count = 0 
        for value in self.getloop(*mpaths):
            count += 1
        return count

    def getcountsum(self,*mpaths):
        ''' return the sum for all values found in mpath. Eg total number of ordered quantities.'''
        count = decimal.Decimal(0)
        for i in self.getloop(*mpaths[:-1]):
            value = i.get(*mpaths[-2:])
            if value:
                count += decimal.Decimal(value)
        return unicode(count)

    def getloop(self,*mpaths):
        ''' generator. Returns one by one the nodes as indicated in mpath
        '''
        #check validity mpaths
        if not mpaths or not isinstance(mpaths,tuple):
            raise botslib.MappingFormatError(u'must be dicts in tuple: getloop($mpath)',mpath=mpaths)
        for part in mpaths:
            if not isinstance(part,dict):
                raise botslib.MappingFormatError(u'must be dicts in tuple: getloop($mpath)',mpath=mpaths)
            if not 'BOTSID' in part:
                raise botslib.MappingFormatError(u'section without "BOTSID": getloop($mpath)',mpath=mpaths)
            for key,value in part.iteritems():
                if  not isinstance(key,basestring):
                    raise botslib.MappingFormatError(u'keys must be strings: getloop($mpath)',mpath=mpaths)
                if  not isinstance(value,basestring):
                    raise botslib.MappingFormatError(u'values must be strings: getloop($mpath)',mpath=mpaths)
            
        for terug in self._getloopcore(*mpaths):
            botsglobal.logmap.debug(u'getloop %s returns "%s".',mpaths,terug.record)
            yield terug
        
    def _getloopcore(self,*mpaths):
        ''' recursive part of getloop()
        '''
        mpath = mpaths[0]
        if self.record['BOTSID'] == mpath['BOTSID']: #found right record
            for part in mpath:
                if not part in self.record or mpath[part] != self.record[part]:
                    return
            else:   #all parts are checked, and OK. 
                if len(mpaths) == 1:
                    yield self
                else:
                    for childnode in self.children:
                        for terug in childnode._getloopcore(*mpaths[1:]): #search recursive for rest of mpaths
                            yield terug
        return

    def getnozero(self,*mpaths):
        terug = self.get(*mpaths)
        try:
            value = float(terug)
        except TypeError:
            return None
        except ValueError:
            return None
        if value == 0:
            return None
        return terug
        

    def put(self,*mpaths):
        if not mpaths or not isinstance(mpaths,tuple):
            raise botslib.MappingFormatError(u'must be dicts in tuple: put($mpath)',mpath=mpaths)
        for part in mpaths:
            if not isinstance(part,dict):
                raise botslib.MappingFormatError(u'must be dicts in tuple: put($mpath)',mpath=mpaths)
        #check: 'BOTSID' is required
        #check: all values should be strings
        for part in mpaths:
            if not 'BOTSID' in part:
                raise botslib.MappingFormatError(u'section without "BOTSID": put($mpath)',mpath=mpaths)
            for key,value in part.iteritems():
                if value is None:
                    botsglobal.logmap.debug(u'"None" in put %s.',str(mpaths))
                    return False
                if  not isinstance(key,basestring):
                    raise botslib.MappingFormatError(u'keys must be strings: put($mpath)',mpath=mpaths)
                part[key] = unicode(value).strip()  #leading and trailing spaces are stripped from the values
        
        if self.sameoccurence(mpaths[0]):
            self._putcore(*mpaths[1:])
        else:
            raise botslib.MappingRootError(u'error in root put "$mpath".',mpath=mpaths[0])
        botsglobal.logmap.debug(u'"True" for put %s',str(mpaths))
        return True

    def _putcore(self,*mpaths):
        if not mpaths:  #newmpath is exhausted, stop searching.
            return True
        for node in self.children:
            if node.record['BOTSID']==mpaths[0]['BOTSID'] and node.sameoccurence(mpaths[0]):
                node._putcore(*mpaths[1:])
                return
        else:   #is not present in children, so append
            self.append(Node(mpaths[0]))
            self.children[-1]._putcore(*mpaths[1:])

    def putloop(self,*mpaths):
        if not mpaths or not isinstance(mpaths,tuple):
            raise botslib.MappingFormatError(u'must be dicts in tuple: putloop($mpath)',mpath=mpaths)
        for part in mpaths:
            if not isinstance(part,dict):
                raise botslib.MappingFormatError(u'must be dicts in tuple: putloop($mpath)',mpath=mpaths)
        #check: 'BOTSID' is required
        #check: all values should be strings
        for part in mpaths:
            if not 'BOTSID' in part:
                raise botslib.MappingFormatError(u'section without "BOTSID": putloop($mpath)',mpath=mpaths)
            for key,value in part.iteritems():
                if  not isinstance(key,basestring):
                    raise botslib.MappingFormatError(u'keys must be strings: putloop($mpath)',mpath=mpaths)
                if value is None:
                    return False
                #~ if  not isinstance(value,basestring):
                    #~ raise botslib.MappingFormatError(u'values must be strings in putloop%s'%(str(mpaths)))
                part[key] = unicode(value).strip()
                
        if self.sameoccurence(mpaths[0]):
            if len(mpaths)==1:
               return self
            return self._putloopcore(*mpaths[1:])
        else:
            raise botslib.MappingRootError(u'error in root putloop "$mpath".',mpath=mpaths[0])

    def _putloopcore(self,*mpaths):
        if len(mpaths) ==1: #end of mpath reached; always make new child-node
            self.append(Node(mpaths[0]))
            return self.children[-1]
        for node in self.children:  #if first part of mpaths exists already in children go recursive
            if node.record['BOTSID']==mpaths[0]['BOTSID'] and node.sameoccurence(mpaths[0]):
                return node._putloopcore(*mpaths[1:])
        else:   #is not present in children, so append a child, and go recursive
            self.append(Node(mpaths[0]))
            return self.children[-1]._putloopcore(*mpaths[1:])

    def sameoccurence(self, mpath):
        for key,value in self.record.iteritems():
            if (key in mpath) and (mpath[key]!=value):
                return False
        else:    #all equal keys have same values, thus both are 'equal'.
            self.record.update(mpath)
            return True

    def sort(self,*mpaths):
        global comparekey
        comparekey = mpaths[1:]
        self.children.sort(key=nodecompare)
