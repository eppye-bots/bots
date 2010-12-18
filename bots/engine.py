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
from django.utils.translation import ugettext as _
#bots-modules
import botslib
import botsinit
import botsglobal
import router
import automaticmaintenance
import cleanup
from botsconfig import *


def showusage():
    usage = '''
    This is "%(name)s", a part of Bots open source EDI translator - http://bots.sourceforge.net.
    The %(name)s does the actual translations and communications; it's the workhorse. It does not have a fancy interface.
    Usage:
        %(name)s  [run-options] [config-option] [routes]

    Run-options (can be combined, except for crashrecovery):
        --new                recieve new edi files (default: if no run-option given: run as new).
        --retransmit         resend and rerececieve as indicated by user.
        --retry              retry previous errors.
        --crashrecovery      reruns the run where the crash occurred. (when database is locked).
        --automaticretrycommunication - automatically retry outgoing communication.
        --retrycommunication retry outgoing communication process errors as indicated by user.
        --cleanup            remove older data from database.
    Config-option:
        -c<directory>        directory for configuration files (default: config).
    Routes: list of routes to run. Default: all active routes (in the database)

    '''%{'name':os.path.basename(sys.argv[0])}
    print usage
    
def start():
    #********command line arguments**************************
    commandspossible = ['--new','--retry','--retransmit','--cleanup','--crashrecovery','--retrycommunication','--automaticretrycommunication']
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
    if not commandstorun:   #if no command on command line, use new (default)
        commandstorun = ['--new']
    #**************init general: find locating of bots, configfiles, init paths etc.****************
    botsinit.generalinit(configdir)
    #set current working directory to botspath
    #~ old_current_directory = os.getcwdu()
    os.chdir(botsglobal.ini.get('directories','botspath'))
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
    #**************handle database lock****************************************
    #try to set a lock on the database; if this is not possible, the database is already locked. Either:
    #1 another instance bots bots-engine is (still) running
    #2 or bots-engine had a severe crash.
    #What to do? 
    #first: check ts of database lock. If below a certain value (set in bots.ini) we assume an other instance is running. Exit quietly - no errors, no logging.
    #                                  else: Warn user, give advise on what to do. gather data: nr files in, errors.
    #next:  warn with report & logging. advise a crashrecovery.
    if not botslib.set_database_lock():
        if '--crashrecovery' in commandstorun:    #user starts recovery operation; the databaselock is ignored; the databaselock is unlocked when routes have run.
            commandstorun = ['--crashrecovery']  #is an exclusive option!
        else:
            #when scheduling bots it is possible that the last run is still running. Check if maxruntime has passed:
            vanaf = datetime.datetime.today() - datetime.timedelta(minutes=botsglobal.ini.getint('settings','maxruntime',60))
            for row in botslib.query('''SELECT ts FROM mutex WHERE ts < %(vanaf)s ''',{'vanaf':vanaf}):
                warn = _(u'!Bots database is locked!\nBots-engine has ended in an unexpected way during the last run.\nThis happens, but is very very rare.\nPossible causes: bots-engine terminated by user, system crash, power-down, etc.\nA forced retry of the last run is advised; bots will (try to) repair the last run.')
                botsglobal.logger.critical(warn)
                botslib.sendbotserrorreport(_(u'[Bots severe error]Database is locked'),warn)
                #add: count errors etc.
                sys.exit(1)
            else:   #maxruntime has not passed. Exit silently, nothing reported
                botsglobal.logger.info(_(u'Database is locked, but "maxruntime" has not been exceeded.'))
                exit(0)
    else:
        if '--crashrecovery' in commandstorun:    #user starts recovery operation but there is no databaselock.
            warn = _(u'User started a forced retry of the last run.\nOnly use this when the database is locked.\nThe database was not locked (database is OK).\nSo Bots has done nothing now.')
            botsglobal.logger.error(warn)
            botslib.sendbotserrorreport(_(u'[Bots Error Report] User started a forced retry of last run, but this was not needed'),warn)
            botslib.remove_database_lock()
            sys.exit(1)
            
    #*************get list of routes to run****************************************
    #~ raise Exception('locked database')       #for testing database lock: abort, database will be locked
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
        botsglobal.logger.info(_(u'Run active routes from database: "%s".'),str(routestorun))
    #routestorun is now either a list with routes from comandline, or the list of active routes for the routes tabel in the db.
    #**************run the routes for retry, retransmit and new runs*************************************
    try: 
        #commandstorun determines the type(s) of run
        #routes to run is a listof the routes that are runs (for each command to run
        #botsglobal.incommunicate is used to control if there is communication in; only 'new' incommunicates.
        #botsglobal.minta4query controls which ta's are queried by the routes.
        #stuff2evaluate controls what is evaluated in automatic maintenance.
        #~ timer = botslib.Timer('../timer.txt')
        errorinrun = 0      #detect if there has been some error. Only used for good exit() code
        botsglobal.incommunicate = False
        if '--crashrecovery' in commandstorun:
            botsglobal.logger.info(_(u'Run crash recovery.'))
            stuff2evaluate = botslib.set_minta4query_crashrecovery()
            if stuff2evaluate:
                router.routedispatcher(routestorun)
                errorinrun +=  automaticmaintenance.evaluate('--crashrecovery',stuff2evaluate)
            else:
                botsglobal.logger.info(_(u'No retry of the last run - there was no last run.'))
        if '--retrycommunication' in commandstorun:
            botsglobal.logger.info(_(u'Run communication retry.'))
            stuff2evaluate = router.routedispatcher(routestorun,'--retrycommunication')
            if stuff2evaluate:
                errorinrun +=  automaticmaintenance.evaluate('--retrycommunication',stuff2evaluate)
            else:
                botsglobal.logger.info(_(u'Run recommunicate: nothing to recommunicate.'))
        if '--automaticretrycommunication' in commandstorun:
            botsglobal.logger.info(_(u'Run automatic communication retry.'))
            stuff2evaluate = router.routedispatcher(routestorun,'--automaticretrycommunication')
            if stuff2evaluate:
                errorinrun +=  automaticmaintenance.evaluate('--automaticretrycommunication',stuff2evaluate)
            else:
                botsglobal.logger.info(_(u'Run automatic recommunicate: nothing to recommunicate.'))
        #~ if '--retry' in commandstorun:
            #~ botsglobal.logger.info(u'Run retry.')
            #~ if botslib.set_minta4query_retry():
                #~ stuff2evaluate = router.routedispatcher(routestorun)
                #~ errorinrun +=  automaticmaintenance.evaluate('--retry',stuff2evaluate)
            #~ else:
                #~ botsglobal.logger.info(_(u'Run retry: nothing to retry.'))
        if '--retry' in commandstorun:
            botsglobal.logger.info(u'Run retry.')
            stuff2evaluate = router.routedispatcher(routestorun,'--retry')
            if stuff2evaluate:
                errorinrun +=  automaticmaintenance.evaluate('--retry',stuff2evaluate)
            else:
                botsglobal.logger.info(_(u'Run retry: nothing to retry.'))
        if '--retransmit' in commandstorun:
            botsglobal.logger.info(u'Run retransmit.')
            stuff2evaluate = router.routedispatcher(routestorun,'--retransmit')
            if stuff2evaluate:
                errorinrun +=  automaticmaintenance.evaluate('--retransmit',stuff2evaluate)
            else:
                botsglobal.logger.info(_(u'Run retransmit: nothing to retransmit.'))
        if '--new' in commandstorun:
            botsglobal.logger.info('Run new.')
            botsglobal.incommunicate = True
            botsglobal.minta4query = 0  #meaning: reset. the actual value is set later (in routedispatcher)
            stuff2evaluate = router.routedispatcher(routestorun)
            errorinrun +=  automaticmaintenance.evaluate('--new',stuff2evaluate)
        if '--cleanup' in commandstorun or botsglobal.ini.get('settings','whencleanup','always')=='always':
            botsglobal.logger.debug(u'Do cleanup.')
            cleanup.cleanup()
        #~ timer.point('cleanup')
        #~ timer.close()
        botslib.remove_database_lock()
    except Exception,e:
        botsglobal.logger.exception(_(u'Severe error in bots system: "%s".')%(e))    #of course this 'should' not happen. 
        sys.exit(1)
    else:
        if errorinrun:
            sys.exit(2) #indicate: error(s) in run(s)
        else:
            sys.exit(0) #OK
            
        
if __name__=='__main__':
    start()

