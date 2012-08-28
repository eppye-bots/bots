import os
import glob
import time
import datetime
import stat
import shutil
from django.utils.translation import ugettext as _
#bots modules
import botslib
import botsglobal
#~ from botsconfig import *


def cleanup():
    ''' public function, does all cleanup of the database and file system.'''
    try:
        _cleanupsession()
        _cleandatafile()
        _cleanarchive()
        _cleanpersist()
        _cleanprocessnothingreceived()
        _cleantransactions()
    except:
        botsglobal.logger.exception(u'Cleanup error.')


def _cleanupsession():
    ''' delete all expired sessions. Bots-engine starts up much more often than web-server.'''
    vanaf = datetime.datetime.today()
    botslib.change('''DELETE FROM django_session WHERE expire_date < %(vanaf)s''', {'vanaf':vanaf})


def _cleanarchive():
    ''' delete all archive directories older than maxdaysarchive days.'''
    vanaf = (datetime.date.today()-datetime.timedelta(days=botsglobal.ini.getint('settings','maxdaysarchive',180))).strftime('%Y%m%d')
    for row in botslib.query('''SELECT archivepath  FROM  channel '''):
        if row['archivepath']:
            vanafdir = botslib.join(row['archivepath'],vanaf)
            for directory in glob.glob(botslib.join(row['archivepath'],'*')):
                if directory < vanafdir:
                    shutil.rmtree(directory,ignore_errors=True)


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
                botsglobal.logger.exception(_(u'Cleanup could not remove file'))
        elif statinfo.st_mtime > vanaf :
            continue #directory is newer than maxdays, which is also true for the data files in it. Skip it.
        else:   #check files in dir and remove all older than maxdays
            frompath2 = botslib.join(filename,'*')
            emptydir = True   #track check if directory is empty after loop (should directory itself be deleted/)
            for filename2 in glob.glob(frompath2):
                statinfo2 = os.stat(filename2)
                if statinfo2.st_mtime > vanaf  or stat.S_ISDIR(statinfo2.st_mode): #check files in dir and remove all older than maxdays
                    emptydir = False
                else:
                    try:
                        os.remove(filename2)
                    except:
                        botsglobal.logger.exception(_(u'Cleanup could not remove file'))
            if emptydir:
                try:
                    os.rmdir(filename)
                except:
                    botsglobal.logger.exception(_(u'Cleanup could not remove directory'))


def _cleanpersist():
    '''delete all persist older than xx days.'''
    vanaf = datetime.datetime.today() - datetime.timedelta(days=botsglobal.ini.getint('settings','maxdayspersist',30))
    botslib.change('''DELETE FROM persist WHERE ts < %(vanaf)s''',{'vanaf':vanaf})


def _cleantransactions():
    ''' delete records from report, filereport and ta.
        best indexes are on idta/reportidta; this should go fast.
    '''
    vanaf = datetime.datetime.today() - datetime.timedelta(days=botsglobal.ini.getint('settings','maxdays',30))
    for row in botslib.query('''SELECT MAX(idta) as max_idta FROM report WHERE ts < %(vanaf)s''',{'vanaf':vanaf}):
        maxidta = row['max_idta']
    if maxidta is None:   #if there is no maxidta to delete, do nothing
        return
    botslib.change('''DELETE FROM report WHERE idta < %(maxidta)s''',{'maxidta':maxidta})
    botslib.change('''DELETE FROM filereport WHERE idta < %(maxidta)s''',{'maxidta':maxidta})
    botslib.change('''DELETE FROM ta WHERE idta < %(maxidta)s''',{'maxidta':maxidta})
    #the most recent run that is older than maxdays is kept (using < instead of <=).
    #Reason: when deleting in ta this would leave the ta-records of the most recent run older than maxdays (except the first ta-record).
    #this will not lead to problems.


def _cleanprocessnothingreceived():
    ''' delete all new runs that received no files; including all ta-processes in the run
    '''
    vanaf = datetime.datetime.today() - datetime.timedelta(hours=botsglobal.ini.getint('settings','hoursrunwithoutresultiskept',1))
    for row in botslib.query('''SELECT idta
                                FROM report
                                WHERE type = 'new'
                                AND lastreceived=0
                                AND ts < %(vanaf)s''',
                               {'vanaf':vanaf}):
        botslib.change('''DELETE FROM report WHERE idta=%(idta)s ''',{'idta':row['idta']})
        botslib.change('''DELETE FROM ta WHERE idta>%(idta)s AND statuse=%(idta)s''',{'idta':row['idta']})
