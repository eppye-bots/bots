#!/usr/bin/env python
import sys
import os
import logging,logging.handlers
import django
from django.core.handlers.wsgi import WSGIHandler
from django.core.servers.basehttp import AdminMediaHandler     
import cherrypy
import botsglobal
import botsinit

def showusage():
    print
    print '    Usage:  %s  -c<directory> '%os.path.basename(sys.argv[0])
    print
    print '    Start the bots web server.'
    print '    Options:'
    print "        -c<directory>   directory for configuration files (default: config)."
    print
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
                print 'You indicated Bots should use specific config directory but no path was given.'
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

    # Make RotatingFileHandler for the error log.
    h = logging.handlers.TimedRotatingFileHandler(os.path.normpath(os.path.join(botsglobal.ini.get('directories','botspath'), botsglobal.ini.get('directories','logging'),'webserver.log')),when='midnight', backupCount=10)
    #~ fileformat = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s : %(message)s",'%Y%m%d %H:%M:%S')
    h.setLevel(logging.INFO)
    #~ h.setFormatter(fileformat)
    myappl.log.error_log.addHandler(h)

    # MakeRotatingFileHandler for the access log.
    #~ h = logging.handlers.TimedRotatingFileHandler(os.path.normpath(os.path.join(botsglobal.ini.get('directories','botspath'), 'botssys/logging/webserver.log')),when='midnight', backupCount=10)
    #~ h.setLevel(logging.DEBUG)
    myappl.log.access_log.addHandler(h)
    botsglobal.logger = myappl.log.access_log 
    
    #write start info to cherrypy log********************************************
    botsglobal.logger.info(u'Bots web server started.')
    botsglobal.logger.info(u'Python version: "%s".',sys.version)
    botsglobal.logger.info(u'Django version: "%s".',django.VERSION)
    
    #start cherrypy *********************************************************************
    if hasattr(cherrypy.engine, 'block'):
        # 3.1 syntax
        cherrypy.engine.start()
        cherrypy.engine.block()
    else:
        # 3.0 syntax
        cherrypy.server.quickstart()
        cherrypy.engine.start()
