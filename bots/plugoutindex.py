#!/usr/bin/env python
import sys
import os
import botsinit
import botsglobal

def showusage():
    usage = '''
    This is "%(name)s", a part of Bots open source edi translator - http://bots.sourceforge.net.
    The %(name)s is a seperate utility to generate the index file of a plugin; this can be seen as a database dump of the configuration.
    This is eg useful for version control.
    index filename is eg bots/usersys/index.py'
    Usage:
        %(name)s  -c<directory>
    Options:
        -c<directory>   directory for configuration files (default: config).
    '''%{'name':os.path.basename(sys.argv[0])}
    print usage
    sys.exit(0)

def start():
    #NOTE bots is always on PYTHONPATH!!! - otherwise it will not start.
    #***command line arguments**************************
    configdir = 'config'
    for arg in sys.argv[1:]:
        if not arg:
            continue
        if arg.startswith('-c'):
            configdir = arg[2:]
            if not configdir:
                print 'Configuration directory indicated, but no directory name.'
                sys.exit(1)
        elif arg in ["?", "/?"] or arg.startswith('-'):
            showusage()
        else:
            showusage()

    #***init general: find locating of bots, configfiles, init paths etc.***********************
    botsinit.generalinit(configdir)

    import pluglib
    usersys = botsglobal.ini.get('directories','usersysabs')
    index_filename = os.path.join(usersys,'index.py')
    filehandler = open(index_filename,'w')
    filehandler.write(pluglib.plugoutindex())
    filehandler.close()
    


if __name__ == '__main__':
    start()
