#!/usr/bin/env python
''' startup script for bots using apache2 as webserver using wsgi.
wsgi script (outside bots directory:
import sys
import django.core.handlers.wsgi
import mod_wsgi

#set PYTHONPATH...not needed if bots is already on PYTHONPATH
sys.path.append('/home/hje/Bots/botsdev')
from bots import apachewebserver

config = mod_wsgi.process_group
apachewebserver.start(config)
application = django.core.handlers.wsgi.WSGIHandler()


apache config file very simple:
WSGIScriptAlias /    <wsgi script>
Alias /media    <media directory>

Listen 8080
NameVirtualHost *:8080
<VirtualHost *:8080>
WSGIDaemonProcess config user=xxxxx
WSGIProcessGroup config
</VirtualHost>

'''
import botsglobal
import botsinit


def start(configdir):
    botsinit.generalinit(configdir)     #find locating of bots, configfiles, init paths etc.
    process_name = 'apache_webserver_' + configdir
    botsglobal.logger = botsinit.initserverlogging(process_name)    #initialise file-logging for web-server. This logging only contains the logging from bots-webserver.


