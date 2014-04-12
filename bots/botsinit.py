import sys
import os
import encodings
import codecs
import ConfigParser
import logging, logging.handlers
#Bots-modules
import botsglobal
import botslib


class BotsConfig(ConfigParser.RawConfigParser):
    ''' As ConfigParser, but with defaults.
    '''
    def get(self,section, option, default=''):
        if self.has_option(section, option):
            return ConfigParser.RawConfigParser.get(self,section, option)
        elif default == '':
            raise botslib.BotsError(u'No entry "%(option)s" in section "%(section)s" in "bots.ini".',{'option':option,'section':section})
        else:
            return default
    def getint(self,section, option, default):
        if self.has_option(section, option):
            return ConfigParser.RawConfigParser.getint(self,section, option)
        else:
            return default
    def getboolean(self,section, option, default):
        if self.has_option(section, option):
            return ConfigParser.RawConfigParser.getboolean(self,section, option)
        else:
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
                raise botslib.PanicError(u'In initilisation: path to configuration does not exists: "%(configdir)s".',{'configdir':configdir})
            addtopythonpath = os.path.abspath(os.path.dirname(configdir))
            #~ print 'add pythonpath for usersys',addtopythonpath
            moduletoimport = os.path.basename(configdir)
            sys.path.append(addtopythonpath)
            importnameforsettings = os.path.normpath(os.path.join(moduletoimport,'settings')).replace(os.sep,'.')
            settings = botslib.botsbaseimport(importnameforsettings)
    #settings are accessed using botsglobal
    botsglobal.settings = settings
    if hasattr(settings,'DATABASE_ENGINE'):      #check for old django settings.py
        print u'You use an old settings.py. Please change settings.py first. See migration instructions in wiki: http://code.google.com/p/bots/wiki/Migrate'
        sys.exit(0)
    #Find pathname configdir using imported settings.py.
    configdirectory = os.path.abspath(os.path.dirname(settings.__file__))

    #Read configuration-file bots.ini.
    botsglobal.ini = BotsConfig()
    botsglobal.ini.read(os.path.join(configdirectory,'bots.ini'))

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
                raise botslib.PanicError(u'In initilisation: path to configuration does not exists: "%(usersys)s".',{'usersys':usersys})
            addtopythonpath = os.path.abspath(os.path.dirname(usersys))     #????
            moduletoimport = os.path.basename(usersys)
            #~ print 'add pythonpath for usersys',addtopythonpath
            sys.path.append(addtopythonpath)
            importnameforusersys = os.path.normpath(usersys).replace(os.sep,'.')
            importedusersys = botslib.botsbaseimport(importnameforusersys)

    #set directory settings in bots.ini************************************************************
    # 'directories','botspath': absolute path for bots directory
    botsglobal.ini.set('directories','botspath',settings.PROJECT_PATH)
    # 'directories','config': absolute path for config directory
    botsglobal.ini.set('directories','config',configdirectory)
    botsglobal.ini.set('directories','config_org',configdir)            #set config as originally received.
    # 'directories','usersysabs': absolute path for config usersysabs
    botsglobal.ini.set('directories','usersysabs',os.path.abspath(os.path.dirname(importedusersys.__file__)))    #???Find pathname usersys using imported usersys
    # botsglobal.usersysimportpath: used for imports from usersys
    botsglobal.usersysimportpath = importnameforusersys
    # 'directories','botssys': absolute path for config botssys
    botssys = botsglobal.ini.get('directories','botssys','botssys')
    botsglobal.ini.set('directories','botssys_org',botssys)             #store original botssys setting
    botsglobal.ini.set('directories','botssys',botslib.join(botssys))

    botsglobal.ini.set('directories','data',botslib.join(botssys,'data'))
    botslib.dirshouldbethere(botsglobal.ini.get('directories','data'))

    botsglobal.ini.set('directories','logging',botslib.join(botssys,'logging'))
    botslib.dirshouldbethere(botsglobal.ini.get('directories','logging'))
    botsglobal.ini.set('directories','templates',botslib.join(botsglobal.ini.get('directories','usersysabs'),'grammars/template/templates'))
    botsglobal.ini.set('directories','templateshtml',botslib.join(botsglobal.ini.get('directories','usersysabs'),'grammars/templatehtml/templates'))

    if botsglobal.ini.get('webserver','environment','development') != 'development':   #values in bots.ini are also used in setting up cherrypy
        logging.raiseExceptions = 0     # during production: if errors occurs in writing to log: ignore error. (leads to a missing log line, better than error;-).

    #initialise bots charsets
    initbotscharsets()
    #set environment for django to start***************************************************************************************************
    os.environ['DJANGO_SETTINGS_MODULE'] = importnameforsettings
    botslib.settimeout(botsglobal.ini.getint('settings','globaltimeout',10))
    import django
    if django.VERSION[1]>= 7:
        django.setup()

#**********************************************************************************
#*** bots specific handling of character-sets (eg UNOA charset) *******************
def initbotscharsets():
    '''set up right charset handling for specific charsets (UNOA, UNOB, UNOC, etc).'''
    #tell python how to search a codec defined by bots. Bots searches for this in usersys/charset
    codecs.register(codec_search_function)
    #syntax has parameters checkcharsetin or checkcharsetout. These can have value 'botsreplace'
    #eg: 'checkcharsetin':'botsreplace',  #strict, ignore or botsreplace
    #in case of errors: the 'wrong' character is replaced with char as set in bots.ini. Default value in bots.ini is ' ' (space)
    botsglobal.botsreplacechar = unicode(botsglobal.ini.get('settings','botsreplacechar',u' '))
    codecs.register_error('botsreplace', botsreplacechar_handler)    #need to register the handler for botsreplacechar
    #set aliases for the charsets in bots.ini
    for key, value in botsglobal.ini.items('charsets'):
        encodings.aliases.aliases[key] = value

def codec_search_function(encoding):
    try:
        module,filename = botslib.botsimport('charsets',encoding)
    except ImportError:         #charsetscript not there; other errors like syntax errors are not catched
        return None
    else:
        if hasattr(module,'getregentry'):
            return module.getregentry()
        else:
            return None

def botsreplacechar_handler(info):
    '''replaces an char outside a charset by a user defined char. Useful eg for fixed records: recordlength does not change.'''
    return (botsglobal.botsreplacechar, info.start+1)
#*** end of bots specific handling of character-sets ******************************
#**********************************************************************************

def connect():
    ''' connect to database for non-django modules eg engine '''
    if botsglobal.settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
        #sqlite has some more fiddling; in separate file. Mainly because of some other method of parameter passing.
        if not os.path.isfile(botsglobal.settings.DATABASES['default']['NAME']):
            raise botslib.PanicError(u'Could not find database file for SQLite')
        import botssqlite
        botsglobal.db = botssqlite.connect(database = botsglobal.settings.DATABASES['default']['NAME'])
    elif botsglobal.settings.DATABASES['default']['ENGINE'] == 'django.db.backends.mysql':
        import MySQLdb
        from MySQLdb import cursors
        botsglobal.db = MySQLdb.connect(host=botsglobal.settings.DATABASES['default']['HOST'],
                                        port=int(botsglobal.settings.DATABASES['default']['PORT']),
                                        db=botsglobal.settings.DATABASES['default']['NAME'],
                                        user=botsglobal.settings.DATABASES['default']['USER'],
                                        passwd=botsglobal.settings.DATABASES['default']['PASSWORD'],
                                        cursorclass=cursors.DictCursor,
                                        **botsglobal.settings.DATABASES['default']['OPTIONS'])
    elif botsglobal.settings.DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql_psycopg2':
        import psycopg2
        import psycopg2.extensions
        import psycopg2.extras
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
        botsglobal.db = psycopg2.connect(host=botsglobal.settings.DATABASES['default']['HOST'],
                                        port=botsglobal.settings.DATABASES['default']['PORT'],
                                        database=botsglobal.settings.DATABASES['default']['NAME'],
                                        user=botsglobal.settings.DATABASES['default']['USER'],
                                        password=botsglobal.settings.DATABASES['default']['PASSWORD'],
                                        connection_factory=psycopg2.extras.DictConnection)
        botsglobal.db.set_client_encoding('UNICODE')
    else:
        raise botslib.PanicError(u'Unknown database engine "%(engine)s".',{'engine':botsglobal.settings.DATABASES['default']['ENGINE']})

#*******************************************************************
#*** init logging **************************************************
#*******************************************************************
logging.addLevelName(25, 'STARTINFO')
convertini2logger = {'DEBUG':logging.DEBUG,'INFO':logging.INFO,'WARNING':logging.WARNING,'ERROR':logging.ERROR,'CRITICAL':logging.CRITICAL,'STARTINFO':25}

def initenginelogging(logname):
    #initialise file logging: create main logger 'bots'
    logger = logging.getLogger(logname)
    logger.setLevel(convertini2logger[botsglobal.ini.get('settings','log_file_level','INFO')])
    handler = logging.handlers.RotatingFileHandler(botslib.join(botsglobal.ini.get('directories','logging'),logname+'.log'),backupCount=botsglobal.ini.getint('settings','log_file_number',10))
    fileformat = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s : %(message)s",'%Y%m%d %H:%M:%S')
    handler.setFormatter(fileformat)
    handler.doRollover()   #each run a new log file is used; old one is rotated
    logger.addHandler(handler)
    #initialise file logging: logger for trace of mapping; tried to use filters but got this not to work.....
    botsglobal.logmap = logging.getLogger('engine.map')
    if not botsglobal.ini.getboolean('settings','mappingdebug',False):
        botsglobal.logmap.setLevel(logging.CRITICAL)
    #logger for reading edifile. is now used only very limited (1 place); is done with 'if'
    #~ botsglobal.ini.getboolean('settings','readrecorddebug',False)
    # initialise console/screen logging
    if botsglobal.ini.getboolean('settings','log_console',True):
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        consuleformat = logging.Formatter("%(levelname)-8s %(message)s")
        console.setFormatter(consuleformat) # add formatter to console
        logger.addHandler(console)  # add console to logger
    return logger

def initserverlogging(logname):
    # initialise file logging
    logger = logging.getLogger(logname)
    logger.setLevel(convertini2logger[botsglobal.ini.get(logname,'log_file_level','INFO')])
    handler = logging.handlers.TimedRotatingFileHandler(os.path.join(botsglobal.ini.get('directories','logging'),logname+'.log'),when='midnight',backupCount=10)
    fileformat = logging.Formatter("%(asctime)s %(levelname)-9s: %(message)s",'%Y%m%d %H:%M:%S')
    handler.setFormatter(fileformat)
    logger.addHandler(handler)
    # initialise console/screen logging
    if botsglobal.ini.getboolean(logname,'log_console',True):
        console = logging.StreamHandler()
        console.setLevel(convertini2logger[botsglobal.ini.get(logname,'log_console_level','STARTINFO')])
        consoleformat = logging.Formatter("%(asctime)s %(levelname)-9s: %(message)s",'%Y%m%d %H:%M:%S')
        console.setFormatter(consoleformat) # add formatter to console
        logger.addHandler(console)  # add console to logger
    return logger

