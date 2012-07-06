#!/usr/bin/env python
import sys
import os
import xmlrpclib
from SimpleXMLRPCServer import SimpleXMLRPCServer
import time
import logging
from logging.handlers import TimedRotatingFileHandler
logging.raiseExceptions = 0     #if errors occur in writing to log: ignore error; this will lead to a missing log line.
                                #it is better to have a missing log line than an error in queueserver....
import subprocess
import threading
import botsinit
import botsglobal


def initlogging(logname):
    # initialise file logging
    convertini2logger = {'DEBUG':logging.DEBUG,'INFO':logging.INFO,'WARNING':logging.WARNING,'ERROR':logging.ERROR,'CRITICAL':logging.CRITICAL,'STARTINFO':25}
    logging.addLevelName(25, 'STARTINFO')
    logger = logging.getLogger(logname)
    logger.setLevel(convertini2logger[botsglobal.ini.get('jobqueue','log_file_level','INFO')])
    handler = TimedRotatingFileHandler(os.path.join(botsglobal.ini.get('directories','logging'),logname+'.log'),when='midnight',backupCount=10)
    fileformat = logging.Formatter("%(asctime)s %(levelname)-9s: %(message)s",'%Y%m%d %H:%M:%S')
    handler.setFormatter(fileformat)
    logger.addHandler(handler)
    # initialise console/screen logging
    if botsglobal.ini.getboolean('jobqueue','log_console',True):      #handling for logging to screen
        console = logging.StreamHandler()
        console.setLevel(convertini2logger[botsglobal.ini.get('jobqueue','log_console_level','STARTINFO')])
        consoleformat = logging.Formatter("%(asctime)s %(levelname)-9s: %(message)s",'%Y%m%d %H:%M:%S')
        console.setFormatter(consoleformat) # add formatter to console
        logger.addHandler(console)  # add console to logger
    return logger

def jobqserver(logger):
    ''' thread starting up the xmlrpc server for handling jobqueue.
    '''
    PRIORITY = 0
    JOBNUMBER = 1
    TASK = 2
    class jobqueue(object):
        ''' handles the jobqueue.
            methodes can be called over xmlrpc (except the methods starting with '_')
        '''
        def __init__(self):
            self.jobqueue = []       # list of jobs. in jobqueue are jobs are: (priority,jobnumber,task)
            self.jobcounter = 0      # to assign unique sequential job-number
                    
        def addjob(self,task,priority):
            #canonize task (to better find duplicates)??. Is dangerous, as non-bots-tasks might be started....
            #first check if job already in queue
            for job in self.jobqueue:
                if job[TASK] == task:
                    if job[PRIORITY] != priority:   #change priority. is this useful?
                        job[PRIORITY] = priority
                        logger.info(u'Duplicate job, changed priority: job "%s", priority "%s".',task, priority)
                        self._sort()
                        return 0        #zero or other code??
                    else:
                        logger.info(u'Duplicate job not added: "%s".',task)
                        return 4
            #add the job
            self.jobcounter += 1
            self.jobqueue.append([priority, self.jobcounter,task])
            logger.info(u'Added job "%s" with priority "%s".',task,priority)
            self._sort()
            return 0

        def clearjobq(self):
            self.jobqueue = []
            logger.info(u'Job queue cleared.')
            return 0
        
        def getjob(self):
            if len(self.jobqueue):
                task =  self.jobqueue.pop()[TASK]
                return task
            return 0

        def _sort(self):
            self.jobqueue.sort(reverse=True)
            logger.debug(u'Job queue changed. New queue:%s',''.join(['\n    ' + repr(job) for job in self.jobqueue]))
        ########################################################################################################################
    address = ('localhost', botsglobal.ini.getint('jobqueue','port',6000))
    server = SimpleXMLRPCServer(address,logRequests=False)        
    server.register_instance(jobqueue())
    server.serve_forever()

def launcher(logger):
    xmlrpcclient = xmlrpclib.ServerProxy('http://localhost:' + str(botsglobal.ini.getint('jobqueue','port',6000)))
    lauchfrequency = botsglobal.ini.getint('jobqueue','lauchfrequency',5)
    while True:
        time.sleep(lauchfrequency)
        task_to_run = xmlrpcclient.getjob()
        if task_to_run:       #0 means nothing to launch
            logger.info(u'Lauched job "%s".',task_to_run)
            try:
                result = subprocess.call(task_to_run,stdin=open(os.devnull,'r'),stdout=open(os.devnull,'w'),stderr=open(os.devnull,'w'))
                logger.info(u'Finished job "%s"; result: "%s".',task_to_run,result)
            except Exception, msg:
                logger.info(u'Error starting job "%s": "%s".',task_to_run,msg)

def showusage():
    usage = '''
    This is "%(name)s", a part of Bots open source edi translator - http://bots.sourceforge.net.
    Usage:
        %(name)s  -c<directory> args
    Options:
        -c<directory>   directory for configuration files (default: config).

    %(name)s is a server program that ensures only a single bots-engine 
    runs at any time, and no engine run requests are lost/discarded.
    Each request goes to a queue and is run in sequence when the
    previous run completes. Use of the job queue is optional and must
    be configured in bots.ini (jobqueue section, enabled = True).
    '''%{'name':os.path.basename(sys.argv[0])}
    print usage

#-------------------------------------------------------------------------------
def start():
    #***command line arguments**************************
    configdir = 'config'
    for arg in sys.argv[1:]:
        if arg.startswith('-c'):
            configdir = arg[2:]
            if not configdir:
                print 'Configuration directory indicated, but no directory name.'
                sys.exit(1)
        else:
            showusage()
            sys.exit(0)

    botsinit.generalinit(configdir)         #needed to read config
    logger = initlogging('jobqueue')
    #~ os.chdir(botsglobal.ini.get('directories','botspath'))       #is not needed. better avoid changing directory.
    
    logger.log(25,u'Bots jobqueue started.')
    logger.log(25,u'Bots jobqueue configdir: "%s".',botsglobal.ini.get('directories','config'))
    logger.log(25,u'Bots jobqueue listens for xmlrpc at port: "%s".',botsglobal.ini.getint('jobqueue','port',6000))

    jobqserver_thread = threading.Thread(name='jobqserver', target=jobqserver, args=(logger,))
    jobqserver_thread.start()
    logger.info(u'Jobqueue server started.')
    
    launcher_thread = threading.Thread(name='launcher', target=launcher, args=(logger,))
    launcher_thread.daemon = True
    launcher_thread.start()
    logger.info(u'Launcher started.')
    
    sys.exit(0)


if __name__ == '__main__':
    start()
