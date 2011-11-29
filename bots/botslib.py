''' Base library for bots. Botslib should not import from other Bots-modules.'''
import sys
import os
import codecs
import traceback
import subprocess
import time
import datetime
import socket   #to set a time-out for connections
import shutil
import string
import urlparse
import urllib
import platform
import django
from django.utils.translation import ugettext as _
#Bots-modules
from botsconfig import *
import botsglobal #as botsglobal

def botsinfo():
    return [
            (_(u'platform'),platform.platform()),
            (_(u'machine'),platform.machine()),
            (_(u'python version'),sys.version),
            (_(u'django version'),django.VERSION),
            (_(u'bots version'),botsglobal.version),
            (_(u'bots installation path'),botsglobal.ini.get('directories','botspath')),
            (_(u'config path'),botsglobal.ini.get('directories','config')),
            (_(u'botssys path'),botsglobal.ini.get('directories','botssys')),
            (_(u'usersys path'),botsglobal.ini.get('directories','usersysabs')),
            (u'DATABASE_ENGINE',botsglobal.settings.DATABASE_ENGINE),
            (u'DATABASE_NAME',botsglobal.settings.DATABASE_NAME),
            (u'DATABASE_USER',botsglobal.settings.DATABASE_USER),
            (u'DATABASE_HOST',botsglobal.settings.DATABASE_HOST),
            (u'DATABASE_PORT',botsglobal.settings.DATABASE_PORT),
            (u'DATABASE_OPTIONS',botsglobal.settings.DATABASE_OPTIONS),
            ]

#**********************************************************/**
#**************getters/setters for some globals***********************/**
#**********************************************************/**
def get_minta4query():
    ''' get the first idta for queries etc.'''
    return botsglobal.minta4query

def set_minta4query():
    if botsglobal.minta4query:    #if already set, do nothing
        return
    else:
        botsglobal.minta4query = _Transaction.processlist[1]  #set root-idta of current run

def set_minta4query_retry():
    botsglobal.minta4query = get_idta_last_error()
    return botsglobal.minta4query

def get_idta_last_error():
    for row in query('''SELECT idta
                        FROM  filereport
                        GROUP BY idta
                        HAVING MAX(statust) != %(statust)s''',
                        {'statust':DONE}):
        #found incoming file with error
        for row2 in query('''SELECT min(reportidta) as min
                            FROM  filereport
                            WHERE idta = %(idta)s ''',
                            {'idta':row['idta']}):
            return row2['min']
    return 0    #if no error found.

def set_minta4query_crashrecovery():
    ''' set/return rootidta of last run - that is supposed to crashed'''
    for row in query('''SELECT max(idta) as max
                        FROM  ta
                        WHERE script= 0
                        '''):
        if row['max'] is None:
            return 0
        botsglobal.minta4query = row['max']
        return botsglobal.minta4query
    return 0

def getlastrun():
    return _Transaction.processlist[1]  #get root-idta of last run

def setrouteid(routeid):
    botsglobal.routeid = routeid

def getrouteid():
    return botsglobal.routeid

def setpreprocessnumber(statusnumber):
    botsglobal.preprocessnumber = statusnumber 
def getpreprocessnumber():
    terug = botsglobal.preprocessnumber
    botsglobal.preprocessnumber +=2
    return terug 
    
#**********************************************************/**
#***************** class  Transaction *********************/**
#**********************************************************/**
class _Transaction(object):
    ''' abstract class for db-ta.
        This class is used for communication with db-ta.
    '''
    #filtering values fo db handling (to avoid unknown fields in db.
    filterlist=['statust','status','divtext','parent','child','script','frompartner','topartner','fromchannel','tochannel','editype','messagetype','merge',
                'testindicator','reference','frommail','tomail','contenttype','errortext','filename','charset','alt','idroute','nrmessages','retransmit',
                'confirmasked','confirmed','confirmtype','confirmidta','envelope','botskey','cc']
    processlist=[0]  #stack for bots-processes. last one is the current process; starts with 1 element in list: root

    def update(self,**ta_info):
        ''' Updates db-ta with named-parameters/dict.
            Use a filter to update only valid fields in db-ta
        '''
        setstring = ','.join([key+'=%('+key+')s' for key in ta_info if key in _Transaction.filterlist])
        if not setstring:   #nothing to update
            return
        ta_info['selfid'] = self.idta   #always set this...I'm not sure if this is needed...take no chances
        cursor = botsglobal.db.cursor()
        cursor.execute(u'''UPDATE ta
                            SET '''+setstring+ '''
                            WHERE idta=%(selfid)s''',
                            ta_info)
        botsglobal.db.commit()
        cursor.close()

    def delete(self):
        '''Deletes current transaction '''
        cursor = botsglobal.db.cursor()
        cursor.execute(u'''DELETE FROM ta
                            WHERE idta=%(selfid)s''',
                            {'selfid':self.idta})
        botsglobal.db.commit()
        cursor.close()

    def failure(self):
        '''Failure: deletes all children of transaction (and children of children etc)'''
        cursor = botsglobal.db.cursor()
        cursor.execute(u'''SELECT idta FROM ta
                           WHERE idta>%(rootidta)s
                           AND parent=%(selfid)s''',
                            {'selfid':self.idta,'rootidta':get_minta4query()})
        rows = cursor.fetchall()
        for row in rows:
            ta=OldTransaction(row['idta'])
            ta.failure()
        cursor.execute(u'''DELETE FROM ta
                            WHERE idta>%(rootidta)s
                            AND parent=%(selfid)s''',
                            {'selfid':self.idta,'rootidta':get_minta4query()})
        botsglobal.db.commit()
        cursor.close()

    def mergefailure(self):
        '''Failure while merging: all parents of transaction get status OK (turn back)'''
        cursor = botsglobal.db.cursor()
        cursor.execute(u'''UPDATE ta
                           SET statust=%(statustnew)s
                           WHERE idta>%(rootidta)s
                           AND child=%(selfid)s
                           AND statust=%(statustold)s''',
                            {'selfid':self.idta,'statustold':DONE,'statustnew':OK,'rootidta':get_minta4query()})
        botsglobal.db.commit()
        cursor.close()

    def syn(self,*ta_vars):
        '''access of attributes of transaction as ta.fromid, ta.filename etc'''
        cursor = botsglobal.db.cursor()
        varsstring = ','.join(ta_vars)
        cursor.execute(u'''SELECT ''' + varsstring + '''
                            FROM ta
                            WHERE idta=%(selfid)s''',
                            {'selfid':self.idta})
        result = cursor.fetchone()
        for key in result.keys():
            setattr(self,key,result[key])
        cursor.close()

    def synall(self):
        '''access of attributes of transaction as ta.fromid, ta.filename etc'''
        cursor = botsglobal.db.cursor()
        varsstring = ','.join(self.filterlist)
        cursor.execute(u'''SELECT ''' + varsstring + '''
                            FROM ta
                            WHERE idta=%(selfid)s''',
                            {'selfid':self.idta})
        result = cursor.fetchone()
        for key in result.keys():
            setattr(self,key,result[key])
        cursor.close()

    def copyta(self,status,**ta_info):
        ''' copy: make a new transaction, copy '''
        script = _Transaction.processlist[-1]
        cursor = botsglobal.db.cursor()
        cursor.execute(u'''INSERT INTO ta (script,  status,     parent,frompartner,topartner,fromchannel,tochannel,editype,messagetype,alt,merge,testindicator,reference,frommail,tomail,charset,contenttype,filename,idroute,nrmessages,botskey)
                                SELECT   %(script)s,%(newstatus)s,idta,frompartner,topartner,fromchannel,tochannel,editype,messagetype,alt,merge,testindicator,reference,frommail,tomail,charset,contenttype,filename,idroute,nrmessages,botskey
                                FROM  ta
                                WHERE idta=%(selfid)s''',
                                {'selfid':self.idta,'script':script,'newstatus':status})
        newidta = cursor.lastrowid
        if not newidta:   #if botsglobal.settings.DATABASE_ENGINE ==
            cursor.execute('''SELECT lastval() as idta''')
            newidta = cursor.fetchone()['idta']
        botsglobal.db.commit()
        cursor.close()
        newdbta = OldTransaction(newidta)
        newdbta.update(**ta_info)
        return newdbta


class OldTransaction(_Transaction):
    def __init__(self,idta,**ta_info):
        '''Use old transaction '''
        self.idta = idta
        self.talijst=[]
        for key in ta_info.keys():   #only used by trace
            setattr(self,key,ta_info[key])  #could be done better, but SQLite does not support .items()


class NewTransaction(_Transaction):
    def __init__(self,**ta_info):
        '''Generates new transaction, returns key of transaction '''
        updatedict = dict([(key,value) for key,value in ta_info.items() if key in _Transaction.filterlist])
        updatedict['script'] = _Transaction.processlist[-1]
        namesstring = ','.join([key for key in updatedict])
        varsstring = ','.join(['%('+key+')s' for key in updatedict])
        cursor = botsglobal.db.cursor()
        cursor.execute(u'''INSERT INTO ta (''' + namesstring + ''')
                                 VALUES   (''' + varsstring + ''')''',
                                updatedict)
        self.idta = cursor.lastrowid
        if not self.idta:
            cursor.execute('''SELECT lastval() as idta''')
            self.idta = cursor.fetchone()['idta']
        botsglobal.db.commit()
        cursor.close()


class NewProcess(NewTransaction):
    ''' Used in logging of processes. Each process is placed on stack processlist'''
    def __init__(self,functionname=''):
        super(NewProcess,self).__init__(filename=functionname,status=PROCESS,idroute=getrouteid())
        _Transaction.processlist.append(self.idta)

    def update(self,**ta_info):
        super(NewProcess,self).update(**ta_info)
        _Transaction.processlist.pop()


def trace_origin(ta,where=None):
    ''' bots traces back all from the current step/ta. 
        where is a dict that is used to indicate a condition.
        eg:  {'status':EXTERNIN}
        If bots finds a ta for which this is true, the ta is added to a list.
        The list is returned when all tracing is done, and contains all ta's for which 'where' is True
    '''
    def trace_recurse(ta):
        ''' recursive
            walk over ta's backward (to origin).
            if condition is met, add the ta to a list
        '''
        for idta in get_parent(ta):
            donelijst.append(idta)
            taparent=OldTransaction(idta=idta)
            taparent.synall()
            for key,value in where.items():
                if getattr(taparent,key) != value:
                    break
            else:   #all where-criteria are true; check if we already have this ta
                teruglijst.append(taparent)
            trace_recurse(taparent)
    def get_parent(ta):
        ''' yields the parents of a ta '''
        if ta.parent:   #the is a parent via the normal parent-pointer
            if ta.parent not in donelijst:
                yield ta.parent
        else:           #no parent via parent-link, so look via child-link
            for row in query('''SELECT idta
                                 FROM  ta
                                 WHERE idta>%(rootidta)s
                                 AND child=%(idta)s''',
                                {'idta':ta.idta,'rootidta':get_minta4query()}):
                if row['idta'] in donelijst:
                    continue
                yield row['idta']
        
    donelijst = []
    teruglijst = []
    ta.syn('parent')
    trace_recurse(ta)
    return teruglijst


def addinfocore(change,where,wherestring):
    ''' core function for add/changes information in db-ta's.
        where-dict selects db-ta's, change-dict sets values;
        returns the number of db-ta that have been changed.
    '''
    if 'rootidta' not in where:
        where['rootidta']=get_minta4query()
        wherestring = ' idta > %(rootidta)s AND ' + wherestring
    if 'statust' not in where:  #by default: look only for statust is OK
        where['statust']=OK
        wherestring += ' AND statust = %(statust)s '
    if 'statust' not in change: #by default: new ta is OK
        change['statust']= OK
    counter = 0 #count the number of dbta changed
    for row in query(u'''SELECT idta FROM ta WHERE '''+wherestring,where):
        counter += 1
        ta_from = OldTransaction(row['idta'])
        ta_from.copyta(**change)     #make new ta from ta_from, using parameters from change
        ta_from.update(statust=DONE)    #update 'old' ta
    return counter


def addinfo(change,where):
    ''' add/changes information in db-ta's by coping the ta's; the status is updated.
        using only change and where dict.'''
    wherestring = ' AND '.join([key+'=%('+key+')s ' for key in where])   #wherestring for copy & done
    return addinfocore(change=change,where=where,wherestring=wherestring)

def updateinfo(change,where):
    ''' update info in ta if not set; no status change.
        where-dict selects db-ta's, change-dict sets values;
        returns the number of db-ta that have been changed.
    '''
    if 'statust' not in where:
        where['statust']=OK
    wherestring = ' AND '.join([key+'=%('+key+')s ' for key in where])   #wherestring for copy & done
    if 'rootidta' not in where:
        where['rootidta']=get_minta4query()
        wherestring = ' idta > %(rootidta)s AND ' + wherestring
    counter = 0 #count the number of dbta changed
    for row in query(u'''SELECT idta FROM ta WHERE '''+wherestring,where):
        counter += 1
        ta_from = OldTransaction(row['idta'])
        ta_from.synall()
        defchange = {}
        for key,value in change.items():
            if value and not getattr(ta_from,key,None): #if there is a value and the key is not set in ta_from:
                defchange[key]=value
        ta_from.update(**defchange)
    return counter

def changestatustinfo(change,where):
    ''' update info in ta if not set; no status change.
        where-dict selects db-ta's, change is the new statust;
        returns the number of db-ta that have been changed.
    '''
    if not isinstance(change,int):
        raise BotsError(_(u'change not valid: expect status to be an integer. Programming error.'))
    if 'statust' not in where:
        where['statust']=OK
    wherestring = ' AND '.join([key+'=%('+key+')s ' for key in where])   #wherestring for copy & done
    if 'rootidta' not in where:
        where['rootidta']=get_minta4query()
        wherestring = ' idta > %(rootidta)s AND ' + wherestring
    counter = 0 #count the number of dbta changed
    for row in query(u'''SELECT idta FROM ta WHERE '''+wherestring,where):
        counter += 1
        ta_from = OldTransaction(row['idta'])
        ta_from.update(statust = change)
    return counter

#**********************************************************/**
#*************************Database***********************/**
#**********************************************************/**
def set_database_lock():
    try:
        change(u'''INSERT INTO mutex (mutexk) VALUES (1)''')
    except: 
        return False
    return True

def remove_database_lock():
    change('''DELETE FROM mutex WHERE mutexk=1''')

def query(querystring,*args):
    ''' general query. yields rows from query '''
    cursor = botsglobal.db.cursor()
    cursor.execute(querystring,*args)
    results =  cursor.fetchall()
    cursor.close()
    for result in results:
        yield result
    
def change(querystring,*args):
    '''general inset/update. no return'''
    cursor = botsglobal.db.cursor()
    try:
        cursor.execute(querystring,*args)
    except: #IntegrityError from postgresql
        botsglobal.db.rollback()
        raise
    botsglobal.db.commit()
    cursor.close()

def unique(domein):
    ''' generate unique number within range domain.
        uses db to keep track of last generated number
        if domain not used before, initialize with 1.
    '''
    cursor = botsglobal.db.cursor()
    try:
        cursor.execute(u'''UPDATE uniek SET nummer=nummer+1 WHERE domein=%(domein)s''',{'domein':domein})
        cursor.execute(u'''SELECT nummer FROM uniek WHERE domein=%(domein)s''',{'domein':domein})
        nummer = cursor.fetchone()['nummer']
    except: # ???.DatabaseError; domein does not exist
        cursor.execute(u'''INSERT INTO uniek (domein) VALUES (%(domein)s)''',{'domein': domein})
        nummer = 1
    if nummer > sys.maxint-2:
        nummer = 1
        cursor.execute(u'''UPDATE uniek SET nummer=1 WHERE domein=%(domein)s''',{'domein':domein})
    botsglobal.db.commit()
    cursor.close()
    return nummer

def checkunique(domein, receivednumber):
    ''' to check of received number is sequential: value is compare with earlier received value.
        if domain not used before, initialize it . '1' is the first value expected.
    '''
    cursor = botsglobal.db.cursor()
    try:
        cursor.execute(u'''SELECT nummer FROM uniek WHERE domein=%(domein)s''',{'domein':domein})
        expectednumber = cursor.fetchone()['nummer'] + 1
    except: # ???.DatabaseError; domein does not exist
        cursor.execute(u'''INSERT INTO uniek (domein,nummer) VALUES (%(domein)s,0)''',{'domein': domein})
        expectednumber = 1
    if expectednumber == receivednumber:
        if expectednumber > sys.maxint-2:
            nummer = 1
        cursor.execute(u'''UPDATE uniek SET nummer=nummer+1 WHERE domein=%(domein)s''',{'domein':domein})
        terug = True
    else:
        terug = False
    botsglobal.db.commit()
    cursor.close()
    return terug

def keeptrackoflastretry(domein,newlastta):
    ''' keep track of last automaticretrycommunication/retry
        if domain not used before, initialize it . '1' is the first value expected.
    '''
    cursor = botsglobal.db.cursor()
    try:
        cursor.execute(u'''SELECT nummer FROM uniek WHERE domein=%(domein)s''',{'domein':domein})
        oldlastta = cursor.fetchone()['nummer']
    except: # ???.DatabaseError; domein does not exist
        cursor.execute(u'''INSERT INTO uniek (domein) VALUES (%(domein)s)''',{'domein': domein})
        oldlastta = 1
    cursor.execute(u'''UPDATE uniek SET nummer=%(nummer)s WHERE domein=%(domein)s''',{'domein':domein,'nummer':newlastta})
    botsglobal.db.commit()
    cursor.close()
    return oldlastta

#**********************************************************/**
#*************************Logging, Error handling********************/**
#**********************************************************/**
def sendbotserrorreport(subject,reporttext):
    if botsglobal.ini.getboolean('settings','sendreportiferror',False):
        from django.core.mail import mail_managers
        try:
            mail_managers(subject, reporttext)
        except:
            botsglobal.logger.debug(u'Error in sending error report: %s',txtexc())

def log_session(f):
    ''' used as decorator.
        The decorated functions are logged as processes.
        Errors in these functions are caught and logged.
    '''
    def wrapper(*args,**argv):
        try:
            ta_session = NewProcess(f.__name__)
        except:
            botsglobal.logger.exception(u'System error - no new session made')
            raise
        try:
            terug =f(*args,**argv)
        except:
            txt=txtexc()
            botsglobal.logger.debug(u'Error in process: %s',txt)
            ta_session.update(statust=ERROR,errortext=txt)
        else:
            ta_session.update(statust=DONE)
            return terug
    return wrapper

def txtexc():
    ''' Get text from last exception    '''
    if botsglobal.ini:
        if botsglobal.ini.getboolean('settings','debug',False):
            limit = None
        else:
            limit=0
    else:
        limit=0
    #problems with char set for some input data that are reported in traces....so always decode this; 
    terug = traceback.format_exc(limit).decode('utf-8','ignore')
    #~ botsglobal.logger.debug(u'exception %s',terug)
    if hasattr(botsglobal,'dbinfo') and botsglobal.dbinfo.drivername != 'sqlite':    #sqlite does not enforce strict lengths
        return terug[-1848:]    #filed isze is 2048; but more text can be prepended. 
    else:
        return terug

class ErrorProcess(NewTransaction):
    ''' Used in logging of errors in processes.
        20110828: used in communication.py
    '''
    def __init__(self,functionname='',errortext='',channeldict=None):
        fromchannel = tochannel = ''
        if channeldict:
            if channeldict['inorout'] == 'in':
                fromchannel = channeldict['idchannel']
            else:
                tochannel = channeldict['idchannel']
        super(ErrorProcess,self).__init__(filename=functionname,status=PROCESS,idroute=getrouteid(),statust=ERROR,errortext=errortext,fromchannel=fromchannel,tochannel=tochannel)

#**********************************************************/**
#*************************File handling os.path, imports etc***********************/**
#**********************************************************/**
def botsbaseimport(modulename):
    ''' Do a dynamic import.'''
    if modulename.startswith('.'):
        modulename = modulename[1:]
    try:
        #~ print 'import',modulename
        module = __import__(modulename)
        components = modulename.split('.')
        for comp in components[1:]:
            module = getattr(module, comp)
    except ImportError: #if module not found; often this is caught later on
        raise
    except:             #other errors
        txt=txtexc()
        raise ScriptImportError(_(u'Import file: "$module", error:\n$txt'),module=modulename,txt=txt)
    else:
        return module

def botsimport(soort,modulename):
    ''' to import modules from usersys.
        return: imported module, filename imported module; 
        if could not be found or error in module: raise
    '''
    try:    #__import__ is picky on the charset used. Might be different for different OS'es. So: test if charset is us-ascii
        modulename.encode('ascii')
    except UnicodeEncodeError:  #if not us-ascii, convert to punycode
        modulename = modulename.encode('punycode')
    modulepath = '.'.join((botsglobal.usersysimportpath,soort,modulename))  #assemble import string
    modulefile = join(botsglobal.usersysimportpath,soort,modulename)   #assemble abs filename for errortexts
    botsglobal.logger.debug(u'import file "%s".',modulefile)
    try:
        module = botsbaseimport(modulepath)
    except ImportError: #if module not found
        botsglobal.logger.debug(u'no import of file "%s".',modulefile)
        raise
    else:
        return module,modulefile

def join(*paths):
    '''Does does more as join.....
        - join the paths (compare os.path.join) 
        - if path is not absolute, interpretate this as relative from bots directory.
        - normalize'''
    return os.path.normpath(os.path.join(botsglobal.ini.get('directories','botspath'),*paths))

def dirshouldbethere(path):
    if path and not os.path.exists(path):
        os.makedirs(path)
        return True
    return False

def abspath(soort,filename):
    ''' get absolute path for internal files; path is a section in bots.ini '''
    directory = botsglobal.ini.get('directories',soort)
    return join(directory,filename)

def abspathdata(filename):
    ''' abspathdata if filename incl dir: return absolute path; else (only filename): return absolute path (datadir)'''
    if '/' in filename: #if filename already contains path
        return join(filename)
    else:
        directory = botsglobal.ini.get('directories','data')
        datasubdir = filename[:-3]
        if not datasubdir:
            datasubdir = '0'
        return join(directory,datasubdir,filename)

def opendata(filename,mode,charset=None,errors=None):
    ''' open internal data file. if no encoding specified: read file raw/binary.'''
    filename = abspathdata(filename)
    if 'w' in mode:
        dirshouldbethere(os.path.dirname(filename))
    if charset:
        return codecs.open(filename,mode,charset,errors)
    else:
        return open(filename,mode)

def readdata(filename,charset=None,errors=None):
    ''' read internal data file in memory using the right encoding or no encoding'''
    f = opendata(filename,'rb',charset,errors)
    content = f.read()
    f.close()
    return content

#**********************************************************/**
#*************************calling modules, programs***********************/**
#**********************************************************/**
def runscript(module,modulefile,functioninscript,**argv):
    ''' Execute user script. Functioninscript is supposed to be there; if not AttributeError is raised.
        Often is checked in advance if Functioninscript does exist.
    '''
    botsglobal.logger.debug(u'run user script "%s" in "%s".',functioninscript,modulefile)
    functiontorun = getattr(module, functioninscript)
    try:
        return functiontorun(**argv)
    except:
        txt=txtexc()
        raise ScriptError(_(u'Script file "$filename": "$txt".'),filename=modulefile,txt=txt)

def tryrunscript(module,modulefile,functioninscript,**argv):
    if module and hasattr(module,functioninscript):
        runscript(module,modulefile,functioninscript,**argv)
        return True
    return False

def runscriptyield(module,modulefile,functioninscript,**argv):
    functiontorun = getattr(module, functioninscript)
    try:
        for result in functiontorun(**argv):
            yield result
    except:
        txt=txtexc()
        raise ScriptError(_(u'Script file "$filename": "$txt".'),filename=modulefile,txt=txt)

def runexternprogram(*args):
    path = os.path.dirname(args[0])
    try:
        subprocess.call(list(args),cwd=path)
    except:
        txt=txtexc()
        raise OSError(_(u'error running extern program "%(program)s", error:\n%(error)s'%{'program':args,'error':txt}))

#**********************************************************/**
#***************###############  mdn   #############
#**********************************************************/**
def checkconfirmrules(confirmtype,**kwargs):
    terug = False       #boolean to return: ask a confirm of not?
    for confirmdict in query(u'''SELECT ruletype,idroute,idchannel_id as idchannel,frompartner_id as frompartner,topartner_id as topartner,editype,messagetype,negativerule
                        FROM    confirmrule
                        WHERE   active=%(active)s
                        AND     confirmtype=%(confirmtype)s
                        ORDER BY negativerule ASC
                        ''',
                        {'active':True,'confirmtype':confirmtype}):
        if confirmdict['ruletype']=='all':
            terug = not confirmdict['negativerule']
        elif confirmdict['ruletype']=='route':
            if 'idroute' in kwargs and confirmdict['idroute'] == kwargs['idroute']:
                terug = not confirmdict['negativerule']
        elif confirmdict['ruletype']=='channel':
            if 'idchannel' in kwargs and confirmdict['idchannel'] == kwargs['idchannel']:
                terug = not confirmdict['negativerule']
        elif confirmdict['ruletype']=='frompartner':
            if 'frompartner' in kwargs and confirmdict['frompartner'] == kwargs['frompartner']:
                terug = not confirmdict['negativerule']
        elif confirmdict['ruletype']=='topartner':
            if 'topartner' in kwargs and confirmdict['topartner'] == kwargs['topartner']:
                terug = not confirmdict['negativerule']
        elif confirmdict['ruletype']=='messagetype':
            if 'editype' in kwargs and confirmdict['editype'] == kwargs['editype'] and 'messagetype' in kwargs and confirmdict['messagetype'] == kwargs['messagetype']:
                terug = not confirmdict['negativerule']
    #~ print '>>>>>>>>>>>>', terug,confirmtype,kwargs
    return terug

#**********************************************************/**
#***************###############  codecs   #############
#**********************************************************/**
def getcodeccanonicalname(codecname):
    c = codecs.lookup(codecname)
    return c.name

def checkcodeciscompatible(charset1,charset2):
    ''' check if charset of edifile) is 'compatible' with charset of channel: OK; else: raise exception
    '''
    #some codecs are upward compatible (subsets); charsetcompatible is used to check if charsets are upward compatibel with each other.
    #some charset are 1 byte (ascii, ISO-8859-*). others are more bytes (UTF-16, utf-32. UTF-8 is more bytes, but is ascii compatible.
    charsetcompatible = {
        'unoa':['unob','ascii','utf-8','iso8859-1','cp1252','iso8859-15'],
        'unob':['ascii','utf-8','iso8859-1','cp1252','iso8859-15'],
        'ascii':['utf-8','iso8859-1','cp1252','iso8859-15'],
        }
    charset_edifile = getcodeccanonicalname(charset1)
    charset_channel = getcodeccanonicalname(charset2)
    if charset_channel == charset_edifile:
        return True
    if charset_edifile in charsetcompatible and charset_channel in charsetcompatible[charset_edifile]:
        return True
    raise CommunicationOutError(_(u'Charset "$charset2" for channel not matching with charset "$charset1" for edi-file.'),charset1=charset1,charset2=charset2)

#**********************************************************/**
#***************###############  misc.   #############
#**********************************************************/**
class Uri(object):
    ''' generate uri from parts. '''
    def __init__(self,**kw):
        self.uriparts = dict(scheme='',username='',password='',host='',port='',path='',parameters='',filename='',query={},fragment='')
        self.uriparts.update(**kw)
    def update(self,**kw):
        self.uriparts.update(kw)
        return self.uri
    @property   #the getter
    def uri(self):
        if not self.uriparts['scheme']:
            raise BotsError(_(u'No scheme in uri.'))
        #assemble complete host name
        fullhost = ''
        if self.uriparts['username']:   #always use both?
            fullhost += self.uriparts['username'] + '@'
        if self.uriparts['host']:
            fullhost += self.uriparts['host']
        if self.uriparts['port']:
            fullhost += ':' + str(self.uriparts['port'])
        #assemble complete path
        if self.uriparts['path'].strip().endswith('/'):
            fullpath = self.uriparts['path'] + self.uriparts['filename']
        else:
            fullpath = self.uriparts['path'] + '/' + self.uriparts['filename']
        if fullpath.endswith('/'):
            fullpath = fullpath[:-1]
            
        _uri = urlparse.urlunparse((self.uriparts['scheme'],fullhost,fullpath,self.uriparts['parameters'],urllib.urlencode(self.uriparts['query']),self.uriparts['fragment']))
        if not _uri:
            raise BotsError(_(u'Uri is empty.'))
        return _uri
    
def settimeout(milliseconds):
    socket.setdefaulttimeout(milliseconds)    #set a time-out for TCP-IP connections

def countunripchars(value,delchars):
	return len([c for c in value if c not in delchars])

def updateunlessset(updatedict,fromdict):
    for key, value in fromdict.items():
        if key not in updatedict:
            updatedict[key]=value

#**********************************************************/**
#**************  Exception classes ***************************
#**********************************************************/**
class BotsError(Exception):
    def __init__(self, msg,**kwargs):
        self.msg = msg
        self.kwargs = kwargs
    def __str__(self):
        s = string.Template(self.msg).safe_substitute(self.kwargs)
        return s.encode(u'utf-8',u'ignore')
class CodeConversionError(BotsError):
    pass
class CommunicationError(BotsError):
    pass
class CommunicationInError(BotsError):
    pass
class CommunicationOutError(BotsError):
    pass
class EanError(BotsError):
    pass
class GrammarError(BotsError):            #grammar.py
    pass
class InMessageError(BotsError):
    pass
class InMessageFieldError(BotsError):
    pass
class LockedFileError(BotsError):
    pass
class MessageError(BotsError):
    pass
class MappingRootError(BotsError):
    pass
class MappingFormatError(BotsError):            #mpath is not valid; mapth will mostly come from mapping-script
    pass
class OutMessageError(BotsError):
    pass
class PanicError(BotsError):
    pass
class PersistError(BotsError):
    pass
class PluginError(BotsError):
    pass
class ScriptImportError(BotsError):   #can not find script; not for errors in a script
    pass
class ScriptError(BotsError):   #runtime errors in a script
    pass
class TraceError(BotsError):
    pass
class TraceNotPickedUpError(BotsError):
    pass
class TranslationNotFoundError(BotsError):
    pass
