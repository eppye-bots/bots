#!/usr/bin/env python
''' Start bots-engine.'''
import sys
import os
import atexit
import logging
import socket
import time
from django.utils.translation import ugettext as _
#bots-modules
import botslib
import botsinit
import botsglobal
import router
import cleanup
import warnings


def start():
    ''' sysexit codes:
        0: OK, no errors
        1: (system) errors incl parsing of command line arguments
        2: bots ran OK, but there are errors/process errors  in the run
        3: Database is locked, but "maxruntime" has not been exceeded.
    '''
    #NOTE: bots directory should always be on PYTHONPATH - otherwise it will not start.
    #********command line arguments**************************
    usage = '''
    This is "%(name)s" version %(version)s, part of Bots open source edi translator (http://bots.sourceforge.net).
    Does the actual translations and communications; it's the workhorse. It does not have a fancy interface.

    Usage:
        %(name)s  [run-options] [config-option] [routes]
    Run-options (can be combined):
        --new                receive new edi files (default: if no run-option given: run as new).
        --resend             resend as indicated by user.
        --rereceive          rereceive as indicated by user.
        --automaticretrycommunication - automatically retry outgoing communication.
        --cleanup            remove older data from database.
    Config-option:
        -c<directory>        directory for configuration files (default: config).
    Routes: list of routes to run. Default: all active routes (in the database)

    '''%{'name':os.path.basename(sys.argv[0]),'version':botsglobal.version}
    configdir = 'config'
    commandspossible = ['--automaticretrycommunication','--resend','--rereceive','--new']
    commandstorun = []
    routestorun = []    #list with routes to run
    do_cleanup_parameter = False
    for arg in sys.argv[1:]:
        if arg.startswith('-c'):
            configdir = arg[2:]
            if not configdir:
                print 'Error: configuration directory indicated, but no directory name.'
                sys.exit(1)
        elif arg in commandspossible:
            commandstorun.append(arg)
        elif arg == '--cleanup':
            do_cleanup_parameter = True
        elif arg in ["?", "/?",'-h', '--help'] or arg.startswith('-'):
            print usage
            sys.exit(0)
        else:   #pick up names of routes to run
            routestorun.append(arg)
    if not commandstorun and not do_cleanup_parameter:   #if no command on command line, use new (default)
        commandstorun = ['--new']
    commandstorun = [command[2:] for command in commandspossible if command in commandstorun]   #sort commands
    #***********end handling command line arguments**************************
    
    botsinit.generalinit(configdir)     #find locating of bots, configfiles, init paths etc.
    #set working directory to bots installation. advantage: when using relative paths it is clear that this point paths within bots installation. 
    os.chdir(botsglobal.ini.get('directories','botspath'))

    #**************check if another instance of bots-engine is running/if port is free******************************
    try:
        engine_socket = botslib.check_if_other_engine_is_running()
    except socket.error:
        sys.exit(3)
    else:
        atexit.register(engine_socket.close)

    #**************initialise logging******************************
    process_name = 'engine'
    botsglobal.logger = botsinit.initenginelogging(process_name)
    atexit.register(logging.shutdown)
    for key,value in botslib.botsinfo():    #log info about environement, versions, etc
        botsglobal.logger.info(u'%(key)s: "%(value)s".',{'key':key,'value':value})

    #**************connect to database**********************************
    try:
        botsinit.connect()
    except Exception as msg:
        botsglobal.logger.exception(_(u'Could not connect to database. Database settings are in bots/config/settings.py. Error: "%(msg)s".'),{'msg':msg})
        sys.exit(1)
    else:
        botsglobal.logger.info(_(u'Connected to database.'))
        atexit.register(botsglobal.db.close)
    #************initialise user exits for the whole bots-engine*************************
    try:
        userscript,scriptname = botslib.botsimport('routescripts','botsengine')
    except botslib.BotsImportError:      #userscript is not there; other errors like syntax errors are not catched
        userscript = scriptname = None
    #***acceptance tests: initialiase acceptance user script******************************
    acceptance_userscript = acceptance_scriptname = None
    if botsglobal.ini.getboolean('acceptance','runacceptancetest',False):
        botsglobal.logger.info(_(u'This run is an acceptance test - as indicated in option "runacceptancetest" in bots.ini.'))
        try:
            acceptance_userscript,acceptance_scriptname = botslib.botsimport('routescripts','bots_acceptancetest')
        except botslib.BotsImportError:
            botsglobal.logger.info(_(u'In acceptance test there is no script file "bots_acceptancetest.py" to check the results of the acceptance test.'))

    #**************handle database lock****************************************
    #set a lock on the database; if not possible, the database is locked: an earlier instance of bots-engine was terminated unexpectedly.
    if not botslib.set_database_lock():
        #for SQLite: do a integrity check on the database
        if botsglobal.settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
            cursor = botsglobal.db.execute('''PRAGMA integrity_check''')
            result = cursor.fetchone()
            if result[0] != u'ok':
                warn =  _(u'!Bots database is locked!\n'\
                            'Bots did an integrity check on the database, but database was not OK.\n'\
                            'Manual action is needed!\n'\
                            'Bots has stopped processing EDI files.')
                botsglobal.logger.critical(warn)
                botslib.sendbotserrorreport(_(u'[Bots severe error]Database is damaged'),warn)
                sys.exit(1)
        warn =  _(u'!Bots database is locked!\n'\
                    'Bots-engine has ended in an unexpected way during the last run.\n'\
                    'Most likely causes: sudden power-down, system crash, problems with disk I/O, bots-engine terminated by user, etc.\n'
                    'Bots will do an automatic crash recovery now.')
        botsglobal.logger.critical(warn)
        botslib.sendbotserrorreport(_(u'[Bots severe error]Database is locked'),warn)
        commandstorun.insert(0,'crashrecovery')         #there is a database lock. Add a crashrecovery as first command to run.
    atexit.register(botslib.remove_database_lock)

    warnings.simplefilter('error', UnicodeWarning)

    #**************run the routes**********************************************
    #commandstorun determines the type(s) of run. eg: ['automaticretrycommunication','new']
    try:
        botslib.prepare_confirmrules()
        #in acceptance tests: run a user script before running eg to clean output directories******************************
        botslib.tryrunscript(acceptance_userscript,acceptance_scriptname,'pretest',routestorun=routestorun)
        botslib.tryrunscript(userscript,scriptname,'pre',commandstorun=commandstorun,routestorun=routestorun)
        errorinrun = 0      #detect if there has been some error. Only used for correct exit() code
        first_command_2_run = True
        for command in commandstorun:
            #if multiple commands in run: reports etc are based on timestamp; so there needs to be at least one second between these runs.
            if first_command_2_run:
                first_command_2_run = False
            else:
                time.sleep(1) 
            botsglobal.logger.info(_(u'Run "%(command)s".'),{'command':command})
            #************get list of routes to run*******************************
            if routestorun:
                use_routestorun = routestorun[:]
                botsglobal.logger.info(_(u'Run routes from command line: "%(routes)s".'),{'routes':unicode(use_routestorun)})
            elif command == 'new':  #fetch all active routes from database unless 'not in default run' or not active.
                use_routestorun = []
                for row in botslib.query('''SELECT DISTINCT idroute
                                            FROM routes
                                            WHERE active=%(active)s
                                            AND (notindefaultrun=%(notindefaultrun)s OR notindefaultrun IS NULL)
                                            ORDER BY idroute ''',
                                            {'active':True,'notindefaultrun':False}):
                    use_routestorun.append(row['idroute'])
                botsglobal.logger.info(_(u'Run active routes from database that are in default run: "%(routes)s".'),{'routes':unicode(use_routestorun)})
            else:   #for command other than 'new': use all active routes.
                use_routestorun = []
                for row in botslib.query('''SELECT DISTINCT idroute
                                            FROM routes
                                            WHERE active=%(active)s
                                            ORDER BY idroute ''',
                                            {'active':True}):
                    use_routestorun.append(row['idroute'])
                botsglobal.logger.info(_(u'Run all active routes from database: "%(routes)s".'),{'routes':unicode(use_routestorun)})
            #************run routes for this command******************************
            botslib.tryrunscript(userscript,scriptname,'pre' + command,routestorun=use_routestorun)
            errorinrun += router.rundispatcher(command,use_routestorun)
            botslib.tryrunscript(userscript,scriptname,'post' + command,routestorun=use_routestorun)
            #*********finished running routes for this command****************************
        #*********finished all commands****************************************
        botslib.tryrunscript(userscript,scriptname,'post',commandstorun=commandstorun,routestorun=routestorun)
        try:    #in acceptance tests: run a user script. no good reporting of errors/results in post-test script. Reason: this is after automaticmaintence.
            botslib.tryrunscript(acceptance_userscript,acceptance_scriptname,'posttest',routestorun=use_routestorun)
        except Exception as msg:
            print unicode(msg)
        
        cleanup.cleanup(do_cleanup_parameter,userscript,scriptname)
    except Exception as msg:
        botsglobal.logger.exception(_(u'Severe error in bots system:\n%(msg)s'),{'msg':unicode(msg)})    #of course this 'should' not happen.
        sys.exit(1)
    else:
        if errorinrun:
            sys.exit(2) #indicate: error(s) in run(s)
        else:
            sys.exit(0) #OK


if __name__ == '__main__':
    start()
