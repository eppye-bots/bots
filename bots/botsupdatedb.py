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

def sqlite_database_is_version3():
    for row in botslib.query('''PRAGMA table_info(routes)'''):
        if row['name'] == 'translateind':
            if row['type'] == 'bool':
                return False
            else:
                return True
    raise Exception('Could determine version of database')

def sqlite_change_translateind():
    querystring = '''
PRAGMA writable_schema = 1;
UPDATE SQLITE_MASTER SET SQL = 
'CREATE TABLE "routes" (
    "id" integer NOT NULL PRIMARY KEY,
    "idroute" varchar(35) NOT NULL,
    "seq" integer unsigned NOT NULL,
    "active" bool NOT NULL,
    "fromchannel_id" varchar(35) REFERENCES "channel" ("idchannel"),
    "fromeditype" varchar(35) NOT NULL,
    "frommessagetype" varchar(35) NOT NULL,
    "tochannel_id" varchar(35) REFERENCES "channel" ("idchannel"),
    "toeditype" varchar(35) NOT NULL,
    "tomessagetype" varchar(35) NOT NULL,
    "alt" varchar(35) NOT NULL,
    "frompartner_id" varchar(35) REFERENCES "partner" ("idpartner"),
    "topartner_id" varchar(35) REFERENCES "partner" ("idpartner"),
    "frompartner_tochannel_id" varchar(35) REFERENCES "partner" ("idpartner"),
    "topartner_tochannel_id" varchar(35) REFERENCES "partner" ("idpartner"),
    "testindicator" varchar(1) NOT NULL,
    "translateind" integer NOT NULL,
    "notindefaultrun" bool NOT NULL,
    "desc" text,
    "rsrv1" varchar(35),
    "rsrv2" integer,
    "defer" bool NOT NULL,
    UNIQUE ("idroute", "seq"))' 
WHERE NAME = 'routes';
PRAGMA writable_schema = 0;
'''
    cursor = botsglobal.db.cursor()
    try:
        cursor.executescript(querystring)
    except:
        txt = botslib.txtexc()
        raise Exception('Could not change schema for routes: "%s".',txt)
    else:
        botsglobal.db.commit()
        cursor.close()

def sqlite3():
    if sqlite_database_is_version3():
        print 'database is already for bots version 3.'
        return
    else:
        print 'change bots database to version 3.'
        sqlite_change_translateind()
            
        #have to close & open database to activate changed schema for routes:
        botsglobal.db.close()
        botsinit.connect()
        
        cursor = botsglobal.db.cursor()
        try:
            #report ****************************************
            cursor.execute('''CREATE INDEX report_ts ON report (ts)''')     #SQLite, mySQL, postgreSQL
            cursor.execute('''ALTER TABLE report ADD COLUMN  filesize INTEGER DEFAULT 0''',None)
            #routes ****************************************
            cursor.execute('''ALTER TABLE routes ADD COLUMN  zip_incoming INTEGER DEFAULT 0''',None)
            cursor.execute('''ALTER TABLE routes ADD COLUMN  zip_outgoing INTEGER DEFAULT 0''',None)
            #channel ****************************************
            cursor.execute('''ALTER TABLE channel ADD COLUMN  rsrv3 INTEGER DEFAULT 0''',None)
            #ta ****************************************
            cursor.execute('''DROP INDEX ta_script''')   #sqlite, postgreSQL
            cursor.execute('''CREATE INDEX ta_reference ON ta (reference)''')     #SQLite, mySQL, postgreSQL
            cursor.execute('''ALTER TABLE ta ADD COLUMN  filesize INTEGER DEFAULT 0''',None)
            cursor.execute('''ALTER TABLE ta ADD COLUMN  numberofresends INTEGER DEFAULT 0''',None)
            cursor.execute('''ALTER TABLE ta ADD COLUMN  rsrv5 VARCHAR(35) DEFAULT '' ''',None)
            #filereport ****************************************
            cursor.execute('''DROP INDEX filereport_reportidta''')   #sqlite, postgreSQL
            cursor.execute('''ALTER TABLE filereport ADD COLUMN  filesize INTEGER DEFAULT 0''',None)
        except:
            txt = botslib.txtexc()
            botsglobal.db.rollback()
            print 'Error while updating the database: "%s".'%(txt)
        else:
            botsglobal.db.commit()
            cursor.close()
            print 'Database is updated.'

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

    if hasattr(botsglobal.settings,'DATABASE_ENGINE'):
        if botsglobal.settings.DATABASE_ENGINE == 'sqlite3':
            sqlite3()
        elif botsglobal.settings.DATABASE_ENGINE == 'mysql':
            mysql()
        elif botsglobal.settings.DATABASE_ENGINE == 'postgresql_psycopg2':
            postgresql_psycopg2()
    elif hasattr(botsglobal.settings,'DATABASES'):
        if botsglobal.settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
            sqlite3()
        elif botsglobal.settings.DATABASES['default']['ENGINE'] == 'django.db.backends.mysql':
            mysql()
        elif botsglobal.settings.DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql_psycopg2':
            postgresql_psycopg2()
    
    sys.exit(0)


if __name__ == '__main__':
    start()

