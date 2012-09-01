#!/usr/bin/env python
import sys
import os
import xmlrpclib
from SimpleXMLRPCServer import SimpleXMLRPCServer
import time
import datetime
import subprocess
import threading
import botsinit
import botslib
import botsglobal


#-------------------------------------------------------------------------------
PRIORITY = 0
JOBNUMBER = 1
TASK = 2
class Jobqueue(object):
    ''' handles the jobqueue.
        methodes can be called over xmlrpc (except the methods starting with '_')
    '''
    def __init__(self,logger):
        self.jobqueue = []       # list of jobs. in jobqueue are jobs are: (priority,jobnumber,task)
        self.jobcounter = 0      # to assign unique sequential job-number
        self.logger = logger
                
    def addjob(self,task,priority):
        #canonize task (to better find duplicates)??. Is dangerous, as non-bots-tasks might be started....
        #first check if job already in queue
        for job in self.jobqueue:
            if job[TASK] == task:
                if job[PRIORITY] != priority:   #change priority. is this useful?
                    job[PRIORITY] = priority
                    self.logger.info(u'Duplicate job, changed priority to %s: %s',priority,task)
                    self._sort()
                    return 0        #zero or other code??
                else:
                    self.logger.info(u'Duplicate job not added: %s',task)
                    return 4
        #add the job
        self.jobcounter += 1
        self.jobqueue.append([priority, self.jobcounter,task])
        self.logger.info(u'Added job %s, priority %s: %s',self.jobcounter,priority,task)
        self._sort()
        return 0

    def clearjobq(self):
        self.jobqueue = []
        self.logger.info(u'Job queue cleared.')
        return 0

    def getjob(self):
        if len(self.jobqueue):
            return self.jobqueue.pop()
        return 0

    def _sort(self):
        self.jobqueue.sort(reverse=True)
        self.logger.debug(u'Job queue changed. New queue:%s',''.join(['\n    ' + repr(job) for job in self.jobqueue]))

#-------------------------------------------------------------------------------
def maxruntimeerror(logger,maxruntime,jobnumber,task_to_run):
    logger.error(u'Job %s exceeded maxruntime of %s minutes',jobnumber,maxruntime)
    botslib.sendbotserrorreport(u'[Bots Job Queue] - Job exceeded maximum runtime',
                                u'Job %s exceeded maxruntime of %s minutes:\n %s' % (jobnumber,maxruntime,task_to_run))

#-------------------------------------------------------------------------------
def launcher(logger,port,lauchfrequency,maxruntime):
    xmlrpcclient = xmlrpclib.ServerProxy('http://localhost:' + str(port))
    maxseconds = maxruntime*60
    time.sleep(3)   #to allow jobqserver to start
    while True:
        time.sleep(lauchfrequency)
        job = xmlrpcclient.getjob()

        if job:       #0 means nothing to launch
            jobnumber = job[1]
            task_to_run = job[2]
            # Start a timer thread for maxruntime error
            timer_thread = threading.Timer(maxseconds,maxruntimeerror,args=(logger,maxruntime,jobnumber,task_to_run))
            timer_thread.start()
            try:
                starttime = datetime.datetime.now()
                logger.info(u'Starting job %s',jobnumber)
                result = subprocess.call(task_to_run,stdin=open(os.devnull,'r'),stdout=open(os.devnull,'w'),stderr=open(os.devnull,'w'))
                time_taken = datetime.timedelta(seconds=(datetime.datetime.now() - starttime).seconds)
                logger.info(u'Finished job %s, elapsed time %s, result %s',jobnumber,time_taken,result)
            except Exception, msg:
                logger.error(u'Error starting job %s: %s',jobnumber,msg)
                botslib.sendbotserrorreport(u'[Bots Job Queue] - Error starting job',
                                            u'Error starting job %s:\n %s\n\n %s' % (jobnumber,task_to_run,msg))
            timer_thread.cancel()

#-------------------------------------------------------------------------------
def showusage():
    usage = '''
    This is "%(name)s", a part of Bots open source edi translator - http://bots.sourceforge.net.
    Usage:
        %(name)s  [-c<directory>]
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
    if not botsglobal.ini.getboolean('jobqueue','enabled',False):
        print 'Bots jobqueue cannot start; not enabled in %s/bots.ini' % configdir
        sys.exit(1)

    port = botsglobal.ini.getint('jobqueue','port',6000)
    lauchfrequency = botsglobal.ini.getint('jobqueue','lauchfrequency',5)
    maxruntime = botsglobal.ini.getint('settings','maxruntime',60)
    
    process_name = 'jobqueue'
    logger = botsinit.initserverlogging(process_name)
    logger.log(25,u'Bots %s started.',process_name)
    logger.log(25,u'Bots %s configdir: "%s".',process_name,botsglobal.ini.get('directories','config'))
    logger.log(25,u'Bots %s listens for xmlrpc at port: "%s".',process_name,port)

    launcher_thread = threading.Thread(name='launcher', target=launcher, args=(logger,port,lauchfrequency,maxruntime))
    launcher_thread.daemon = True
    launcher_thread.start()
    logger.info(u'Jobqueue launcher started.')

    # this main thread is the jobqserver (the xmlrpc server for handling jobqueue)
    logger.info(u'Jobqueue server started.')
    server = SimpleXMLRPCServer(('localhost', port),logRequests=False)        
    server.register_instance(Jobqueue(logger))
    server.serve_forever()
    
    sys.exit(0)


if __name__ == '__main__':
    start()
