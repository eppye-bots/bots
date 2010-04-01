import os
import sys
import atexit
import traceback
import logging
#import bots-modules
import bots.botslib as botslib
import bots.botsglobal as botsglobal

def showusage():
    print '    Update existing bots database for new release 1.6.0'
    print '    Options:'
    print "        -c<directory>   directory for configuration files (default: config)."
    

def start(botsinifile = 'config'):
    #********command line arguments**************************
    for arg in sys.argv[1:]:
        if not arg:
            continue
        if arg.startswith('-c'):
            botsinifile = arg[2:]
            if not botsinifile:
                print 'Indicated Bots should use specific .ini file but no file name was given.'
                sys.exit(1)
        elif arg in ["?", "/?"] or arg.startswith('-'):
            showusage()
            sys.exit(0)
        else:   #pick up names of routes to run
            showusage()
    #**************initialise configuration file******************************
    try:
        botslib.initconfigurationfile(botsinifile)
        botslib.settimeout(botsglobal.ini.getint('settings','globaltimeout',10))    #
    except:
        traceback.print_exc()
        print 'Error in reading/initializing ini-file.'
        sys.exit(1)
    #**************initialise logging******************************
    try:
        botslib.initlogging()
    except:
        traceback.print_exc()
        print 'Error in initialising logging system.'
        sys.exit(1)
    else:
        atexit.register(logging.shutdown)
    botsglobal.logger.info('Python version: "%s".',sys.version)
    botsglobal.logger.info('Bots configuration file: "%s".',botsinifile)
    botsglobal.logger.info('Bots database configuration file: "%s".',botslib.join('config',os.path.basename(botsglobal.ini.get('directories','tgconfig','botstg.cfg'))))
    #**************connect to database**********************************
    try:
        botslib.connect() 
    except:
        traceback.print_exc()
        print 'Error connecting to database.'
        sys.exit(1)
    else:
        atexit.register(botsglobal.db.close)


    try:
        cursor = botsglobal.db.cursor()
        cursor.execute('''ALTER TABLE routes ADD COLUMN  notindefaultrun BOOLEAN''',None)
        cursor.execute('''ALTER TABLE channel ADD COLUMN  archivepath VARCHAR(256)''',None)
        cursor.execute('''ALTER TABLE partner ADD COLUMN  mail VARCHAR(256)''',None)
        cursor.execute('''ALTER TABLE partner ADD COLUMN  cc VARCHAR(256)''',None)
        cursor.execute('''ALTER TABLE chanpar ADD COLUMN  cc VARCHAR(256)''',None)
        cursor.execute('''ALTER TABLE ta ADD COLUMN  confirmasked BOOLEAN''',None)
        cursor.execute('''ALTER TABLE ta ADD COLUMN  confirmed BOOLEAN''',None)
        cursor.execute('''ALTER TABLE ta ADD COLUMN  confirmtype VARCHAR(35) DEFAULT '' ''',None)
        cursor.execute('''ALTER TABLE ta ADD COLUMN  confirmidta INTEGER DEFAULT 0''',None)
        cursor.execute('''ALTER TABLE ta ADD COLUMN  envelope VARCHAR(35) DEFAULT '' ''',None)
        cursor.execute('''ALTER TABLE ta ADD COLUMN  botskey VARCHAR(35) DEFAULT '' ''',None)
        cursor.execute('''ALTER TABLE ta ADD COLUMN  cc VARCHAR(512) DEFAULT '' ''',None)
        if botsglobal.dbinfo.drivername == 'mysql':
            cursor.execute('''ALTER TABLE ta MODIFY errortext VARCHAR(2048)''',None)
        elif botsglobal.dbinfo.drivername == 'postgres':
            cursor.execute('''ALTER TABLE ta ALTER COLUMN errortext type VARCHAR(2048)''',None)
        #else: #sqlite does not allow modifying existing field, but does not check lentghs either so this works.
        cursor.execute('''CREATE TABLE confirmrule (
                            id INTEGER PRIMARY KEY,
                            active BOOLEAN,
                            confirmtype VARCHAR(35),
                            ruletype VARCHAR(35),
                            negativerule BOOLEAN,
                            frompartner VARCHAR(35),
                            topartner VARCHAR(35),
                            idchannel VARCHAR(35),
                            idroute VARCHAR(35),
                            editype VARCHAR(35),
                            messagetype VARCHAR(35) )
                            ''',None)
    except:
        traceback.print_exc()
        print 'Error while updating the database. Database is not updated.'
        botsglobal.db.rollback()
        sys.exit(1)
        
    botsglobal.db.commit()
    cursor.close()
    print 'Database is updated.'
    sys.exit(0)
    