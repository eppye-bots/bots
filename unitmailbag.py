import filecmp 
import shutil
import os
import sys
import subprocess
import logging
#import bots-modules
import bots.botslib as botslib
import bots.botsinit as botsinit
import bots.botsglobal as botsglobal
from bots.botsconfig import *

'''
plugin 'unitmailbag'
enable routes
'''

def dummylogger():
    botsglobal.logger = logging.getLogger('dummy')
    botsglobal.logger.setLevel(logging.ERROR)
    botsglobal.logger.addHandler(logging.StreamHandler(sys.stdout))

def getreportlastrun():
    for row in botslib.query(u'''SELECT *
                            FROM    report
                            ORDER BY idta DESC
                            '''):
        #~ print row
        return row
    raise Exception('no report')

def geterrorlastrun():
    for row in botslib.query(u'''SELECT *
                            FROM    filereport
                            ORDER BY idta DESC
                            '''):
        #~ print row
        return row['errortext']
    raise Exception('no filereport')

def comparedicts(dict1,dict2):
    for key,value in dict1.items():
        if value != dict2[key]:
            raise Exception('error comparing "%s": should be %s but is %s (in db),'%(key,value,dict2[key]))

def removeWS(str):
    return ' '.join(str.split())



if __name__=='__main__':
    pythoninterpreter = 'python2.7'
    newcommand = [pythoninterpreter,'bots-engine.py',]
    botsinit.generalinit('config')
    dummylogger()
    botsinit.connect()
    botssys = botsglobal.ini.get('directories','botssys')
    
    subprocess.call(newcommand)     #run bots
    comparedicts({'status':0,'lastreceived':13,'lasterror':0,'lastdone':13,'lastok':0,'lastopen':0,'send':39,'processerrors':0},getreportlastrun()) #check report

    logging.shutdown()
    botsglobal.db.close
    
    print 'Tests OK!!!' 
