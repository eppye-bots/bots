#!/usr/bin/env python
import sys
import os
from SimpleXMLRPCServer import SimpleXMLRPCServer
import logging, logging.handlers
from logging.handlers import TimedRotatingFileHandler
import subprocess
import botsinit
import botsglobal


def initlogging(logname):
    # initialise file and console logging
    convertini2logger = {'DEBUG':logging.DEBUG,'INFO':logging.INFO,'WARNING':logging.WARNING,'ERROR':logging.ERROR,'CRITICAL':logging.CRITICAL,'STARTINFO':25}
    logging.addLevelName(25, 'STARTINFO')
    botsglobal.logger = logging.getLogger(logname)
    botsglobal.logger.setLevel(convertini2logger[botsglobal.ini.get('jobqueue','log_file_level','INFO')])
    handler = TimedRotatingFileHandler(os.path.join(botsglobal.ini.get('directories','logging'),logname+'.log'),when='midnight',backupCount=10)
    fileformat = logging.Formatter("%(asctime)s %(levelname)-9s: %(message)s",'%Y%m%d %H:%M:%S')
    handler.setFormatter(fileformat)
    botsglobal.logger.addHandler(handler)
    #logging for console/screen
    if botsglobal.ini.getboolean('jobqueue','log_console',True):      #handling for logging to screen
        console = logging.StreamHandler()
        console.setLevel(convertini2logger[botsglobal.ini.get('jobqueue','log_console_level','STARTINFO')])
        consoleformat = logging.Formatter("%(asctime)s %(levelname)-9s: %(message)s",'%Y%m%d %H:%M:%S')
        console.setFormatter(consoleformat) # add formatter to console
        botsglobal.logger.addHandler(console)  # add console to logger

#for handling of jobs/tasks in jobqueue
PRIORITY = 0
JOBNUMBER = 1
TASK = 2

class jobqueue(object):
    ''' handles the xmlrpc calls.
        takes care of starting the launcher (and re-start if needed)
        methodes can be called over xmlrpc (except the methods starting with '_')
    '''
    def __init__(self,configdir):
        self.jobqueue = []       # list of jobs. in jobqueue are jobs are: (priority,jobnumber,task)
        self.jobcounter = 0      # to assign unique sequential job-number
        self.configdir = configdir
        self._start_launcher()        #start launcher_process; is watched
                
    def addjob(self,task,priority):
        #canonize task (to better find duplicates)??. Is angerous, as non-bots-tasks might be started....
        #when job is added, always check if launcher_process is still alive:
        status_launcher = self._launcher_process.poll()
        if status_launcher is not None:
            botsglobal.logger.error(u'Launcher is gone with status: %s'%(status_launcher))
            self._start_launcher()        #start launcher_process; is watched
        #check if job already in queue
        for job in self.jobqueue:
            if job[TASK] == task:
                if job[PRIORITY] != priority:
                    job[PRIORITY] = priority
                    self._sort()
                    botsglobal.logger.info(u'Duplicate job, changed priority: job "%", priority %s',task, priority)
                    return 0        #zero or other code??
                else:
                    botsglobal.logger.info(u'Duplicate job not added: %s',task)
                    return 4
        #add the job
        self.jobcounter += 1
        self.jobqueue.append([priority, self.jobcounter,task])
        self._sort()
        botsglobal.logger.info(u'Added job %s priority %s',task,priority)
        return 0

    def logresult(self,task,result):
        ''' launcher reports the results of a job. '''
        botsglobal.logger.info(u'Finished job "%s" finished; result: %s',task,result)
        return 0

    def clearjobq(self):
        self.jobqueue = []
        botsglobal.logger.info(u'Job queue cleared.')
        return 0
    
    def getjob(self):
        if len(self.jobqueue):
            task =  self.jobqueue.pop()[TASK]
            botsglobal.logger.info(u'Started job %s via launcher.',task)
            return task
        return 0

    def _sort(self):
        self.jobqueue.sort(reverse=True)
        botsglobal.logger.debug(u'Job queue changed. New queue:%s',''.join(['\n    ' + repr(job) for job in self.jobqueue]))

    def _start_launcher(self):
        ''' launcher_process will be watched; each time a job is added a check is done.s
        '''
        self._launcher_process = subprocess.Popen([sys.executable,os.path.join(botsglobal.ini.get('directories','botspath'),'launcher.py'),'-c' + self.configdir],stdin=open(os.devnull,'r'),stdout=open(os.devnull,'w'),stderr=open(os.devnull,'w'))
        botsglobal.logger.log(25,u'Bots jobqueueserver started the launcher.')


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
    initlogging('jobqueueserver')
    #~ os.chdir(botsglobal.ini.get('directories','botspath'))

    botsglobal.logger.log(25,u'Bots jobqueueserver started.')
    botsglobal.logger.log(25,u'Bots jobqueueserver configdir: "%s".',botsglobal.ini.get('directories','config'))
    botsglobal.logger.log(25,u'Bots jobqueueserver serving at port: %s',botsglobal.ini.getint('jobqueue','port',6000))

    address = ('localhost', botsglobal.ini.getint('jobqueue','port',6000))
    server = SimpleXMLRPCServer(address,logRequests=False)        
    server.register_instance(jobqueue(configdir))
    server.serve_forever()  # Run the server's main loop

    sys.exit(0)


if __name__ == '__main__':
    start()
