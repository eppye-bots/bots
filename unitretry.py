import filecmp 
import glob
import shutil
import os
import sys
import subprocess
import logging
import logging
import bots.botslib as botslib
import bots.botsinit as botsinit
import bots.botsglobal as botsglobal
from bots.botsconfig import *

'''plugin unitretry.zip'''
''' input: mime (complex structure); 2 different edi attachments, and ' tekst' attachemnt
    some user scripts are written in this unit test; so one runs errors will occur; write user script which prevents error in next run
'''
    

def dummylogger():
    botsglobal.logger = logging.getLogger('dummy')
    botsglobal.logger.setLevel(logging.ERROR)
    botsglobal.logger.addHandler(logging.StreamHandler(sys.stdout))


def getlastreport():
    for row in botslib.query(u'''SELECT *
                            FROM    report
                            ORDER BY idta DESC
                            '''):
        #~ print row
        return row

def mycompare(dict1,dict2):
    for key,value in dict1.items():
        if value != dict2[key]:
            raise Exception('error comparing "%s": should be %s but is %s (in db),'%(key,value,dict2[key]))

def scriptwrite(path,content):
    f = open(path,'w')
    f.write(content)
    f.close()

if __name__ == '__main__':
    pythoninterpreter = 'C:/python26/python'
    newcommand = [pythoninterpreter,'bots-engine.py',]
    retrycommand = [pythoninterpreter,'bots-engine.py','--retry']
    
    botsinit.generalinit('config')
    botssys = botsglobal.ini.get('directories','botssys')
    usersys = botsglobal.ini.get('directories','usersysabs')
    dummylogger()
    botsinit.connect()
    
    scriptwrite(os.path.join(usersys,'mappings','edifact','unitretry_2.py'),
'''
import bots.transform as transform
def main(inn,out):
    raise Exception('test mapping')
    transform.inn2out(inn,out)''')

    scriptwrite(os.path.join(usersys,'communicationscripts','unitretry_mime1_in.py'),
'''
def accept_incoming_attachment(channeldict,ta,charset,content,contenttype):
    if not content.startswith('UNB'):
        raise Exception('test')
    return True
''')

    #new;  error in mime-handling
    subprocess.call(newcommand)
    mycompare({'status':1,'lastreceived':1,'lasterror':1,'lastdone':0,'send':0},getlastreport())
    
    #retry: again same error
    subprocess.call(retrycommand)
    mycompare({'status':1,'lastreceived':1,'lasterror':1,'lastdone':0,'send':0},getlastreport())
    scriptwrite(os.path.join(usersys,'communicationscripts','unitretry_mime1_in.py'),
'''
def accept_incoming_attachment(channeldict,ta,charset,content,contenttype):
    if not content.startswith('UNB'):
        return False
    return True
''')
    #retry: mime is OK< but mapping error will occur
    subprocess.call(retrycommand)
    mycompare({'status':1,'lastreceived':1,'lasterror':1,'lastdone':0,'send':1},getlastreport())

    #retry: mime is OK, same mapping error
    subprocess.call(retrycommand)
    mycompare({'status':1,'lastreceived':1,'lasterror':1,'lastdone':0,'send':0},getlastreport())

    scriptwrite(os.path.join(usersys,'mappings','edifact','unitretry_2.py'),
'''
import bots.transform as transform
def main(inn,out):
    transform.inn2out(inn,out)''')
    
    #retry: whole translation is OK
    subprocess.call(retrycommand)
    mycompare({'status':0,'lastreceived':1,'lasterror':0,'lastdone':1,'send':2},getlastreport())

    #new;  whole transaltion is OK
    subprocess.call(newcommand)
    mycompare({'status':0,'lastreceived':1,'lasterror':0,'lastdone':1,'send':2},getlastreport())
    
    logging.shutdown()
    botsglobal.db.close