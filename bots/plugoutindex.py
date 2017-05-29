#!/usr/bin/env python
import sys
import os
import botsinit
import botsglobal


def start():
    #NOTE: bots directory should always be on PYTHONPATH - otherwise it will not start.
    #***command line arguments**************************
    usage = '''
    This is "%(name)s" version %(version)s, part of Bots open source edi translator (http://bots.sourceforge.net).
    A utility to generate the index file of a plugin; this can be seen as a database dump of the configuration.
    This is eg useful for version control.
    Usage:
        %(name)s  -c<directory>
    Options:
        -c<directory>   directory for configuration files (default: config).
        
    '''%{'name':os.path.basename(sys.argv[0]),'version':botsglobal.version}
    configdir = 'config'
    for arg in sys.argv[1:]:
        if arg.startswith('-c'):
            configdir = arg[2:]
            if not configdir:
                print 'Error: configuration directory indicated, but no directory name.'
                sys.exit(1)
        else:
            print usage
            sys.exit(0)
    #***end handling command line arguments**************************
    botsinit.generalinit(configdir)     #find locating of bots, configfiles, init paths etc.
    import pluglib              #import here, import at start of file gives error; first initialize.
    usersys = botsglobal.ini.get('directories','usersysabs')
    index_filename = os.path.join(usersys,'index.py')
    dummy_for_cleaned_data = {'databaseconfiguration':True,'umlists':botsglobal.ini.getboolean('settings','codelists_in_plugin',True),'databasetransactions':False}
    pluglib.make_index(dummy_for_cleaned_data,index_filename)
    

if __name__ == '__main__':
    start()
