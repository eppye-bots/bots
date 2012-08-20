#!/usr/bin/env python
''' This script starts bots-engine.'''
import sys
import os
import atexit
import traceback
import datetime
import logging
logging.raiseExceptions = 0     #if errors occur in writing to log: ignore error; this will lead to a missing log line.
                                #it is better to have a missing log line than an error in a translation....
from django.utils.translation import ugettext as _
#bots-modules
import botslib
import botsinit
import botsglobal
import router
import cleanup
from botsconfig import *


def showusage():
    usage = '''
    This is "%(name)s", a part of Bots open source edi translator - http://bots.sourceforge.net.
    The %(name)s does the actual translations and communications; it's the workhorse. It does not have a fancy interface.
    Usage:
        %(name)s  [run-options] [config-option] [routes]

    Run-options (can be combined, except for crashrecovery):
        --new                receive new edi files (default: if no run-option given: run as new).
        --resend             resend as indicated by user.
        --rereceive          rereceive as indicated by user.
        --crashrecovery      reruns the run where the crash occurred. (when database is locked).
        --automaticretrycommunication - automatically retry outgoing communication.
        --cleanup            remove older data from database.
    Config-option:
        -c<directory>        directory for configuration files (default: config).
    Routes: list of routes to run. Default: all active routes (in the database)

    '''%{'name':os.path.basename(sys.argv[0])}
    print usage

def start():
    #exit codes:
    # 0: OK, no errors
    # 1: (system) errors
    # 2: bots ran OK, but there are errors/process errors  in the run
    # 3: Database is locked, but "maxruntime" has not been exceeded.
    #********command line arguments**************************
    commandspossible = ['--crashrecovery','--automaticretrycommunication','--resend','--rereceive','--new']
    commandstorun = []
    routestorun = []    #list with routes to run
    configdir = 'config'
    cleanupcommand = False
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
        elif arg == '--cleanup':
            cleanupcommand = True
        elif arg in ["?", "/?"] or arg.startswith('-'):
            showusage()
            sys.exit(0)
        else:   #pick up names of routes to run
            routestorun.append(arg)
    if not commandstorun:   #if no command on command line, use new (default)
        commandstorun = ['--new']
    commandstorun = [command[2:] for command in commandspossible if command in commandstorun]   #sort commands
    #**************init general: find locating of bots, configfiles, init paths etc.****************
    botsinit.generalinit(configdir)
    #set current working directory to botspath
    #~ os.chdir(botsglobal.ini.get('directories','botspath'))
    #**************initialise logging******************************
    try:
        botsinit.initenginelogging()
    except:
        print _('Error in initialising logging system.')
        traceback.print_exc()
        sys.exit(1)
    else:
        atexit.register(logging.shutdown)

    for key,value in botslib.botsinfo():    #log start info
        botsglobal.logger.info(u'%s: "%s".',key,value)
    #**************connect to database**********************************
    try:
        botsinit.connect()
    except:
        botsglobal.logger.exception(_(u'Could not connect to database. Database settings are in bots/config/settings.py.'))
        sys.exit(1)
    else:
        botsglobal.logger.info(_(u'Connected to database.'))
        atexit.register(botsglobal.db.close)
    #initialise user exits for the whole bots-engine (this script file)
    try:
        userscript,scriptname = botslib.botsimport('routescripts','botsengine')
    except ImportError:      #script is not there; other errors like syntax errors are not catched
        userscript = scriptname = None

    #**************handle database lock****************************************
    #try to set a lock on the database; if this is not possible, the database is already locked. Either:
    #1 another instance bots bots-engine is (still) running
    #2 or bots-engine was terminated unexpected.
    if not botslib.set_database_lock():
        #there is a database lock!
        if 'crashrecovery' in commandstorun:
            pass    #ok, user wants a crashrecovery
        else:
            #following settings in bots.ini are important for this:
            #- maxruntime: max time  engine is allowed/expected to run. 
            #       if maxtime is not passed: do nothing.
            #       if maxtime is passed: generate ONE warning email. examine when last action was done.
            #- automaticcrashrecovery: if True bots does automaticcrashrecovery.
            #- maxruntimeforcerecovery (only if automaticcrashrecovery):
            #       if maxruntimeforcerecovery is not passed: do nothing
            #       if maxruntimeforcerecovery is passed: when last action is > than maxruntime: do nothing
            #       if maxruntimeforcerecovery is passed: when last action is < than maxruntime: do automatic recovery
            #when scheduling bots it is possible that the last run is still running. Check if maxruntime has passed:
            maxruntime_is_passed = False
            maxruntime = datetime.datetime.today() - datetime.timedelta(minutes=botsglobal.ini.getint('settings','maxruntime',60))
            for row in botslib.query('''SELECT ts,mutexer FROM mutex WHERE ts < %(maxruntime)s ''',{'maxruntime':maxruntime}):
                #maxruntime has passed!
                maxruntime_is_passed = True
                time_of_crashed_run = row['ts']
                is_error_email_send = row['mutexer']
                #check when last action was performed
                for row2 in botslib.query('''SELECT MAX(idta) as maxidta FROM ta WHERE idta IS NOT NULL'''):
                    lastta = botslib.OldTransaction(row2['maxidta'])
                    lastta.syn('ts')    #get the timestamp of this run
                    time_of_last_action = lastta.ts
                    break
                else:
                    time_of_last_action = ''
                warn =   _(u'Bots database is locked!\n'
                            'Possible causes:\n'
                            '- An instance of bots-engine is still running.\n'
                            '- The previous run of bots-engine has ended abnormally. Most likely causes: bots-engine terminated by user, system crash, power-down, etc.\n'
                            'Advised is to check first if bots-engine is still running.\n'
                            'If bots-engine is not running, do (via menu:Systasks) a "Run crash recovery".\n'
                            'Time the previous run started: "%s"\n'
                            'Time of last action in the previous run: "%s"'%(time_of_crashed_run,time_of_last_action))
                botsglobal.logger.critical(warn)
                #send ONE warning email.
                if is_error_email_send != 1:
                    botslib.sendbotserrorreport(_(u'[Bots severe error]Database is locked'),warn)
                    #set indication that email to report crashed run is set
                    botslib.change('''UPDATE mutex
                                        SET mutexer=1
                                        WHERE mutexk=1 ''')
                if botsglobal.ini.get('settings','automaticcrashrecovery','False'):
                    do_automaticcrashrecovery = False
                    maxruntimeforcerecovery = datetime.datetime.today() - datetime.timedelta(minutes=botsglobal.ini.getint('settings','maxruntimeforcerecovery',90))
                    for row3 in botslib.query('''SELECT ts,mutexer FROM mutex WHERE ts < %(maxruntimeforcerecovery)s ''',{'maxruntimeforcerecovery':maxruntimeforcerecovery}):
                        botsglobal.logger.info('"maxruntimeforcerecovery" is passed, bots will do an automatic crash recovery.')
                        do_automaticcrashrecovery = True
                        #maxruntimeforcerecovery has passed: bots will do a forced recovery, but only
                        #if time_of_last_action is after maxruntime (when bots-engine did an action after maxruntime)
                        if time_of_last_action > maxruntime:
                            warn =   _(u'"maxruntimeforcerecovery" is passed, but engine is still active as engine has done an action after "maxruntime".\n'
                                        'So nothing is done now')
                            botsglobal.logger.critical(warn)
                            botslib.sendbotserrorreport(_(u'[Bots severe error]Database is locked'),warn)
                            sys.exit(3)
                        else:
                            botsglobal.logger.critical('Do a automatic crash recovery.')
                            commandstorun.insert(0,'crashrecovery')
                    if not do_automaticcrashrecovery:
                        botsglobal.logger.info(_(u'Database is locked; "maxruntime" is exceeded but "maxruntimeforcerecovery" is not exceeded.'))
                        sys.exit(3)
                else:
                    sys.exit(3)
            if not maxruntime_is_passed:   #maxruntime has not passed. Exit silently, nothing reported
                botsglobal.logger.info(_(u'Database is locked but "maxruntime" has not been exceeded.'))
                sys.exit(3)
    else:       #normal operation, there was no database lock
        if 'crashrecovery' in commandstorun:    #user starts recovery operation but there is no databaselock.
            botsglobal.logger.info('database is not locked, engine is run with "crashrecovery"; as this is not usefull no crashrecovery is done.')
            commandstorun.remove('crashrecovery')
            botslib.remove_database_lock()
            sys.exit(0)
    
    #**************run the routes**********************************************
    #commandstorun determines the type(s) of run. eg: ['--automaticretrycommunication','--new']
    #for each command
    #   do a run all routes
    try:
        errorinrun = 0      #detect if there has been some error. Only used for correct exit() code
        for command in commandstorun:
            botsglobal.logger.info('Run %s.'%command)
            #get list of routes to run
            if command == 'new':
                if routestorun:
                    use_routestorun = routestorun[:]
                    botsglobal.logger.info(u'Run routes from command line: "%s".',str(use_routestorun))
                else:   # no routes from command line parameters: fetch all active routes from database (unless 'not in default run')
                    use_routestorun = []
                    for row in botslib.query('''SELECT DISTINCT idroute
                                                FROM routes
                                                WHERE active=%(active)s
                                                AND (notindefaultrun=%(notindefaultrun)s OR notindefaultrun IS NULL)
                                                ORDER BY idroute ''',
                                                {'active':True,'notindefaultrun':False}):
                        use_routestorun.append(row['idroute'])
                    botsglobal.logger.info(_(u'Run active routes from database that are in default run: "%s".'),str(use_routestorun))
            else:   #for command other than 'new': use all active routes.
                use_routestorun = []
                for row in botslib.query('''SELECT DISTINCT idroute
                                            FROM routes
                                            WHERE active=%(active)s
                                            ORDER BY idroute ''',
                                            {'active':True}):
                    use_routestorun.append(row['idroute'])
                botsglobal.logger.info(_(u'Run all active routes from database: "%s".'),str(use_routestorun))
            errorinrun += router.rundispatcher(command,use_routestorun)
            if userscript and hasattr(userscript,'post' + command):
                botslib.runscript(userscript,scriptname,'post' + command,routestorun=use_routestorun)
        if cleanupcommand or botsglobal.ini.get('settings','whencleanup','always')=='always':
            botsglobal.logger.debug(u'Do cleanup.')
            cleanup.cleanup()
        botslib.remove_database_lock()
    except Exception,msg:
        botsglobal.logger.exception(_(u'Severe error in bots system:\n%s')%(msg))    #of course this 'should' not happen.
        sys.exit(1)
    else:
        if errorinrun:
            sys.exit(2) #indicate: error(s) in run(s)
        else:
            sys.exit(0) #OK


if __name__ == '__main__':
    start()

