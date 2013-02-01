''' Base library for bots. Botslib should not import code from other Bots-modules.'''
import sys
import os
import time
import codecs
import traceback
import socket
import string
import urlparse
import urllib
import platform
import django
from django.utils.translation import ugettext as _
#Bots-modules (no code)
from botsconfig import *    #constants
import botsglobal           #globals

def botsinfo():
    return [
            (_(u'served at port'),botsglobal.ini.getint('webserver','port',8080)),
            (_(u'platform'),platform.platform()),
            (_(u'machine'),platform.machine()),
            (_(u'python version'),platform.python_version),
            (_(u'django version'),django.VERSION),
            (_(u'bots version'),botsglobal.version),
            (_(u'bots installation path'),botsglobal.ini.get('directories','botspath')),
            (_(u'config path'),botsglobal.ini.get('directories','config')),
            (_(u'botssys path'),botsglobal.ini.get('directories','botssys')),
            (_(u'usersys path'),botsglobal.ini.get('directories','usersysabs')),
            (u'DATABASE_ENGINE',botsglobal.settings.DATABASES['default']['ENGINE']),
            (u'DATABASE_NAME',botsglobal.settings.DATABASES['default']['NAME']),
            (u'DATABASE_USER',botsglobal.settings.DATABASES['default']['USER']),
            (u'DATABASE_HOST',botsglobal.settings.DATABASES['default']['HOST']),
            (u'DATABASE_PORT',botsglobal.settings.DATABASES['default']['PORT']),
            (u'DATABASE_OPTIONS',botsglobal.settings.DATABASES['default']['OPTIONS']),
            ]
#**********************************************************/**
#**************getters/setters for some globals***********************/**
#**********************************************************/**
def get_minta4query():
    ''' get the first idta for queries etc.
        botsglobal.minta4query is set in router.py
    '''
    return botsglobal.minta4query

def setrouteid(routeid):
    botsglobal.routeid = routeid

def getrouteid():
    return botsglobal.routeid

#**********************************************************/**
#***************** class  Transaction *********************/**
#**********************************************************/**
class _Transaction(object):
    ''' abstract class for db-ta.
        This class is used for communication with db-ta.
    '''
    #filtering values for db handling to avoid unknown fields in db.
    filterlist = ('statust','status','divtext','parent','child','script','frompartner','topartner','fromchannel','tochannel','editype','messagetype','merge',
                'testindicator','reference','frommail','tomail','contenttype','errortext','filename','charset','alt','idroute','nrmessages','retransmit',
                'confirmasked','confirmed','confirmtype','confirmidta','envelope','botskey','cc','rsrv1','filesize','numberofresends')
    processlist = [0]  #stack for bots-processes. last one is the current process; starts with 1 element in list: root

    def update(self,**ta_info):
        ''' Updates db-ta with named-parameters/dict.
            Use a filter to update only valid fields in db-ta
        '''
        setstring = ','.join([key+'=%('+key+')s' for key in ta_info if key in self.filterlist])
        if not setstring:   #nothing to update
            return
        ta_info['selfid'] = self.idta
        changeq(u'''UPDATE ta
                    SET '''+setstring+ '''
                    WHERE idta=%(selfid)s''',
                    ta_info)

    def delete(self):
        '''Deletes current transaction '''
        changeq(u'''DELETE FROM ta
                    WHERE idta=%(idta)s''',
                    {'idta':self.idta})

    def deletechildren(self):
        self.deleteonlychildren_core(self.idta)
        
    def deleteonlychildren_core(self,idta):
        for row in query(u'''SELECT idta 
                            FROM ta
                            WHERE idta>%(rootidta)s
                            AND parent=%(idta)s''',
                            {'idta':idta,'rootidta':get_minta4query()}):
            self.deleteonlychildren_core(row['idta'])
            changeq(u'''DELETE FROM ta
                        WHERE idta=%(idta)s''',
                        {'idta':row['idta' ]})
        
    def syn(self,*ta_vars):
        '''access of attributes of transaction as ta.fromid, ta.filename etc'''
        varsstring = ','.join(ta_vars)
        for row in query(u'''SELECT ''' + varsstring + '''
                              FROM ta
                              WHERE idta=%(idta)s''',
                              {'idta':self.idta}):
            self.__dict__.update(dict(row))

    def synall(self):
        '''access of attributes of transaction as ta.fromid, ta.filename etc'''
        self.syn(*self.filterlist)

    def copyta(self,status,**ta_info):
        ''' copy old transaction, return new transaction.
            parameters for new transaction are in ta_info (new transaction is updated with these values).
        '''
        script = _Transaction.processlist[-1]
        newidta = insertta(u'''INSERT INTO ta (script,  status,     parent,frompartner,topartner,fromchannel,tochannel,editype,messagetype,alt,merge,testindicator,reference,frommail,tomail,charset,contenttype,filename,idroute,nrmessages,botskey)
                                SELECT %(script)s,%(newstatus)s,idta,frompartner,topartner,fromchannel,tochannel,editype,messagetype,alt,merge,testindicator,reference,frommail,tomail,charset,contenttype,filename,idroute,nrmessages,botskey
                                FROM ta
                                WHERE idta=%(idta)s''',
                                {'idta':self.idta,'script':script,'newstatus':status})
        newta = OldTransaction(newidta)
        newta.update(**ta_info)
        return newta


class OldTransaction(_Transaction):
    ''' Resurrect old transaction '''
    def __init__(self,idta):
        self.idta = idta


class NewTransaction(_Transaction):
    ''' Generate new transaction. '''
    def __init__(self,**ta_info):
        updatedict = dict([(key,value) for key,value in ta_info.items() if key in self.filterlist])     #filter ta_info
        updatedict['script'] = self.processlist[-1]
        namesstring = ','.join([key for key in updatedict])
        varsstring = ','.join(['%('+key+')s' for key in updatedict])
        self.idta = insertta(u'''INSERT INTO ta (''' + namesstring + ''')
                                 VALUES   (''' + varsstring + ''')''',
                                updatedict)


class NewProcess(NewTransaction):
    ''' Create a new process (which is very much like a transaction).
        Used in logging of processes. 
        Each process is placed on stack processlist
    '''
    def __init__(self,functionname=''):
        super(NewProcess,self).__init__(filename=functionname,status=PROCESS,idroute=getrouteid())
        self.processlist.append(self.idta)

    def update(self,**ta_info):
        ''' update process, delete from process-stack. '''
        super(NewProcess,self).update(**ta_info)
        self.processlist.pop()


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
            taparent = OldTransaction(idta=idta)
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
                                 FROM ta
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
        where['rootidta'] = get_minta4query()
        wherestring = ' idta > %(rootidta)s AND ' + wherestring
    if 'statust' not in where:  #by default: look only for statust is OK
        where['statust'] = OK
        wherestring += ' AND statust = %(statust)s '
    if 'statust' not in change: #by default: new ta is OK
        change['statust'] = OK
    counter = 0 #count the number of dbta changed
    for row in query(u'''SELECT idta FROM ta WHERE '''+wherestring,where):
        counter += 1
        ta_from = OldTransaction(row['idta'])
        ta_from.copyta(**change)     #make new ta from ta_from, using parameters from change
        ta_from.update(statust=DONE)    #update 'old' ta
    return counter

def addinfo(change,where):
    ''' changes ta's; ta's are copyed to new ta; the status is updated.
        change-dict: values to change; where-dict: selection.'''
    wherestring = ' AND '.join([key+'=%('+key+')s ' for key in where])   #wherestring for copy & done
    return addinfocore(change=change,where=where,wherestring=wherestring)

def updateinfo(change,where):
    ''' update info in ta's; not to be used for status change (use addinfo)
        where-dict selects ta's, change-dict sets values;
    '''
    if 'statust' not in where:
        where['statust'] = OK
    wherestring = ' AND '.join([key+'=%('+key+')s ' for key in where])   #wherestring for copy & done
    where['rootidta'] = get_minta4query()
    wherestring = ' idta > %(rootidta)s AND ' + wherestring
    #change-dict: discard empty values. Change keys: this is needed because same keys can be in where-dict
    change = [(key,value) for key,value in change.items() if value]
    changestring = ','.join([key+'=%(change_'+key+')s' for key,value in change])
    if not changestring:
        return
    where.update([('change_'+key,value) for key,value in change])
    changeq(u'''UPDATE ta SET '''+changestring+ ''' WHERE '''+wherestring+ ''' ''',where)

def changestatustinfo(change,where):
    ''' update statust in ta.
        where-dict selects db-ta's, change is the new statust;
    '''
    updateinfo({'statust':change},where)

#**********************************************************/**
#*************************Database***********************/**
#**********************************************************/**
def set_database_lock():
    try:
        changeq(u'''INSERT INTO mutex (mutexk) VALUES (1)''')
    except:
        return False
    return True

def remove_database_lock():
    changeq('''DELETE FROM mutex WHERE mutexk=1''')

def query(querystring,*args):
    ''' general query. yields rows from query '''
    cursor = botsglobal.db.cursor()
    cursor.execute(querystring,*args)
    results =  cursor.fetchall()
    cursor.close()
    for result in results:
        yield result

def changeq(querystring,*args):
    '''general inset/update. no return'''
    cursor = botsglobal.db.cursor()
    try:
        cursor.execute(querystring,*args)
    except:
        botsglobal.db.rollback()    #rollback is needed for postgreSQL as this is also used by user scripts (eg via persist)
        raise
    botsglobal.db.commit()
    cursor.close()

def insertta(querystring,*args):
    ''' insert ta
        from insert get back the idta; this is different with postgrSQL.
    '''
    cursor = botsglobal.db.cursor()
    cursor.execute(querystring,*args)
    newidta = cursor.lastrowid
    if not newidta:   #if botsglobal.settings.DATABASE_ENGINE ==
        cursor.execute('''SELECT lastval() as idta''')
        newidta = cursor.fetchone()['idta']
    botsglobal.db.commit()
    cursor.close()
    return newidta

def unique_runcounter(domain):
    ''' generate unique counter within range domain during one run of bots.
        if domain not used before, initialize as 1; for each subsequent call this is incremented with 1
        usage example:
        unh_reference = unique_runcounter(<messagetype>_<topartner>)
    '''
    domain += 'bots_1_8_4_9_6'  #avoid using/mixing other values in botsglobal
    try:
        terug = 1 + getattr(botsglobal,domain)
    except AttributeError:
        terug = 1
    finally:
        setattr(botsglobal,domain,terug)
    return terug

def unique(domein):
    ''' generate unique number within range domain.
        uses db to keep track of last generated number
        if domain not used before, initialize with 1.
    '''
    nummer = uniquecore(domein)
    if nummer > sys.maxint-2:
        nummer = 1
        changeq(u'''UPDATE uniek SET nummer=%(nummer)s WHERE domein=%(domein)s''',{'domein':domein,'nummer':nummer})
    return nummer

def uniquecore(domein,updatewith=None):
    if botsglobal.ini.getboolean('acceptance','runacceptancetest',False):
        return unique_runcounter(domein)
    else:
        cursor = botsglobal.db.cursor()
        try:
            cursor.execute(u'''SELECT nummer FROM uniek WHERE domein=%(domein)s''',{'domein':domein})
            nummer = cursor.fetchone()['nummer']
        except TypeError: #if domein does not exist, fetchone returns None, so TypeError
            cursor.execute(u'''INSERT INTO uniek (domein,nummer) VALUES (%(domein)s,0)''',{'domein': domein})
            nummer = 0
        if updatewith is None:
            nummer += 1
            updatewith = nummer
        cursor.execute(u'''UPDATE uniek SET nummer=%(nummer)s WHERE domein=%(domein)s''',{'domein':domein,'nummer':updatewith})
        botsglobal.db.commit()
        cursor.close()
        return nummer
    
def checkunique(domein, receivednumber):
    ''' to check if received number is sequential: value is compare with earlier received value.
        if domain not used before, initialize it . '1' is the first value expected.
    '''
    earlierreceivednumber = uniquecore(domein,updatewith=receivednumber)
    if earlierreceivednumber+1  == receivednumber:
        return True
    else:
        #set back number
        if botsglobal.ini.getboolean('acceptance','runacceptancetest',False):
            return False     #TODO: set the unique_runcounter
        else:
            changeq(u'''UPDATE uniek SET nummer=%(nummer)s WHERE domein=%(domein)s''',{'domein':domein,'nummer':earlierreceivednumber})
            return False

#**********************************************************/**
#*************************Logging, Error handling********************/**
#**********************************************************/**
def sendbotserrorreport(subject,reporttext):
    ''' Send an email in case of errors or problems with bots-engine.
        Email is send to MANAGERS in config/settings.py.
        Email parameters are in config/settings.py (EMAIL_HOST, etc).
    '''
    if botsglobal.ini.getboolean('settings','sendreportiferror',False) and not botsglobal.ini.getboolean('acceptance','runacceptancetest',False):
        from django.core.mail import mail_managers
        try:
            mail_managers(subject, reporttext)
        except Exception,msg:
            botsglobal.logger.debug(u'Error in sending error report: %s',msg)

def sendbotsemail(partner,subject,reporttext):
    ''' Send a simple email message to any bots partner.
        Mail is sent to all To: and cc: addresses for the partner (but send_mail does not support cc).
        Email parameters are in config/settings.py (EMAIL_HOST, etc).
    '''
    from django.core.mail import send_mail
    for row in query('''SELECT mail,cc FROM partner WHERE idpartner=%(partner)s''',{'partner':partner}):
        if row['mail']:
            recipient_list = row['mail'].split(',') + row['cc'].split(',')
            try:
                send_mail(subject, reporttext, botsglobal.settings.SERVER_EMAIL, recipient_list)
            except Exception,msg:
                botsglobal.logger.warning(u'Error sending email: %s',msg)

def log_session(func):
    ''' used as decorator.
        The decorated functions are logged as processes.
        Errors in these functions are caught and logged.
    '''
    def wrapper(*args,**argv):
        try:
            ta_process = NewProcess(func.__name__)
        except:
            botsglobal.logger.exception(u'System error - no new process made')
            raise
        try:
            terug = func(*args,**argv)
        except:
            txt = txtexc()
            botsglobal.logger.debug(u'Error in process: %s',txt)
            ta_process.update(statust=ERROR,errortext=txt)
        else:
            ta_process.update(statust=DONE)
            return terug
    return wrapper

def txtexc():
    ''' Process last exception to get (safe) errortext.
    '''
    if botsglobal.ini and botsglobal.ini.getboolean('settings','debug',False):
        return traceback.format_exc(limit=None).decode('utf-8','ignore')    #problems with char set for some input data, so always decode this.
    else:
        terug = traceback.format_exc(limit=0).decode('utf-8','ignore')    #problems with char set for some input data, so always decode this.
        return terug.replace(u'Traceback (most recent call last):\n',u'')

class ErrorProcess(NewTransaction):
    ''' Used in logging of errors in processes: communication.py to indicate errors in receiving files (files have not been received)
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
#*************************import ***********************/**
#**********************************************************/**
def isa_direct_importerror():
    ''' check if module itself is not there, or if there is an import error in the module.
        this avoid hard-to-find errors/problems.
    '''
    exc_type, exc_value, exc_traceback = sys.exc_info()
    #test if direct or indirect import error
    tracebacklist = traceback.extract_tb(exc_traceback,limit=2)
    if tracebacklist[-1][2] == u'botsbaseimport':
        return True
    return False
    
def botsbaseimport(modulename):
    ''' Do a dynamic import.
        Errors/exceptions are handled in calling functions.
    '''
    if modulename.startswith('.'):
        modulename = modulename[1:]
    module = __import__(modulename)
    components = modulename.split('.')
    for comp in components[1:]:
        module = getattr(module, comp)
    return module

def botsimport(soort,modulename):
    ''' import modules from usersys.
        return: imported module, filename imported module;
        if could not be found or error in module: raise
    '''
    try:    #__import__ is picky on the charset used. Might be different for different OS'es. So: test if charset is us-ascii
        modulename.encode('ascii')
    except UnicodeEncodeError:  #if not us-ascii, convert to punycode
        modulename = modulename.encode('punycode')
    if soort:
        lijst = (botsglobal.usersysimportpath,soort,modulename)
    else:
        lijst = (botsglobal.usersysimportpath,modulename)
    modulepath = '.'.join(lijst)  #assemble import string
    modulefile = join(botsglobal.usersysimportpath,soort,modulename)   #assemble abs filename for errortexts
    try:
        module = botsbaseimport(modulepath)
    except ImportError: #if module not found
        if isa_direct_importerror():
            botsglobal.logger.debug(u'no import of "%s".',modulefile)
            raise
        else:
            txt = txtexc()
            raise ScriptImportError(_(u'import error in "$module", error:\n$txt'),module=modulefile,txt=txt)
    except:             #other errors
        txt = txtexc()
        raise ScriptImportError(_(u'Error in "$module", error:\n$txt'),module=modulefile,txt=txt)
    else:
        botsglobal.logger.debug(u'import "%s".',modulefile)
        return module,modulefile
#**********************************************************/**
#*************************File handling os.path etc***********************/**
#**********************************************************/**
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

def deldata(filename):
    ''' delete internal data file.'''
    filename = abspathdata(filename)
    try:
        os.remove(filename)
    except:
        print 'not deleted', filename
        pass

def opendata(filename,mode,charset=None,errors='strict'):
    ''' open internal data file. if no encoding specified: read file raw/binary.'''
    filename = abspathdata(filename)
    if 'w' in mode:
        dirshouldbethere(os.path.dirname(filename))
    if charset:
        return codecs.open(filename,mode,charset,errors)
    else:
        return open(filename,mode)

def readdata(filename,charset=None,errors='strict'):
    ''' read internal data file in memory using the right encoding or no encoding'''
    filehandler = opendata(filename,'rb',charset,errors)
    content = filehandler.read()
    filehandler.close()
    return content

#**********************************************************/**
#*************************calling modules, programs***********************/**
#**********************************************************/**
def runscript(module,modulefile,functioninscript,**argv):
    ''' Execute userscript. Functioninscript is supposed to be there; if not AttributeError is raised.
        Often is checked in advance if Functioninscript does exist.
    '''
    botsglobal.logger.debug(u'run userscript "%s" in "%s".',functioninscript,modulefile)
    functiontorun = getattr(module, functioninscript)
    try:
        return functiontorun(**argv)
    except:
        txt = txtexc()
        raise ScriptError(_(u'Userscript "$filename": "$txt".'),filename=modulefile,txt=txt)

def tryrunscript(module,modulefile,functioninscript,**argv):
    if module and hasattr(module,functioninscript):
        runscript(module,modulefile,functioninscript,**argv)
        return True
    return False

def runscriptyield(module,modulefile,functioninscript,**argv):
    botsglobal.logger.debug(u'run userscript "%s" in "%s".',functioninscript,modulefile)
    functiontorun = getattr(module, functioninscript)
    try:
        for result in functiontorun(**argv):
            yield result
    except:
        txt = txtexc()
        raise ScriptError(_(u'Script file "$filename": "$txt".'),filename=modulefile,txt=txt)

#**********************************************************/**
#***************###############  misc.   #############
#**********************************************************/**
def strftime(format):
    if botsglobal.ini.getboolean('acceptance','runacceptancetest',False):
        return time.strftime(format,time.strptime("2013-01-23 01:23:45", "%Y-%m-%d %H:%M:%S"))    #if acceptance test use fixed date/time
    else:
        return time.strftime(format)
    
    
def lookup_translation(frommessagetype,fromeditype,alt,frompartner,topartner):
    ''' lookup the translation: frommessagetype,fromeditype,alt,frompartner,topartner -> mappingscript, tomessagetype, toeditype
    '''
    for row2 in query(u'''SELECT tscript,tomessagetype,toeditype
                            FROM translate
                            WHERE frommessagetype = %(frommessagetype)s
                            AND fromeditype = %(fromeditype)s
                            AND active=%(booll)s
                            AND alt=%(alt)s
                            AND (frompartner_id IS NULL OR frompartner_id=%(frompartner)s OR frompartner_id in (SELECT to_partner_id
                                                                                                                    FROM partnergroup
                                                                                                                    WHERE from_partner_id=%(frompartner)s ))
                            AND (topartner_id IS NULL OR topartner_id=%(topartner)s OR topartner_id in (SELECT to_partner_id
                                                                                                            FROM partnergroup
                                                                                                            WHERE from_partner_id=%(topartner)s ))
                            ORDER BY alt DESC,
                                     CASE WHEN frompartner_id IS NULL THEN 1 ELSE 0 END, frompartner_id ,
                                     CASE WHEN topartner_id IS NULL THEN 1 ELSE 0 END, topartner_id ''',
                            {'frommessagetype':frommessagetype,
                             'fromeditype':fromeditype,
                             'alt':alt,
                             'frompartner':frompartner,
                             'topartner':topartner,
                            'booll':True}):
        return row2['tscript'],row2['toeditype'],row2['tomessagetype']
        #translation is found; only the first one is used - this is what the ORDER BY in the query takes care of
    else:       #no translation found in translate table
        return None,None,None


def check_if_other_engine_is_running():
    ''' bots-engine always connects to 127.0.0.1 port 28081 (or port as set in bots.ini).
        this  is a good way of detecting that another bots-engien is still running.
        problem is avoided anyway if using jobqueueserver.
    ''' 
    try:
        engine_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port = botsglobal.ini.getint('settings','port',28081)
        engine_socket.bind(('127.0.0.1', port))
    except socket.error:
        engine_socket.close()
        raise
    else:
        return engine_socket

def globalcheckconfirmrules(confirmtype):
    ''' global check if confirmrules with this confirmtype is uberhaupt used. 
    ''' 
    for confirmdict in query(u'''SELECT confirmtype
                        FROM confirmrule
                        WHERE active=%(active)s
                        AND confirmtype=%(confirmtype)s
                        ''',
                        {'active':True,'confirmtype':confirmtype}):
        return True
    return False

def checkconfirmrules(confirmtype,**kwargs):
    confirm = False       #boolean to return: confirm of not?
    #confirmrules are evaluated one by one; first the positive rules, than the negative rules.
    #this make it possible to include first, than exclude. Eg: send for 'all', than exclude certain partners.
    for confirmdict in query(u'''SELECT ruletype,idroute,idchannel_id as idchannel,frompartner_id as frompartner,topartner_id as topartner,messagetype,negativerule
                        FROM confirmrule
                        WHERE active=%(active)s
                        AND confirmtype=%(confirmtype)s
                        ORDER BY negativerule ASC
                        ''',
                        {'active':True,'confirmtype':confirmtype}):
        if confirmdict['ruletype'] == 'all':
            confirm = not confirmdict['negativerule']
        elif confirmdict['ruletype'] == 'route':
            if 'idroute' in kwargs and confirmdict['idroute'] == kwargs['idroute']:
                confirm = not confirmdict['negativerule']
        elif confirmdict['ruletype'] == 'channel':
            if 'idchannel' in kwargs and confirmdict['idchannel'] == kwargs['idchannel']:
                confirm = not confirmdict['negativerule']
        elif confirmdict['ruletype'] == 'frompartner':
            if 'frompartner' in kwargs and confirmdict['frompartner'] == kwargs['frompartner']:
                confirm = not confirmdict['negativerule']
        elif confirmdict['ruletype'] == 'topartner':
            if 'topartner' in kwargs and confirmdict['topartner'] == kwargs['topartner']:
                confirm = not confirmdict['negativerule']
        elif confirmdict['ruletype'] == 'messagetype':
            if 'messagetype' in kwargs and confirmdict['messagetype'] == kwargs['messagetype']:
                confirm = not confirmdict['negativerule']
        #~ print '>>>>>>>>>>>>', confirm,confirmtype,kwargs,confirmdict
    return confirm

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
            updatedict[key] = value

#**********************************************************/**
#**************  Exception classes ***************************
#**********************************************************/**
class BotsError(Exception):
    def __init__(self, msg,**kwargs):
        self.msg = msg
        self.kwargs = kwargs
    def __str__(self):
        terug = string.Template(self.msg).safe_substitute(self.kwargs)
        return terug.encode(u'utf-8',u'ignore')
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
class GrammarError(BotsError):         #grammar.py
    pass
class InMessageError(BotsError):
    pass
class LockedFileError(BotsError):
    pass
class MessageError(BotsError):
    pass
class MappingRootError(BotsError):
    pass
class MappingFormatError(BotsError):   #mpath is not valid; mapth will mostly come from mappingscript
    pass
class OutMessageError(BotsError):
    pass
class PanicError(BotsError):
    pass
class PersistError(BotsError):
    pass
class PluginError(BotsError):
    pass
class ScriptImportError(BotsError):    #can not find userscript; not for errors in a userscript
    pass
class ScriptError(BotsError):          #runtime errors in a userscript
    pass
class TraceError(BotsError):
    pass
class TranslationNotFoundError(BotsError):
    pass
