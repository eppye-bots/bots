import sys
import os
import atexit
import logging
import socket
#bots-modules
import botslib
import botsinit
import botsglobal


def start():
    #********command line arguments**************************
    usage = '''
    This is "%(name)s" version %(version)s, part of Bots open source edi translator (http://bots.sourceforge.net).
    Updates existing bots database to version %(version)s

    Usage:
        %(name)s  [config-option]
    Options:
        -c<directory>        directory for configuration files (default: config).

    '''%{'name':os.path.basename(sys.argv[0]),'version':botsglobal.version}
    configdir = 'config'
    for arg in sys.argv[1:]:
        if arg.startswith('-c'):
            configdir = arg[2:]
            if not configdir:
                print 'Error: configuration directory indicated, but no directory name.'
                sys.exit(1)
        else:   #pick up names of routes to run
            print usage
            sys.exit(0)
    #***end handling command line arguments**************************
    botsinit.generalinit(configdir)     #find locating of bots, configfiles, init paths etc.

    #**************check if another instance of bots-engine is running/if port is free******************************
    try:
        engine_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port = botsglobal.ini.getint('settings','port',35636)
        engine_socket.bind(('127.0.0.1', port))
    except socket.error:
        engine_socket.close()
        sys.exit(3)
    else:
        atexit.register(engine_socket.close)

    #**************initialise logging******************************
    process_name = 'updatedatabase'
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
        warn =  _(u'!Bots database is locked!\n'\
                    'Bots-engine has ended in an unexpected way during the last run.\n'\
                    'Most likely causes: sudden power-down, system crash, problems with disk I/O, bots-engine terminated by user, etc.')
        botsglobal.logger.critical(warn)
        sys.exit(3)
    atexit.register(botslib.remove_database_lock)


    try:
        cursor = botsglobal.db.cursor()
        
        #report
        cursor.execute('''CREATE INDEX report_ts ON report (ts)''')     #SQLite, mySQL, postgreSQL
        
        #for SQLite: but this is not possible in SQLite
        #mutex;
        #cursor.execute('''DROP TRIGGER uselocaltime_mutex''')    #sqlite only
        #cursor.execute('''ALTER TABLE mutex MODIFY ts timestamp NOT NULL DEFAULT (datetime('now','localtime'))''')     #change only for sqlite but does not work!
        
        #persist
        cursor.execute('''ALTER TABLE persist MODIFY content TEXT''')     #mySQL, postgreSQL, not needed for SQLite
        #cursor.execute('''ALTER TABLE persist MODIFY ts timestamp NOT NULL DEFAULT (datetime('now','localtime'))''')     #change only for sqlite but does not work!
        
        #channel
        cursor.execute('''ALTER TABLE channel MODIFY filename varchar(256) NOT NULL''')     #mySQL, postgreSQL, not needed for SQLite

        #ta
        #cursor.execute('''DROP TRIGGER uselocaltime''')    #sqlite only
        #cursor.execute('''ALTER TABLE ta MODIFY ts timestamp NOT NULL DEFAULT (datetime('now','localtime'))''')     #change only for sqlite but does not work!
        cursor.execute('''DROP INDEX ta_script''')   #sqlite, postgreSQL
        cursor.execute('''CREATE INDEX ta_reference ON ta (reference)''')     #SQLite, mySQL, postgreSQL
        cursor.execute('''ALTER TABLE ta MODIFY errortext TEXT ''')     #mySQL, postgreSQL, not needed for SQLite
        
        #filereport
        #postgresql only
        cursor.execute('''ALTER TABLE filereport DROP CONSTRAINT filereport_pkey''')      #remove primary key
        cursor.execute('''ALTER TABLE filereport DROP CONSTRAINT filereport_idta_key''')  #drop contraint UNIQUE(idta, reportidta)
        cursor.execute('''DROP INDEX filereport_idta''')                                  #drop index on idta (will be primary key)
        cursor.execute('''ALTER TABLE filereport ADD CONSTRAINT filereport_pkey PRIMARY KEY(idta)''')    #idta is primary key
        #end of postgresql only
        
        cursor.execute('''ALTER TABLE filereport DROP COLUMN id''')        #SQLite, mySQL, postgreSQL; is this possible? was primary key...     
        cursor.execute('''DROP INDEX filereport_reportidta''')   #sqlite, postgreSQL
        cursor.execute('''DROP INDEX reportidta on filereport''') #mySQL
        #drop contraint UNIQUE(idta, reportidta) fro MySQL? see postgresql section
        
        cursor.execute('''ALTER TABLE filereport MODIFY errortext TEXT''')     #mySQL, postgreSQL, not needed for SQLite
        
        
    except:
        traceback.print_exc()
        print 'Error while updating the database. Database is not updated.'
        botsglobal.db.rollback()
        sys.exit(1)
        
    botsglobal.db.commit()
    cursor.close()
    print 'Database is updated.'
    sys.exit(0)


if __name__ == '__main__':
    start()

