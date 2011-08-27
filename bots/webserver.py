#!/usr/bin/env python
import sys
import os
import logging,logging.handlers
import django
from django.core.handlers.wsgi import WSGIHandler
from django.core.servers.basehttp import AdminMediaHandler     
from django.utils.translation import ugettext as _
import cherrypy
import botslib
import botsglobal
import botsinit

def showusage():
    usage = '''
    This is "%(name)s", a part of Bots open source EDI translator - http://bots.sourceforge.net.
    The %(name)s is the web server for bots; the interface (bots-monitor) can be accessed in a browser, eg 'http://localhost:8080'.
    Usage:
        %(name)s  -c<directory>
    Options:
        -c<directory>   directory for configuration files (default: config).
    '''%{'name':os.path.basename(sys.argv[0])}
    print usage
    sys.exit(0)

class Root(object):
    ''' dummy class needed by cherrypy.'''
    pass

def start():
    #NOTE bots is always on PYTHONPATH!!! - otherwise it will not start.
    #********command line arguments**************************
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
    
    #init general: find locating of bots, configfiles, init paths etc.***********************
    botsinit.generalinit(configdir)

    #init cherrypy; only needed for webserver. *********************************************
    cherrypy.config.update({'global': { 'tools.staticdir.root': botsglobal.ini.get('directories','botspath'),
                                        'server.socket_host' : "0.0.0.0",       #to what IP addresses should be server. 0.0.0.0: all. See cherrypy docs
                                        'server.socket_port': botsglobal.ini.getint('webserver','port',8080),
                                        'server.environment': botsglobal.ini.get('webserver','environment','development'),    # development production
                                        'log.screen': False,
                                        #~ 'log.error_file': '',    #set later to rotating log file
                                        #~ 'log.access_file': '',    #set later to rotating log file
                                        }})
    conf = {'/': {'tools.staticdir.on' : True,'tools.staticdir.dir' : 'media' }}
            #~ '/favicon.ico': {'tools.staticfile.on': True,'tools.staticfile.filename': '/home/hje/botsup-django/bots/media/images/favicon.ico'}}
    cherrypy.tree.graft(AdminMediaHandler(WSGIHandler()), '/')
    myroot = Root()
    myappl = cherrypy.tree.mount(myroot, '/media', conf)    #myappl is needed to set logging 



    botsglobal.logger = logging.getLogger('webserver')
    botsglobal.logger.setLevel(logging.DEBUG)
    h = logging.handlers.TimedRotatingFileHandler(botslib.join(botsglobal.ini.get('directories','logging'),'webserver.log'),when='midnight', backupCount=10)
    fileformat = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s : %(message)s",'%Y%m%d %H:%M:%S')
    h.setFormatter(fileformat)
    # add rotating file handler to main logger
    botsglobal.logger.addHandler(h)
    



    # Make RotatingFileHandler for the error log.
    #~ h = logging.handlers.TimedRotatingFileHandler(botslib.join(botsglobal.ini.get('directories','logging'),'webserver.log'),when='midnight', backupCount=10)
    #~ fileformat = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s : %(message)s",'%Y%m%d %H:%M:%S')
    #~ h.setLevel(logging.INFO)
    #~ h.setFormatter(fileformat)
    #~ myappl.log.error_log.addHandler(h)

    # MakeRotatingFileHandler for the access log.
    #~ h = logging.handlers.TimedRotatingFileHandler(os.path.normpath(os.path.join(botsglobal.ini.get('directories','botspath'), 'botssys/logging/webserver.log')),when='midnight', backupCount=10)
    #~ h.setLevel(logging.DEBUG)
    #~ myappl.log.access_log.addHandler(h)
    #~ botsglobal.logger = myappl.log.access_log 
    
    #write start info to cherrypy log********************************************
    botsglobal.logger.info(_(u'Bots web server started.'))
    botsglobal.logger.info(_(u'Python version: "%s".'),sys.version)
    botsglobal.logger.info(_(u'Django version: "%s".'),django.VERSION)
    
    #start cherrypy *********************************************************************
    cherrypy.engine.start()
    cherrypy.engine.block()
        
if __name__=='__main__':
    start()
