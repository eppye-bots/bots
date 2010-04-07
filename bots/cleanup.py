import os
import glob
import time
import datetime
import stat
import shutil
import ConfigParser
#bots modules
import botslib
import botsglobal
from botsconfig import *


def cleanup():
    ''' public function, does all cleanup of the database and file system.'''
    try:
        _cleanupsession() 
        _cleanfilereport() 
        _cleanreport() 
        _cleandatafile()
        _cleanarchive()
        _cleanpersist()
        _cleanta()
        _cleanprocessold()
        _cleanprocessnothingreceived()
    except:
        botsglobal.logger.exception(u'Cleanup error.')


def _cleanupsession():
    ''' delete all expired sessions. Bots-engine starts up much more often than web-server.'''
    vanaf = datetime.datetime.today()
    botslib.change('''DELETE FROM django_session WHERE expire_date < %(vanaf)s''', {'vanaf':vanaf})


def _cleanfilereport():
    ''' delete records in filereport older than xx days; ts in filereport is the same as root-ta.'''
    vanaf = datetime.datetime.today() - datetime.timedelta(days=botsglobal.ini.getint('settings','maxdays',30))
    botslib.change('''DELETE FROM filereport WHERE ts < %(vanaf)s''',{'vanaf':vanaf})
        
def _cleanreport():
    ''' delete all reports older than xx days; ts in report is the same as root-ta.'''
    vanaf = datetime.datetime.today() - datetime.timedelta(days=botsglobal.ini.getint('settings','maxdays',30))
    botslib.change('''DELETE FROM report WHERE ts < %(vanaf)s''',{'vanaf':vanaf})


def _cleanarchive():
    ''' delete all archive directories older than maxdaysarchive days.'''
    vanaf = (datetime.date.today()-datetime.timedelta(days=botsglobal.ini.getint('settings','maxdaysarchive',180))).strftime('%Y%m')
    try:
        for key, value in botsglobal.ini.items('archive'): #lookup for archive directory
            vanafdir = botslib.join(value,vanaf)
            for dir in glob.glob(botslib.join(value,'*')):
                if dir < vanafdir:
                    shutil.rmtree(dir,ignore_errors=True)
    except ConfigParser.NoSectionError:
        pass
    
    
def _cleandatafile():
    ''' delete all data files older than xx days.'''
    vanaf = time.time() - (botsglobal.ini.getint('settings','maxdays',30) * 3600 * 24)
    frompath = botslib.join(botsglobal.ini.get('directories','data','botssys/data'),'*')
    for filename in glob.glob(frompath):
        statinfo = os.stat(filename)
        if not stat.S_ISDIR(statinfo.st_mode):
            try:
                os.remove(filename) #remove files - should be no files in root of data dir
            except:
                botsglobal.logger.exception(u'Cleanup could not remove file')
        elif statinfo.st_mtime > vanaf :
            continue #directory is newer than maxdays, which is also true for the data files in it. Skip it.
        else:   #check files in dir and remove all older than maxdays
            frompath2 = botslib.join(filename,'*')
            emptydir=True   #track check if directory is empty after loop (should directory itself be deleted/)
            for filename2 in glob.glob(frompath2):
                statinfo2 = os.stat(filename2)
                if statinfo2.st_mtime > vanaf  or stat.S_ISDIR(statinfo2.st_mode): #check files in dir and remove all older than maxdays
                    emptydir = False
                else:   
                    try:
                        os.remove(filename2)
                    except:
                        botsglobal.logger.exception(u'Cleanup could not remove file')
            if emptydir:
                try:
                    os.rmdir(filename)
                except:
                    botsglobal.logger.exception(u'Cleanup could not remove directory')

def _cleanpersist():
    '''delete all persist older than xx days.'''
    vanaf = datetime.datetime.today() - datetime.timedelta(days=botsglobal.ini.getint('settings','maxdayspersist',30))
    botslib.change('''DELETE FROM persist WHERE ts < %(vanaf)s''',{'vanaf':vanaf})

def _cleanta():
    '''delete all ta older than xx days -but delete no processes'''
    vanaf = datetime.datetime.today() - datetime.timedelta(days=botsglobal.ini.getint('settings','maxdays',30))
    botslib.change('''DELETE FROM ta
                        WHERE status!=%(status)s
                        AND ts < %(vanaf)s''',
                       {'status':PROCESS,'vanaf':vanaf})

def _cleanprocessold():
    ''' delete all processes that are no longer referred by other ta's & older than xx days.
        as non-process ta's will be deleted after maxdays, I expect the processes also to be deleted.
        (this seems to much better than just delete the processes > maxdays; it is done in the right way.
        processes are organised as trees, so recursive;
    '''
    def core(idta):
        haschildren = False
        #select db-ta's referring to this db-ta
        for row in botslib.query('''SELECT idta,status
                                    FROM  ta
                                    WHERE script=%(idta)s''',
                                    {'idta':idta}):
            if  row[1]!=PROCESS or core(row[0]):
                haschildren = True
        if not haschildren:
            ta=botslib.OldTransaction(idta)
            ta.delete()
        return haschildren
    #select root-processes older than maxdays
    vanaf = datetime.datetime.today() - datetime.timedelta(days=botsglobal.ini.getint('settings','maxdays',30))
    #~ for row in botslib.query('''SELECT idta
                                #~ FROM  ta
                                #~ WHERE status=%(status)s
                                #~ AND script=0
                                #~ AND ts < %(vanaf)s''',    #if script=0: is a root process
                               #~ {'status':PROCESS,'vanaf':vanaf}):
    for row in botslib.query('''SELECT idta
                                FROM  ta
                                WHERE script=0
                                AND ts < %(vanaf)s''',    #if script=0: is a root process
                               {'vanaf':vanaf}):
        core(row[0])


def _cleanprocessnothingreceived():
    ''' delete all processes longer referred by other ta's & older than 1 day, and which are DONE.
        processes are organised as trees, so recursive.
    '''
    def core(idta):
        #select db-ta's referring to this db-ta
        for row in botslib.query('''SELECT idta
                                    FROM  ta
                                    WHERE script=%(idta)s''',
                                    {'idta':idta}):
            core(row[0])
        ta=botslib.OldTransaction(idta)
        ta.delete()
        return 
    #select root-processes older than hoursnotrefferedarekept
    vanaf = datetime.datetime.today() - datetime.timedelta(hours=botsglobal.ini.getint('settings','hoursrunwithoutresultiskept',1))
    for row in botslib.query('''SELECT idta
                                FROM  report
                                WHERE status=%(status)s
                                AND lastreceived=0
                                AND ts < %(vanaf)s''',    #if script=0: is a root process
                               {'status':False,'vanaf':vanaf}):
        core(row[0])
        #delete report
        botslib.change('''DELETE FROM report WHERE idta=%(idta)s ''',{'idta':row[0]})
    #the empty retries are not cleaned by this...these ar not logged as reports. 

