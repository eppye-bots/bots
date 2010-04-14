import sys
import os
import encodings
import codecs
import ConfigParser
import logging, logging.handlers
#Bots-modules
from botsconfig import *
import botsglobal #as botsglobal
import botslib

class BotsConfig(ConfigParser.SafeConfigParser):
    ''' See SafeConfigParser.
    '''
    def get(self,section, option, default=''):
        try:
            return ConfigParser.SafeConfigParser.get(self,section,option)
        except: #if there is no such section,option
            if default == '':
                raise botslib.BotsError(u'No entry "$entry" in section "$section" in "bots.ini".',entry=option,section=section)
            return default
    def getint(self,section, option, default):
        try:
            return ConfigParser.SafeConfigParser.getint(self,section,option)
        except:
            return default
    def getboolean(self,section, option, default):
        try:
            return ConfigParser.SafeConfigParser.getboolean(self,section,option)
        except:
            return default

def generalinit(configdir):
    #Set Configdir 
    #Configdir MUST be importable. So configdir is relative to PYTHONPATH. Try several options for this import.
    try:                        #configdir outside bots-directory: import configdir.settings.py
        importnameforsettings = os.path.normpath(os.path.join(configdir,'settings')).replace(os.sep,'.')
        settings = botslib.botsbaseimport(importnameforsettings)
    except ImportError:         #configdir is in bots directory: import bots.configdir.settings.py
        try:
            importnameforsettings = os.path.normpath(os.path.join('bots',configdir,'settings')).replace(os.sep,'.')
            settings = botslib.botsbaseimport(importnameforsettings)
        except ImportError:     #set pythonpath to config directory first
            if not os.path.exists(configdir):    #check if configdir exists.
                raise botslib.BotsError(u'In initilisation: path to configuration does not exists: "$path".',path=configdir)
            addtopythonpath = os.path.abspath(os.path.dirname(configdir))
            print 'add pythonpath for usersys',addtopythonpath
            moduletoimport = os.path.basename(configdir)
            sys.path.append(addtopythonpath)
            importnameforsettings = os.path.normpath(os.path.join(moduletoimport,'settings')).replace(os.sep,'.')
            settings = botslib.botsbaseimport(importnameforsettings)
    #settings are accessed using botsglobal
    botsglobal.settings = settings  
    #Find pathname configdir using imported settings.py.
    configdirectory = os.path.abspath(os.path.dirname(settings.__file__))
            
    #Read configuration-file bots.ini.
    botsglobal.ini = BotsConfig()
    cfgfile = open(os.path.join(configdirectory,'bots.ini'), 'r')
    botsglobal.ini.readfp(cfgfile)
    cfgfile.close()
    
    #Set usersys. 
    #usersys MUST be importable. So usersys is relative to PYTHONPATH. Try several options for this import.
    usersys = botsglobal.ini.get('directories','usersys','usersys')
    try:                        #usersys outside bots-directory: import usersys
        importnameforusersys = os.path.normpath(usersys).replace(os.sep,'.')
        importedusersys = botslib.botsbaseimport(importnameforusersys)
    except ImportError:         #usersys is in bots directory: import bots.usersys
        try:
            importnameforusersys = os.path.normpath(os.path.join('bots',usersys)).replace(os.sep,'.')
            importedusersys = botslib.botsbaseimport(importnameforusersys)
        except ImportError:     #set pythonpath to usersys directory first
            if not os.path.exists(usersys):    #check if configdir exists.
                raise botslib.BotsError(u'In initilisation: path to configuration does not exists: "$path".',path=usersys)
            addtopythonpath = os.path.abspath(os.path.dirname(usersys))     #????
            moduletoimport = os.path.basename(usersys)
            print 'add pythonpath for usersys',addtopythonpath
            sys.path.append(addtopythonpath)
            importnameforusersys = os.path.normpath(usersys).replace(os.sep,'.')
            importedusersys = botslib.botsbaseimport(importnameforusersys)
            
    #set directory settings in bots.ini************************************************************
    botsglobal.ini.set('directories','botspath',botsglobal.settings.PROJECT_PATH)
    botsglobal.ini.set('directories','config',configdirectory)
    botsglobal.ini.set('directories','usersysabs',os.path.abspath(os.path.dirname(importedusersys.__file__)))    #???Find pathname usersys using imported usersys
    
    botsglobal.usersysimportpath = importnameforusersys
    botssys = botsglobal.ini.get('directories','botssys','botssys')
    botsglobal.ini.set('directories','botssys',botslib.join(botssys))
    
    botsglobal.ini.set('directories','data',botslib.join(botssys,'data'))
    botslib.dirshouldbethere(botsglobal.ini.get('directories','data'))
    
    botsglobal.ini.set('directories','logging',botslib.join(botssys,'logging'))
    botslib.dirshouldbethere(botsglobal.ini.get('directories','logging'))
    
    #set values in setting.py**********************************************************************
    if botsglobal.ini.get('webserver','environment','development') == 'development':   #values in bots.ini are also used in setting up cherrypy
        settings.DEBUG = True
    else:
        settings.DEBUG = False
    settings.TEMPLATE_DEBUG = settings.DEBUG
    #set paths in settings.py:
    settings.FILE_UPLOAD_TEMP_DIR = os.path.join(settings.PROJECT_PATH, 'botssys/pluginsuploaded')

    #start initializing bots charsets
    initbotscharsets()
    #set environemnt for django to start***************************************************************************************************
    os.environ['DJANGO_SETTINGS_MODULE'] = importnameforsettings
    initbotscharsets()
    botslib.settimeout(botsglobal.ini.getint('settings','globaltimeout',10))    #


def initbotscharsets():
    '''set up right charset handling for specific charsets (UNOA, UNOB, UNOC, etc).'''
    codecs.register(codec_search_function)  #tell python how to search a codec defined by bots. These are the codecs in usersys/charset
    botsglobal.botsreplacechar = unicode(botsglobal.ini.get('settings','botsreplacechar',u' '))
    codecs.register_error('botsreplace', botscharsetreplace)    #define the ' botsreplace' error handling for codecs/charsets.
    for key, value in botsglobal.ini.items('charsets'): #set aliases for charsets in bots.ini
        encodings.aliases.aliases[key]=value

def codec_search_function(encoding):
    try:
        module,filename = botslib.botsimport('charsets',encoding)
    except:
        return None
    else:
        if hasattr(module,'getregentry'):
            return module.getregentry()
        else:
            return None

def botscharsetreplace(info):
    '''replaces an char outside a charset by a user defined char. Useful eg for fixed records: recordlength does not change. Do not know if this works for eg UTF-8...'''
    return (botsglobal.botsreplacechar, info.start+1)
    #~ if isinstance(info, UnicodeEncodeError):
    #~ else:   #if isinstance(info, UnicodeDecodeError) or isinstance(info, UnicodeTranslateError):
        #~ return (u' ', info.start+1)


def initenginelogging():
    convertini2logger={'DEBUG':logging.DEBUG,'INFO':logging.INFO,'WARNING':logging.WARNING,'ERROR':logging.ERROR,'CRITICAL':logging.CRITICAL}
    # create main logger 'bots'
    botsglobal.logger = logging.getLogger('bots')
    botsglobal.logger.setLevel(logging.DEBUG)

    # create rotating file handler
    log_file = botslib.join(botsglobal.ini.get('directories','logging'),'engine.log')
    rotatingfile = logging.handlers.RotatingFileHandler(log_file,backupCount=botsglobal.ini.getint('settings','log_file_number',10))
    rotatingfile.setLevel(convertini2logger[botsglobal.ini.get('settings','log_file_level','ERROR')])
    fileformat = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s : %(message)s",'%Y%m%d %H:%M:%S')
    rotatingfile.setFormatter(fileformat)
    rotatingfile.doRollover()   #each run a new log file is used; old one is rotated
    # add rotating file handler to main logger
    botsglobal.logger.addHandler(rotatingfile)
    
    #logger for trace of mapping; tried to use filters but got this not to work.....
    botsglobal.logmap = logging.getLogger('bots.map')
    if  not botsglobal.ini.getboolean('settings','mappingdebug',False):
        botsglobal.logmap.setLevel(logging.CRITICAL)

    #logger for reading edifile. is now used only very limited (1 place); is done with 'if'
    #~ botsglobal.ini.getboolean('settings','readrecorddebug',False)

    # create console handler
    if botsglobal.ini.getboolean('settings','log_console',True):
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        consuleformat = logging.Formatter("%(levelname)-8s %(message)s")
        console.setFormatter(consuleformat) # add formatter to console
        botsglobal.logger.addHandler(console)  # add console to logger


def connect():
    #different connect code per tyoe of database
    if botsglobal.settings.DATABASE_ENGINE == 'sqlite3':
        #sqlite has some more fiddling; in separate file. Mainly because of some other method of parameter passing.
        if not os.path.isfile(botsglobal.settings.DATABASE_NAME):
            raise Exception('Could not find database file for SLQite')
        import botssqlite
        botsglobal.db = botssqlite.connect(database = botsglobal.settings.DATABASE_NAME)
    elif botsglobal.settings.DATABASE_ENGINE == 'mysql':
        import MySQLdb
        from MySQLdb import cursors
        botsglobal.db = MySQLdb.connect(host=botsglobal.settings.DATABASE_HOST, 
                                        port=int(botsglobal.settings.DATABASE_PORT), 
                                        db=botsglobal.settings.DATABASE_NAME, 
                                        user=botsglobal.settings.DATABASE_USER, 
                                        passwd=botsglobal.settings.DATABASE_PASSWORD,
                                        cursorclass=cursors.DictCursor,
                                        **botsglobal.settings.DATABASE_OPTIONS)
    elif botsglobal.settings.DATABASE_ENGINE == 'postgresql_psycopg2':
        import psycopg2
        import psycopg2.extensions
        import psycopg2.extras
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
        botsglobal.db = psycopg2.connect( 'host=%s dbname=%s user=%s password=%s'%( botsglobal.settings.DATABASE_HOST,
                                                                                    botsglobal.settings.DATABASE_NAME,
                                                                                    botsglobal.settings.DATABASE_USER,
                                                                                    botsglobal.settings.DATABASE_PASSWORD),connection_factory=psycopg2.extras.DictConnection)
        botsglobal.db.set_client_encoding('UNICODE')
        

