#!/usr/bin/env python
''' This script starts bots-engine.'''
import sys
import os
import atexit
import traceback
import logging
logging.raiseExceptions = 0     #if errros occur in writing to log: ignore error; this will lead to a missing log line. 
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
    print '        --cleanup      remove older data from database.'
    print "        -c<directory>   directory for configuration files (default: config)."
    print '    Options can be combined.'
    
    
def start():
    #********command line arguments**************************
    commandstorun = []
    commandspossible = ['--new','--retry','--retransmit','--cleanup']
    routestorun = []    #list with routes to run
    configdir = 'config'
    for arg in sys.argv[1:]:
        if not arg:
            continue
        if arg.startswith('-c'):
            configdir = arg[2:]
            if not configdir:
                print 'Indicated Bots should use specific .ini file but no file name was given.'
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
    #**************initialise configuration file******************************
    #init general: find locating of bots, configfiles, init paths etc.***********************
    botsinit.generalinit(configdir)
    botslib.settimeout(botsglobal.ini.getint('settings','globaltimeout',10))    #
    #**************initialise logging******************************
    try:
        botsinit.initenginelogging()
    except:
        print 'Error in initialising logging system.'
        traceback.print_exc()
        sys.exit(1)
    else:
        atexit.register(logging.shutdown)
    botsglobal.logger.info(u'Python version: "%s".',sys.version)
    botsglobal.logger.info(u'Bots configuration file: "%s".',configdir)
    botsglobal.logger.info(u'Bots database configuration file: "%s".',botslib.join('config',os.path.basename(botsglobal.ini.get('directories','tgconfig','botstg.cfg'))))
    #~ import transform     #run without database etc for debugging
    #~ transform.translate2()
    #~ sys.exit(0)
    #**************connect to database**********************************
    try:
        botslib.connect() 
    except:
        botsglobal.logger.exception(u'Error connecting to database.')
        sys.exit(1)
    else:
        atexit.register(botsglobal.db.close)
    #**************init sending report via smtp***************************
    #if sendreportiferror in bots.ini is set: check if there is a channel called 'botsreport'
    if botsglobal.ini.getboolean('settings','sendreportiferror',False):
        for row in botslib.query('''SELECT idchannel
                                    FROM  channel
                                    WHERE idchannel=%(idchannel)s''',
                                    {'idchannel':'botsreport'}):
            break
        else:
            botsglobal.logger.error(u'Setting "sendreportiferror" in bots.ini is set, but there is no idchannel "botsreport". This is needed to send a errorreport. Tip: use the errorreport-plugin for this.')
            sys.exit(1)
    #**************start main loop****************************************
    try: 
        if botslib.mutexon():   #set a lock on the database
            if not routestorun: #if no routes from command line parameters: use all active routes from database
                for row in botslib.query('''SELECT DISTINCT idroute
                                                FROM routes
                                                WHERE active=%(active)s 
                                                AND (notindefaultrun=%(notindefaultrun)s OR notindefaultrun IS NULL)
                                                ORDER BY idroute ''',
                                                {'active':True,'notindefaultrun':False}):
                    routestorun.append(row['idroute'])
       
            #run the routes for retry, retransmit and new runs.
            #~ timer = botslib.Timer('../timer.txt')
            errorinrun = 0 #indicates if error in run; but is not a real bool
            if '--retry' in commandstorun:
                botsglobal.logger.info(u'Run for retry of old errors.')
                if automaticmaintenance.findlasterror():
                    botsglobal.retry = True     #global is used to indicate that dbta since last error are looked at
                    router.routedispatcher(routestorun,type='retry')
                    botsglobal.retry = False    #needed for correct evaluate
                    #~ timer.point('retry')
                    errorinrun +=  automaticmaintenance.evaluateretryrun('retry')
                    #~ timer.point('retry maintenance')
                else:
                    #~ timer.point('retry')
                    botsglobal.logger.info(u'Nothing to retry.')
            if '--retransmit' in commandstorun:
                botsglobal.logger.info(u'Run for retransmit.')
                if router.routedispatcher(routestorun,type='retransmit'):
                    errorinrun +=  automaticmaintenance.evaluaterun('retransmit')
                else:
                    botsglobal.logger.info(u'Nothing to retransmit.')
                #~ timer.point('retransmit')
            if '--new' in commandstorun:
                botsglobal.logger.info('New run.')
                botsglobal.incommunicate = True
                router.routedispatcher(routestorun,type='new')
                #~ timer.point('new')
                errorinrun +=  automaticmaintenance.evaluaterun('new')
                #~ timer.point('new maintenance')
            if botsglobal.ini.get('settings','whencleanup','always')=='always' or '--cleanup' in commandstorun:
                cleanup.cleanup()
            #~ timer.point('cleanup')
            #~ timer.close()
            botslib.mutexoff()  #remove database lock
        else:
            raise botslib.PanicError(u'Database locked - either another instance of bots-engine is running or bots-engine had a severe error in the last run.')
    except:
        botsglobal.logger.exception(u'Severe system error in bots.')
        sys.exit(1)
    else:
        if errorinrun:
            sys.exit(2) #indicate: error(s) in run(s)
        else:
            sys.exit(0) #OK
            

