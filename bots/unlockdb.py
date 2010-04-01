import sys
import os
import traceback
import atexit
#import bots-modules
import bots.botslib as botslib
import bots.botsglobal as botsglobal

def showusage():
    print
    print '    Usage:  %s  -c<directory> '%os.path.basename(sys.argv[0])
    print
    print '    Unlock the bots database.'
    print '    Options:'
    print "        -c<ini-file>   directory for configuration files (default: config)."
    print
    sys.exit(0)

def start():
    #********command line arguments**************************
    botsinifile = 'config'
    for arg in sys.argv[1:]:
        if not arg:
            continue
        if arg.startswith('-c'):
            botsinifile = arg[2:]
            if not botsinifile:
                print '    !!Indicated Bots should use specific .ini file but no file name was given.'
                showusage()
        elif arg in ["?", "/?"] or arg.startswith('-'):
            showusage()
        else:
            showusage()
    #********end handling command line arguments**************************

    try:
        botslib.initconfigurationfile(botsinifile)
        botslib.initlogging()
    except:
        print 'Error while initialising (before database connection).'
        traceback.print_exc()
        sys.exit(1)
    try:
        botslib.connect()   #init db-connectie;
    except:
        print 'Error connecting to database'
        traceback.print_exc()
        sys.exit(1)
    else:
        atexit.register(botsglobal.db.close)
    try:
        botslib.change('''UPDATE mutex SET mutexer = 0 WHERE mutexk=0''')
        print 'Bots database unlocked.'
    except:
        print 'Bots database unlocking failed.'
        sys.exit(1)
    else:
        sys.exit(0)

