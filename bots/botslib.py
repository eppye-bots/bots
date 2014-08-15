''' Base library for bots. Botslib should not import code from other Bots-modules.'''
import sys
import os
import time
import codecs
import traceback
import socket
import urlparse
import urllib
import platform
import collections
import django
try:
    import importlib
except:
    import bots_importlib as importlib
from django.utils.translation import ugettext as _
#Bots-modules (no code)
from botsconfig import *    #constants
import botsglobal           #globals

#**********************************************************/**
#**************getters/setters for some globals***********************/**
#**********************************************************/**
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
                'confirmasked','confirmed','confirmtype','confirmidta','envelope','botskey','cc','rsrv1','filesize','numberofresends','rsrv3')
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
                            WHERE parent=%(idta)s''',
                            {'idta':idta}):
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
        newidta = insertta(u'''INSERT INTO ta (script,  status,     parent,frompartner,topartner,fromchannel,tochannel,editype,messagetype,alt,merge,testindicator,reference,frommail,tomail,charset,contenttype,filename,idroute,nrmessages,botskey,envelope,rsrv3)
                                SELECT %(script)s,%(newstatus)s,idta,frompartner,topartner,fromchannel,tochannel,editype,messagetype,alt,merge,testindicator,reference,frommail,tomail,charset,contenttype,filename,idroute,nrmessages,botskey,envelope,rsrv3
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
        updatedict = dict((key,value) for key,value in ta_info.iteritems() if key in self.filterlist)     #filter ta_info
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


#**********************************************************/**
#*************************Database***********************/**
#**********************************************************/**
def addinfocore(change,where,wherestring):
    ''' core function for add/changes information in db-ta's.
    '''
    wherestring = ' WHERE idta > %(rootidta)s AND ' + wherestring
    counter = 0 #count the number of dbta changed
    for row in query(u'''SELECT idta FROM ta '''+wherestring,where):
        counter += 1
        ta_from = OldTransaction(row['idta'])
        ta_from.copyta(**change)     #make new ta from ta_from, using parameters from change
        ta_from.update(statust=DONE)    #update 'old' ta
    return counter
    
def addinfo(change,where):
    ''' change ta's to new phase: ta's are copied to new ta.
        returns the number of db-ta that have been changed.
        change (dict): values to change.
        where (dict): selection.
    '''
    if 'rootidta' not in where:
        where['rootidta'] = botsglobal.currentrun.get_minta4query()
    if 'statust' not in where:  #by default: look only for statust is OK
        where['statust'] = OK
    if 'statust' not in change: #by default: new ta is OK
        change['statust'] = OK
    wherestring = ' AND '.join([key+'=%('+key+')s ' for key in where if key != 'rootidta'])   #wherestring; does not use rootidta
    return addinfocore(change=change,where=where,wherestring=wherestring)

def updateinfocore(change,where,wherestring=''):
    ''' update info in ta's.
        where (dict) selects ta's,
        change (dict) sets values;
    '''
    wherestring = ' WHERE idta > %(rootidta)s AND ' + wherestring
    #change-dict: discard empty values. Change keys: this is needed because same keys can be in where-dict
    change2 = [(key,value) for key,value in change.iteritems() if value]
    if not change2:
        return
    changestring = ','.join([key+'=%(change_'+key+')s' for key,value in change2])
    where.update([('change_'+key,value) for key,value in change2])
    return changeq(u'''UPDATE ta SET ''' + changestring + wherestring,where)

def updateinfo(change,where):
    ''' update ta's.
        returns the number of db-ta that have been changed.
        change (dict): values to change.
        where (dict): selection.
    '''
    if 'rootidta' not in where:
        where['rootidta'] = botsglobal.currentrun.get_minta4query()
    if 'statust' not in where:  #by default: look only for statust is OK
        where['statust'] = OK
    if 'statust' not in change: #by default: new ta is OK
        change['statust'] = OK
    wherestring = ' AND '.join([key+'=%('+key+')s ' for key in where if key != 'rootidta'])   #wherestring for copy & done
    return updateinfocore(change=change,where=where,wherestring=wherestring)

def changestatustinfo(change,where):
    return updateinfo({'statust':change},where)

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
    terug = cursor.rowcount
    cursor.close()
    return terug

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

def unique_runcounter(domain,updatewith=None):
    ''' as unique, but per run of bots-engine.
    '''
    domain += 'bots_1_8_4_9_6'  #avoid using/mixing other values in botsglobal
    domain = domain.encode('unicode-escape')
    nummer = getattr(botsglobal,domain,0)
    if updatewith is None:
        nummer += 1
        updatewith = nummer
        if updatewith > sys.maxint-2:
            updatewith = 0
    setattr(botsglobal,domain,updatewith)
    return nummer

def unique(domein,updatewith=None):
    ''' generate unique number within range domain. Uses db to keep track of last generated number.
        3 use cases:
        - in acceptance: use unique_runcounter
        - if updatewith is not None: return current number, update database with updatewith
        - if updatewith is None: return current number plus 1; update database with  current number plus 1
            if domain not used before, initialize with 1.
    '''
    if botsglobal.ini.getboolean('acceptance','runacceptancetest',False):
        return unique_runcounter(domein)
    else:
        cursor = botsglobal.db.cursor()
        try:
            cursor.execute(u'''SELECT nummer FROM uniek WHERE domein=%(domein)s''',{'domein':domein})
            nummer = cursor.fetchone()['nummer']
            if updatewith is None:
                nummer += 1
                updatewith = nummer
                if updatewith > sys.maxint-2:
                    updatewith = 0
            cursor.execute(u'''UPDATE uniek SET nummer=%(nummer)s WHERE domein=%(domein)s''',{'domein':domein,'nummer':updatewith})
        except TypeError: #if domein does not exist, cursor.fetchone returns None, so TypeError
            cursor.execute(u'''INSERT INTO uniek (domein,nummer) VALUES (%(domein)s,1)''',{'domein': domein})
            nummer = 1
        botsglobal.db.commit()
        cursor.close()
        return nummer

def checkunique(domein, receivednumber):
    ''' to check if received number is sequential: value is compare with new generated number.
        if domain not used before, initialize it . '1' is the first value expected.
    '''
    newnumber = unique(domein)
    if newnumber  == receivednumber:
        return True
    else:
        #received number is not OK. Reset counter in database to previous value.  
        if botsglobal.ini.getboolean('acceptance','runacceptancetest',False):
            return False     #TODO: set the unique_runcounter
        else:
            changeq(u'''UPDATE uniek SET nummer=%(nummer)s WHERE domein=%(domein)s''',{'domein':domein,'nummer':newnumber-1})
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
        except Exception as msg:
            botsglobal.logger.warning(u'Error in sending error report: %(msg)s',{'msg':msg})

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
            except Exception as msg:
                botsglobal.logger.warning(u'Error sending email: %(msg)s',{'msg':msg})

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
            botsglobal.logger.debug(u'Error in process: %(txt)s',{'txt':txt})
            ta_process.update(statust=ERROR,errortext=txt)
        else:
            ta_process.update(statust=DONE)
            return terug
    return wrapper

def txtexc(mention_exception_type=True):
    ''' Process last exception, get an errortext.
        Errortext should be valid unicode.
    '''
    if botsglobal.ini and botsglobal.ini.getboolean('settings','debug',False):
        return safe_unicode(traceback.format_exc(limit=None))
    else:
        terug = safe_unicode(traceback.format_exc(limit=0))
        terug = terug.replace(u'Traceback (most recent call last):\n',u'')
        if not mention_exception_type:
            terug = terug.partition(': ')[2]
        return terug

def safe_unicode(value):
    ''' For errors: return best possible unicode...should never lead to errors.
    '''
    try:
        if isinstance(value, unicode):      #is already unicode, just return
            return value            
        elif isinstance(value, str):        #string/bytecode, encoding unknown.   
            for charset in ['utf_8','latin_1']:
                try:
                    return value.decode(charset, 'strict')  #decode strict
                except:
                    continue
            return value.decode('utf_8', 'ignore')  #decode as if it is utf-8, ignore errors.
        else:
            return unicode(value)
    except:
        try:
            return unicode(repr(value))
        except:
            return u'Error while displaying error'

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
def botsbaseimport(modulename):
    ''' Do a dynamic import.
        Errors/exceptions are handled in calling functions.
    '''
    return importlib.import_module(modulename.encode(sys.getfilesystemencoding()))

def botsimport(*args):
    ''' import modules from usersys.
        return: imported module, filename imported module;
        if not found or error in module: raise
    '''
    modulepath = '.'.join((botsglobal.usersysimportpath,) + args)             #assemble import string
    modulefile = join(botsglobal.ini.get('directories','usersysabs'),*args)   #assemble abs filename for errortexts; note that 'join' is function in this script-file.
    if modulepath in botsglobal.not_import:     #check if previous import failed (no need to try again).This eliminates eg lots of partner specific imports.
        botsglobal.logger.debug(_(u'No import of module "%(modulefile)s".'),{'modulefile':modulefile})
        raise BotsImportError(_(u'No import of module "%(modulefile)s".'),{'modulefile':modulefile})
    try:
        module = botsbaseimport(modulepath)
    except ImportError as msg:
        botsglobal.not_import.add(modulepath)
        botsglobal.logger.debug(_(u'No import of module "%(modulefile)s": %(txt)s.'),{'modulefile':modulefile,'txt':msg})
        raise BotsImportError(_(u'No import of module "%(modulefile)s": %(txt)s'),{'modulefile':modulefile,'txt':msg})
    except Exception as msg:
        botsglobal.logger.debug(_(u'Error in import of module "%(modulefile)s": %(txt)s.'),{'modulefile':modulefile,'txt':msg})
        raise ScriptImportError(_(u'Error in import of module "%(modulefile)s":\n%(txt)s'),{'modulefile':modulefile,'txt':msg})
    else:
        botsglobal.logger.debug(u'Imported "%(modulefile)s".',{'modulefile':modulefile})
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
        #~ print 'not deleted', filename
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
    botsglobal.logger.debug(u'Run userscript "%(functioninscript)s" in "%(modulefile)s".',
                            {'functioninscript':functioninscript,'modulefile':modulefile})
    functiontorun = getattr(module, functioninscript)
    try:
        return functiontorun(**argv)
    except:
        txt = txtexc()
        raise ScriptError(_(u'Userscript "%(modulefile)s": "%(txt)s".'),{'modulefile':modulefile,'txt':txt})

def tryrunscript(module,modulefile,functioninscript,**argv):
    if module and hasattr(module,functioninscript):
        runscript(module,modulefile,functioninscript,**argv)
        return True
    return False

def runscriptyield(module,modulefile,functioninscript,**argv):
    botsglobal.logger.debug(u'Run userscript "%(functioninscript)s" in "%(modulefile)s".',
                            {'functioninscript':functioninscript,'modulefile':modulefile})
    functiontorun = getattr(module, functioninscript)
    try:
        for result in functiontorun(**argv):
            yield result
    except:
        txt = txtexc()
        raise ScriptError(_(u'Script file "%(modulefile)s": "%(txt)s".'),{'modulefile':modulefile,'txt':txt})

#**********************************************************/**
#*************** confirmrules *****************************/**
#**********************************************************/**
def prepare_confirmrules():
    ''' as confirmrules are often used, read these into memory. Reason: performance.
        additional notes:
        - there are only a few confirmrules (10 would be a lot I guess).
        - indexing is not helpfull for confirmrules, this means that each time the whole confirmrule-tabel is scanned.
        - as confirmrules are used for incoming and outgoing (x12, edifact, email) this will almost always lead to better performance. 
    '''
    for confirmdict in query(u'''SELECT confirmtype,ruletype,idroute,idchannel_id as idchannel,frompartner_id as frompartner,topartner_id as topartner,messagetype,negativerule
                        FROM confirmrule
                        WHERE active=%(active)s
                        ORDER BY negativerule ASC
                        ''',
                        {'active':True}):
        botsglobal.confirmrules.append(confirmdict)

def set_asked_confirmrules(routedict,rootidta):
    ''' set 'ask confirmation/acknowledgements for x12 and edifact
    '''
    if not globalcheckconfirmrules(u'ask-x12-997') and not globalcheckconfirmrules(u'ask-edifact-CONTRL'):
        return
    for row in query('''SELECT parent,editype,messagetype,frompartner,topartner
                                FROM ta
                                WHERE idta>%(rootidta)s
                                AND status=%(status)s
                                AND statust=%(statust)s
                                AND (editype='edifact' OR editype='x12') ''',
                                {'status':FILEOUT,'statust':OK,'rootidta':rootidta}):
        if row['editype'] == 'x12':
            if row['messagetype'][:3] in ['997','999']:
                continue
            confirmtype = u'ask-x12-997'
        else:
            if row['messagetype'][:6] in ['CONTRL','APERAK']:
                continue
            confirmtype = u'ask-edifact-CONTRL'
        if not checkconfirmrules(confirmtype,idroute=routedict['idroute'],idchannel=routedict['tochannel'],
                                    topartner=row['topartner'],frompartner=row['frompartner'],messagetype=row['messagetype']):
            continue
        changeq('''UPDATE ta
                   SET confirmasked=%(confirmasked)s, confirmtype=%(confirmtype)s
                   WHERE idta=%(parent)s ''',
                   {'parent':row['parent'],'confirmasked':True,'confirmtype':confirmtype})

def globalcheckconfirmrules(confirmtype):
    ''' global check if confirmrules with this confirmtype is uberhaupt used. 
    '''
    for confirmdict in botsglobal.confirmrules:
        if confirmdict['confirmtype'] == confirmtype:
            return True
    return False

def checkconfirmrules(confirmtype,**kwargs):
    confirm = False       #boolean to return: confirm of not?
    #confirmrules are evaluated one by one; first the positive rules, than the negative rules.
    #this make it possible to include first, than exclude. Eg: send for 'all', than exclude certain partners.
    for confirmdict in botsglobal.confirmrules:
        if confirmdict['confirmtype'] != confirmtype:
            continue
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

#**********************************************************/**
#***************###############  misc.   #############
#**********************************************************/**
def set_database_lock():
    try:
        changeq(u'''INSERT INTO mutex (mutexk) VALUES (1)''')
    except:
        return False
    return True

def remove_database_lock():
    changeq('''DELETE FROM mutex WHERE mutexk=1''')

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
            for key,value in where.iteritems():
                if getattr(taparent,key) != value:
                    break
            else:   #all where-criteria are true; 
                teruglijst.append(taparent)
            trace_recurse(taparent)
    def get_parent(ta):
        ''' yields the parents of a ta '''
        if ta.parent:   #parent via the normal parent-attribute
            if ta.parent not in donelijst:
                yield ta.parent
        else:           #no parent via parent-link, so look via child-link
            for row in query('''SELECT idta
                                 FROM ta
                                 WHERE idta>%(minidta)s
                                 AND idta<%(maxidta)s
                                 AND child=%(idta)s''',
                                {'idta':ta.idta,'minidta':ta.script,'maxidta':ta.idta}):
                if row['idta'] in donelijst:
                    continue
                yield row['idta']

    donelijst = []
    teruglijst = []
    ta.synall()
    trace_recurse(ta)
    return teruglijst

def countoutfiles(idchannel,rootidta):
    ''' counts the number of edifiles to be transmitted via outchannel.'''
    for row in query('''SELECT COUNT(*) as count
                        FROM ta
                        WHERE idta>%(rootidta)s
                        AND status=%(status)s
                        AND statust=%(statust)s
                        AND tochannel=%(tochannel)s
                        ''',
                        {'status':FILEOUT,'statust':OK,'tochannel':idchannel,'rootidta':rootidta}):
        return row['count']

def lookup_translation(frommessagetype,fromeditype,alt,frompartner,topartner):
    ''' lookup the translation: frommessagetype,fromeditype,alt,frompartner,topartner -> mappingscript, tomessagetype, toeditype
    '''
    for row2 in query(u'''SELECT tscript,tomessagetype,toeditype
                            FROM translate
                            WHERE frommessagetype = %(frommessagetype)s
                            AND fromeditype = %(fromeditype)s
                            AND active=%(booll)s
                            AND (alt='' OR alt=%(alt)s)
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

def botsinfo():
    return [
            (_(u'served at port'),botsglobal.ini.getint('webserver','port',8080)),
            (_(u'platform'),platform.platform()),
            (_(u'machine'),platform.machine()),
            (_(u'python version'),platform.python_version()),
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

def strftime(timeformat):
    if botsglobal.ini.getboolean('acceptance','runacceptancetest',False):
        return time.strftime(timeformat,time.strptime("2013-01-23 01:23:45", "%Y-%m-%d %H:%M:%S"))    #if acceptance test use fixed date/time
    else:
        return time.strftime(timeformat)

def settimeout(milliseconds):
    socket.setdefaulttimeout(milliseconds)    #set a time-out for TCP-IP connections

def updateunlessset(updatedict,fromdict):
    updatedict.update((key,value) for key, value in fromdict.iteritems() if key not in updatedict) #!!TODO when is this valid? Note: prevents setting charset from gramamr 
    #~ updatedict.update((key,value) for key, value in fromdict.iteritems() if key not in updatedict or not updatedict[key]) #!!TODO when is this valid? Note: prevents setting charset from gramamr 

def rreplace(org,old,new='',count=1):
    ''' string handling:
        replace old with new in org, max count times.
        with default values: remove last occurence of old in org.
    '''
    lijst = org.rsplit(old,count)
    return new.join(lijst)

def get_relevant_text_for_UnicodeError(msg):
    ''' see python doc for details of UnicodeError'''
    start = msg.start - 10 if msg.start >= 10 else 0
    return msg.object[start:msg.end+35]

def indent_xml(node, level=0,indentstring='    '):
    text2indent = "\n" + level*indentstring
    if len(node):
        if not node.text or not node.text.strip():
            node.text = text2indent + indentstring
        for subnode in node:
            indent_xml(subnode, level+1)
            if not subnode.tail or not subnode.tail.strip():
                subnode.tail = text2indent + indentstring
        if not subnode.tail or not subnode.tail.strip():
            subnode.tail = text2indent
    else:
        if level and (not node.tail or not node.tail.strip()):
            node.tail = text2indent

    
class Uri(object):
    ''' generate uri from parts/components
        - different forms of uri (eg with/without password)
        - general layout like 'scheme://user:pass@hostname:80/path/filename?query=argument#fragment'
        - checks: 1. what is required; 2. all parameters need to be valid
        Notes:
        - no filename: path ends with '/'
        Usage: uri = Uri(scheme='http',username='hje',password='password',hostname='test.com',port='80', path='')
        Usage: uri = Uri(scheme='http',hostname='test.com',port='80', path='test')
    '''
    def __init__(self, **kw):
        self._uri = dict(scheme=u'',username=u'',password=u'',hostname=u'',port=u'', path=u'', filename=u'',query={},fragment=u'')
        self.update(**kw)
    def update( self, **kw):
        self._uri.update(**kw)
    def uri(self, **kw):
        self.update(**kw)
        return self.__str__()
    def __str__(self):
        scheme   = self._uri['scheme'] + u':' if self._uri['scheme'] else u''
        password = u':' + self._uri['password'] if self._uri['password'] else u''
        userinfo = self._uri['username'] + password + u'@' if self._uri['username'] else u''
        port     = u':' + unicode(self._uri['port']) if self._uri['port'] else u''
        fullhost = self._uri['hostname'] + port if self._uri['hostname'] else u''
        authority = u'//' + userinfo + fullhost if fullhost else u''
        if self._uri['path'] or self._uri['filename']:
            terug = os.path.join(authority,self._uri['path'],self._uri['filename'])
        else:
            terug = authority
        return scheme + terug
#**********************************************************/**
#**************  Exception classes ***************************
#**********************************************************/**
class BotsError(Exception):
    ''' formats the error messages. Under all circumstances: give (reasonable) output, no errors.
        input (msg,*args,**kwargs) can be anything: strings (any charset), unicode, objects. Note that these are errors, so input can be 'not valid'!
        to avoid the risk of 'errors during errors' catch-all solutions are used.
        2 ways to raise Exceptions:
        - BotsError('tekst %(var1)s %(var2)s',{'var1':'value1','var2':'value2'})  ###this one is preferred!!
        - BotsError('tekst %(var1)s %(var2)s',var1='value1',var2='value2')
    '''
    def __init__(self, msg,*args,**kwargs):
        self.msg = safe_unicode(msg)
        if args:    ##expect args[0] to be a dict
            if isinstance(args[0],dict):
                xxx = args[0]
            else:
                xxx = {}
        else:
            xxx = kwargs
        self.xxx = collections.defaultdict(unicode)     #catch-all if var in string is not there
        for key,value in xxx.iteritems():
            self.xxx[safe_unicode(key)] = safe_unicode(value)
    def __unicode__(self):
        try:
            return self.msg%self.xxx    #this is already unicode
        except:
            return self.msg             #errors in self.msg; non supported format codes. Don't think this happen...
    def __str__(self):
        try:
            return (self.msg%self.xxx).encode('utf-8','ignore')
        except:
            return self.msg.encode('utf-8','ignore')            #errors in self.msg; non supported format codes. Don't think this happen...
            
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
class GrammarError(BotsError):
    pass
class InMessageError(BotsError):
    pass
class LockedFileError(BotsError):
    pass
class MessageError(BotsError):
    pass
class MessageRootError(BotsError):
    pass
class MappingRootError(BotsError):
    pass
class MappingFormatError(BotsError):
    pass
class OutMessageError(BotsError):
    pass
class PanicError(BotsError):
    pass
class PersistError(BotsError):
    pass
class PluginError(BotsError):
    pass
class BotsImportError(BotsError):    #import script or recursivly imported scripts not there
    pass
class ScriptImportError(BotsError):    #import errors in userscript; userscript is there
    pass
class ScriptError(BotsError):          #runtime errors in a userscript
    pass
class TraceError(BotsError):
    pass
class TranslationNotFoundError(BotsError):
    pass
class GotoException(BotsError):     #sometimes it is simplest to raise an error, and catch it rightaway. Like a goto ;-)  
    pass
class FileTooLargeError(BotsError):
    pass
