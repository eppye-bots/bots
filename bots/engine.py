#!/usr/bin/env python
''' Start bots-engine.'''
import sys
import os
import atexit
import logging
import socket
from django.utils.translation import ugettext as _
#bots-modules
import botslib
import botsinit
import botsglobal
import router
import cleanup


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
    cleanupcommand = False
    for arg in sys.argv[1:]:
        if arg.startswith('-c'):
            configdir = arg[2:]
            if not configdir:
                print 'Error: configuration directory indicated, but no directory name.'
                sys.exit(1)
        elif arg in commandspossible:
            commandstorun.append(arg)
        elif arg == '--cleanup':
            cleanupcommand = True
        elif arg in ["?", "/?",'-h', '--help'] or arg.startswith('-'):
            print usage
            sys.exit(0)
        else:   #pick up names of routes to run
            routestorun.append(arg)
    if not commandstorun:   #if no command on command line, use new (default)
        commandstorun = ['--new']
    commandstorun = [command[2:] for command in commandspossible if command in commandstorun]   #sort commands
    #***end handling command line arguments**************************
    botsinit.generalinit(configdir)     #find locating of bots, configfiles, init paths etc.

    #**************check if another instance of bots-engine is running/if port is free******************************
    try:
        my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port = botsglobal.ini.getint('settings','port',35636)
        my_socket.bind(('127.0.0.1', port))
    except socket.error:
        my_socket.close()
        sys.exit(3)
    else:
        atexit.register(my_socket.close)

    #**************initialise logging******************************
    process_name = 'engine'
    botsglobal.logger = botsinit.initenginelogging(process_name)
    atexit.register(logging.shutdown)
    for key,value in botslib.botsinfo():    #log info about environement, versions, etc
        botsglobal.logger.info(u'%s: "%s".',key,value)

    #**************connect to database**********************************
    try:
        botsinit.connect()
    except Exception,msg:
        botsglobal.logger.exception(_(u'Could not connect to database. Database settings are in bots/config/settings.py. Error: "%s".'),msg)
        sys.exit(1)
    else:
        botsglobal.logger.info(_(u'Connected to database.'))
        atexit.register(botsglobal.db.close)
    #initialise user exits for the whole bots-engine
    try:
        userscript,scriptname = botslib.botsimport('routescripts','botsengine')
    except ImportError:      #userscript is not there; other errors like syntax errors are not catched
        userscript = scriptname = None

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
    #**************run the routes**********************************************
    #commandstorun determines the type(s) of run. eg: ['automaticretrycommunication','new']
    #for each command: run all routes
    #    for each route: run all seq
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
                                            ORDER BY idroute '''):
                    use_routestorun.append(row['idroute'])
                botsglobal.logger.info(_(u'Run all active routes from database: "%s".'),str(use_routestorun))
            errorinrun += router.rundispatcher(command,use_routestorun)
            if userscript and hasattr(userscript,'post' + command):
                botslib.runscript(userscript,scriptname,'post' + command,routestorun=use_routestorun)
        if cleanupcommand or botsglobal.ini.get('settings','whencleanup','always')=='always':
            cleanup.cleanup()
            botsglobal.logger.info(u'Done cleanup.')
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

