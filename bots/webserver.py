#!/usr/bin/env python
import sys
import os
import django
from django.core.handlers.wsgi import WSGIHandler
from django.utils.translation import ugettext as _
import cherrypy
from cherrypy import wsgiserver
import botsglobal
import botsinit


def start():
    #NOTE: bots directory should always be on PYTHONPATH - otherwise it will not start.
    #***command line arguments**************************
    usage = '''
    This is "%(name)s" version %(version)s, part of Bots open source edi translator (http://bots.sourceforge.net).
    The %(name)s is the web server for bots; the interface (bots-monitor) can be accessed in a 
    browser, eg 'http://localhost:8080'.
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
    process_name = 'webserver'
    botsglobal.logger = botsinit.initserverlogging(process_name)    #initialise file-logging for web-server. This logging only contains the logging from bots-webserver, not from cherrypy.

    #***init cherrypy as webserver*********************************************
    #global configuration for cherrypy
    cherrypy.config.update({'global': {'log.screen': False, 'server.environment': botsglobal.ini.get('webserver','environment','production')}})
    #cherrypy handling of static files
    conf = {'/': {'tools.staticdir.on' : True,'tools.staticdir.dir' : 'media' ,'tools.staticdir.root': botsglobal.ini.get('directories','botspath')}}
    servestaticfiles = cherrypy.tree.mount(None, '/media', conf)    #None: no cherrypy application (as this only serves static files)
    #cherrypy handling of django
    servedjango = WSGIHandler()     #was: servedjango = AdminMediaHandler(WSGIHandler())  but django does not need the AdminMediaHandler in this setup. is much faster.
    #cherrypy uses a dispatcher in order to handle the serving of static files and django.
    dispatcher = wsgiserver.WSGIPathInfoDispatcher({'/': servedjango, '/media': servestaticfiles})
    botswebserver = wsgiserver.CherryPyWSGIServer(bind_addr=('0.0.0.0', botsglobal.ini.getint('webserver','port',8080)), wsgi_app=dispatcher, server_name=botsglobal.ini.get('webserver','name','bots-webserver'))
    botsglobal.logger.log(25,_(u'Bots %(process_name)s started.'),
                                {'process_name':process_name})
    botsglobal.logger.log(25,_(u'Bots %(process_name)s configdir: "%(configdir)s".'),
                                {'process_name':process_name, 'configdir':botsglobal.ini.get('directories','config')})
    botsglobal.logger.log(25,_(u'Bots %(process_name)s serving at port: "%(port)s".'),
                                {'process_name':process_name,'port':botsglobal.ini.getint('webserver','port',8080)})
    #handle ssl: cherrypy < 3.2 always uses pyOpenssl. cherrypy >= 3.2 uses python buildin ssl (python >= 2.6 has buildin support for ssl).
    ssl_certificate = botsglobal.ini.get('webserver','ssl_certificate',None)
    ssl_private_key = botsglobal.ini.get('webserver','ssl_private_key',None)
    if ssl_certificate and ssl_private_key:
        if cherrypy.__version__ >= '3.2.0':
            adapter_class = wsgiserver.get_ssl_adapter_class('builtin')
            botswebserver.ssl_adapter = adapter_class(ssl_certificate,ssl_private_key)
        else:
            #but: pyOpenssl should be there!
            botswebserver.ssl_certificate = ssl_certificate
            botswebserver.ssl_private_key = ssl_private_key
        botsglobal.logger.log(25,_(u'Bots %(process_name)s uses ssl (https).'),{'process_name':process_name})
    else:
        botsglobal.logger.log(25,_(u'Bots %(process_name)s uses plain http (no ssl).'),{'process_name':process_name})

    #***start the cherrypy webserver.************************************************
    try:
        botswebserver.start()
    except KeyboardInterrupt:
        botswebserver.stop()


if __name__ == '__main__':
    start()
