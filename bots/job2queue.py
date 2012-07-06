#!/usr/bin/env python
import sys
import os
import xmlrpclib
import socket
import botsinit
import botsglobal

def send_job_to_jobqueue(task_args,priority=5):
    ''' adds a new job to the bots-jobqueueserver.
        is a xmlrpc client.
        Import this function in eg views.py.
        Received return codes  from jobqueueserver:
        0 = OK, job added to job queue.
        4 = job is a duplicate of job already in the queue
    '''
    try:
        #~ remote_server = xmlrpclib.ServerProxy('http://localhost:' + str(botsglobal.ini.getint('jobqueue','port',6000)))
        remote_server = xmlrpclib.ServerProxy('http://localhost:6000')
        return remote_server.addjob(task_args,priority)
    except socket.error:
        return 1    #jobqueueserver server not active

def showusage():
    usage = '''
    This is "%(name)s", a part of Bots open source edi translator - http://bots.sourceforge.net.
    Usage:
        %(name)s  -c<directory> [-p<priority>] program [parameters]
    Options:
        -c<directory>   directory for configuration files (default: config).
        -p<priority>    priority of job, 1-9 (default: 5).

    Place a job in the bots jobqueue. Bots jobqueue takes care of
    correct processing of jobs.
    Example of usage:
        %(name)s -cconfig -p5 python2.7 /usr/local/bin/bots-engine.py
    '''%{'name':os.path.basename(sys.argv[0])}
    print usage

#-------------------------------------------------------------------------------
def start():
    #***command line arguments**************************
    configdir = 'config'    #default value
    priority = 5    #default value
    task_args = []
    for arg in sys.argv[1:]:
        if arg in ['-h', '--help']:
            showusage()
            sys.exit(0)
        elif arg.startswith('-p'):
            try:
                priority =  int(arg[2:])
            except:
                print 'Priority should be numeric (1=highest, 9=lowest).'
                sys.exit(64)
        elif arg.startswith('-c'):
            configdir = arg[2:]
            if not configdir:
                print 'Configuration directory indicated, but no directory name.'
                sys.exit(64)
            task_args.append(arg)
        else:
            task_args.append(arg)
    
    botsinit.generalinit(configdir)         #needed to read config
    #~ os.chdir(botsglobal.ini.get('directories','botspath'))
    terug = send_job_to_jobqueue(task_args,priority)
    if terug == 0:
        print 'OK, job is added to queue'
    elif terug == 1:
        print 'Error, job not error to jobqueue.'
    elif terug == 4:
        print 'Duplicate job, not added.'
    sys.exit(terug)

if __name__ == '__main__':
    start()
