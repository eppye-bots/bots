#!/usr/bin/env python
''' This script starts bots-engine.'''
import sys
import os
import atexit
import traceback
import logging
import datetime
logging.raiseExceptions = 0     #if errors occur in writing to log: ignore error; this will lead to a missing log line. 
                                #it is better to have a missing log line than an error in a translation....
#bots-modules
import botslib
import botsinit
import botsglobal
import router
import automaticmaintenance
import cleanup
from botsconfig import *


def showusage():
    print '    Usage without parameters:'
    print '    - Run all actived routes.'
    print '    - Recieve new files.'
    print '    - Previous errors are retried.'
    print '    - Retransmitted/resend: as indicated by user.'
    print '    - Cleanup: as indicated by parameter in config/bots.ini.'
    print '    - Settings in config/bots.ini are used.'
    print
    print '    Routes can be used as parameters, eg:'
    print '        %s  route1  route2'%os.path.basename(sys.argv[0])
    print '    In this example Bots will run route1 and route2.'
    print
    print '    Options:'
    print '        --new          recieve new edi files.'
    print '        --retransmit   resend and rerececieve.'    
    print '        --retry        retry previous errors.'
    print '        --retrylastrun retry lat run (in case of crash).'
    print '        --retrycommunication retry only outgoing communication errors.'
    print '        --cleanup      remove older data from database.'
    print "        -c<directory>   directory for configuration files (default: config)."
    print '    Options can be combined.'
    
    
def start():
    #********command line arguments**************************
    commandspossible = ['--new','--retry','--retransmit','--cleanup','--retrylastrun','--retrycommunication']
    commandstorun = []
    routestorun = []    #list with routes to run
    configdir = 'config'
    for arg in sys.argv[1:]:
        if not arg:
            continue
        if arg.startswith('-c'):
            configdir = arg[2:]
            if not configdir:
                print 'Configuration directory indicated, but no directory name.'
                sys.exit(1)
        elif arg in commandspossible:
            commandstorun.append(arg)
        elif arg in ["?", "/?"] or arg.startswith('-'):
            showusage()
            sys.exit(0)
        else:   #pick up names of routes to run
            routestorun.append(arg)
    if not commandstorun:   #if no command on command line, use all (default)
        commandstorun = commandspossible
    #**************init general: find locating of bots, configfiles, init paths etc.****************
    botsinit.generalinit(configdir)
    #**************initialise logging******************************
    try:
        botsinit.initenginelogging()
    except:
        print 'Error in initialising logging system.'
        traceback.print_exc()
        sys.exit(1)
    else:
        atexit.register(logging.shutdown)
        
    for key,value in botslib.botsinfo():    #log start info
        botsglobal.logger.info(u'%s: "%s".',key,value)
    botsglobal.logger.info(u'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX.')
    #**************connect to database**********************************
    try:
        botsinit.connect() 
    except:
        botsglobal.logger.exception(u'Could not connect to database. Database settings are in bots/config/settings.py.')
        sys.exit(1)
    else:
        botsglobal.logger.info(u'Connect to database "%s".',botsglobal.settings.DATABASE_ENGINE)
        atexit.register(botsglobal.db.close)
    #**************handle database lock****************************************
    #try to set a lock on the database; if this is not possible, the database is already locked. Either:
    #- another instance bots bots-engine is (still) running
    #- or bots-engine had a severe crash.
    #first: check ts of database lock. If below a certain value (set in bots.ini) we assume an other instance is running. Exit quietly - no errors, no logging.
    #next:  warn with report or notification. try a retry of the last run.
    if not botslib.set_database_lock():
        vanaf = datetime.datetime.today() - datetime.timedelta(minutes=botsglobal.ini.getint('settings','maxruntime',60))
        for row in botslib.query('''SELECT ts FROM mutex WHERE ts < %(vanaf)s ''',{'vanaf':vanaf}):
            botsglobal.logger.info('The database is locked. This means bots-engine has crashed in a previous run. This is very rare, eg after a ')
            botslib.sendbotserrorreport('[Bots severe error]!!!Database is locked!!!','jaja...go for retry of last run. ')
            commandstorun = ['--retrylastrun']
            raise botslib.PanicError(u'Database locked - either another instance of bots-engine is running or bots-engine had a severe error in the last run.')
            sys.exit(1)
            break
        else:
            exit(0)
    #*************make up list of routes to run****************************************
    if routestorun: 
        botsglobal.logger.info(u'Run routes from command line: "%s".',str(routestorun))
    else:   # no routes from command line parameters: fetch all active routes from database
        for row in botslib.query('''SELECT DISTINCT idroute
                                    FROM routes
                                    WHERE active=%(active)s 
                                    AND (notindefaultrun=%(notindefaultrun)s OR notindefaultrun IS NULL)
                                    ORDER BY idroute ''',
                                    {'active':True,'notindefaultrun':False}):
            routestorun.append(row['idroute'])
        botsglobal.logger.info(u'Run active routes for database: "%s".',str(routestorun))
    #routestorun is now either a list with routes from comandline, or the list of active routes for the routes tabel in the db.
    #**************run the routes for retry, retransmit and new runs*************************************
    try: 
        #~ timer = botslib.Timer('../timer.txt')
        errorinrun = 0      #detect if there has been some error.
        #retry only communication errors
        #retry last run ***errorrecovery
        if '--retry' in commandstorun:
            if automaticmaintenance.findlasterror():
                botsglobal.logger.info(u'Run for retry of old errors.')
                botsglobal.retry = True     #global is used to indicate that dbta since last error are looked at
                router.routedispatcher(routestorun)
                botsglobal.retry = False    #needed for correct evaluate
                #~ timer.point('retry')
                errorinrun +=  automaticmaintenance.evaluate('retry')
                #~ timer.point('retry maintenance')
            else:
                #~ timer.point('retry')
                botsglobal.logger.info(u'Nothing to retry.')
        if '--retransmit' in commandstorun:
            if automaticmaintenance.prepareretransmit():
                botsglobal.logger.info(u'Run for retransmit.')
                router.routedispatcher(routestorun)
                errorinrun +=  automaticmaintenance.evaluate('retransmit')
            else:
                botsglobal.logger.info(u'Nothing to retransmit.')
            #~ timer.point('retransmit')
        if '--new' in commandstorun:
            botsglobal.logger.info('New run.')
            botsglobal.incommunicate = True
            router.routedispatcher(routestorun)
            #~ timer.point('new')
            errorinrun +=  automaticmaintenance.evaluate('new')
            #~ timer.point('new maintenance')
        if '--cleanup' in commandstorun or botsglobal.ini.get('settings','whencleanup','always')=='always':
            cleanup.cleanup()
        #~ timer.point('cleanup')
        #~ timer.close()
        botslib.remove_database_lock()
    except Exception,e:
        botsglobal.logger.exception(u'Severe error in bots system: "%s".'%(e))    #of course this 'should' not happen. 
        sys.exit(1)
    else:
        if errorinrun:
            sys.exit(2) #indicate: error(s) in run(s)
        else:
            sys.exit(0) #OK
            

