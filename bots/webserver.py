#!/usr/bin/env python
import sys
import os
import logging,logging.handlers
import django
from django.core.handlers.wsgi import WSGIHandler
from django.core.servers.basehttp import AdminMediaHandler
from django.utils.translation import ugettext as _
import cherrypy
from cherrypy import wsgiserver
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

class Dummyclass(object):
    ''' dummy class needed by cherrypy for serving static files.'''
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

    #initialise logging. This logging only contains the logging from bots-webserver, not from cherrypy.
    botsglobal.logger = logging.getLogger('bots-webserver')
    botsglobal.logger.setLevel(logging.DEBUG)
    h = logging.handlers.TimedRotatingFileHandler(botslib.join(botsglobal.ini.get('directories','logging'),'webserver.log'), backupCount=10)
    fileformat = logging.Formatter("%(asctime)s %(levelname)-8s: %(message)s",'%Y%m%d %H:%M:%S')
    h.setFormatter(fileformat)
    botsglobal.logger.addHandler(h)
    
    #**********init cherrypy as webserver*********************************************
    #set global configuration options for cherrypy
    cherrypy.config.update({'global': { 'log.screen': False, 'server.environment': botsglobal.ini.get('webserver','environment','development')}})
    #set the cherrypy handling of static files
    conf = {'/': {'tools.staticdir.on' : True,'tools.staticdir.dir' : 'media' ,'tools.staticdir.root': botsglobal.ini.get('directories','botspath')}}
    servestaticfiles = cherrypy.tree.mount(Dummyclass(), '/media', conf)    #myroot is needed to set logging 
    #cherrypy uses a dispatcher in order to handle the serving of static files and django.
    dispatcher = wsgiserver.WSGIPathInfoDispatcher({'/': AdminMediaHandler(WSGIHandler()), '/media': servestaticfiles})
    botswebserver = wsgiserver.CherryPyWSGIServer(('0.0.0.0', botsglobal.ini.getint('webserver','port',8080)), dispatcher)
    
    botsglobal.logger.info(_(u'Bots web server started.'))
    #handle ssl in webserver:
    ssl_certificate = botsglobal.ini.get('webserver','ssl_certificate',None)
    ssl_private_key = botsglobal.ini.get('webserver','ssl_private_key',None)
    if ssl_certificate and ssl_private_key:
        botswebserver.ssl_module = 'builtin'            #in cherrypy > 3.1, this has no result (but does no harm)
        botswebserver.ssl_certificate = '/home/hje/testcert/mycert.pem'
        botswebserver.ssl_private_key = '/home/hje/testcert/mycert.pem'
        botsglobal.logger.info(_(u'Bots web server uses ssl (https).'))
    else:
        botsglobal.logger.info(_(u'Bots web server uses plain http (no ssl).'))
    
    #start the cherrypy webserver.
    try:
        botswebserver.start()
    except KeyboardInterrupt:
        botswebserver.stop()


if __name__=='__main__':
    start()
