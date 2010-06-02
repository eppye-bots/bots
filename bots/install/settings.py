# Django settings for bots project.
import os
import bots

#*******settings for bots error reports**********************************
MANAGERS = (    #bots will send error reports to the MANAGERS
    ('name_manager', 'manager@domain.org'),
    )
#~ EMAIL_HOST = 'smtp.gmail.com'             #Default: 'localhost'
#~ EMAIL_PORT = '587'             #Default: 25
#~ EMAIL_USE_TLS = True       #Default: False
#~ EMAIL_HOST_USER = 'user@gmail.com'        #Default: ''. Username to use for the SMTP server defined in EMAIL_HOST. If empty, Django won't attempt authentication.
#~ EMAIL_HOST_PASSWORD = ''    #Default: ''. PASSWORD to use for the SMTP server defined in EMAIL_HOST. If empty, Django won't attempt authentication.
#~ SERVER_EMAIL = 'user@gmail.com'           #Sender of bots error reports. Default: 'root@localhost'
#~ EMAIL_SUBJECT_PREFIX = ''   #This is prepended on email subject.

#*********path settings*************************advised is not to change these values!!
PROJECT_PATH = os.path.abspath(os.path.dirname(bots.__file__))
# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = PROJECT_PATH + '/'
# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''
# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'
#~ FILE_UPLOAD_TEMP_DIR = os.path.join(PROJECT_PATH, 'botssys/pluginsuploaded') #set in bots.ini
ROOT_URLCONF = 'bots.urls'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_URL = '/logout/'
#~ LOGOUT_REDIRECT_URL = #??not such parameter; is set in urls
TEMPLATE_DIRS = (
    os.path.join(PROJECT_PATH, 'templates'),
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    )

#*********database settings*************************
#django-admin syncdb --pythonpath='/home/hje/botsup' --settings='bots.config.settings'
#SQLITE: 
DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = os.path.join(PROJECT_PATH, 'botssys/sqlitedb/botsdb')       #path to database; if relative path: interpreted relative to bots root directory
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''
DATABASE_OPTIONS = {}
#~ #MySQL:
#~ DATABASE_ENGINE = 'mysql'
#~ DATABASE_NAME = 'botsdb'
#~ DATABASE_USER = 'bots'
#~ DATABASE_PASSWORD = 'botsbots'
#~ DATABASE_HOST = '192.168.0.7'
#~ DATABASE_PORT = '3306'
#~ DATABASE_OPTIONS = {'use_unicode':True,'charset':'utf8',"init_command": 'SET storage_engine=INNODB'}
#PostgeSQL:
#~ DATABASE_ENGINE = 'postgresql_psycopg2'
#~ DATABASE_NAME = 'botsdb'
#~ DATABASE_USER = 'bots'
#~ DATABASE_PASSWORD = 'botsbots'
#~ DATABASE_HOST = '192.168.0.7'
#~ DATABASE_PORT = '5432'
#~ DATABASE_OPTIONS = {}

#*********sessions, cookies, log out time*************************
SESSION_EXPIRE_AT_BROWSER_CLOSE = True      #True: always log in when browser is closed
SESSION_COOKIE_AGE = 3600                   #seconds a user needs to login when no activity
SESSION_SAVE_EVERY_REQUEST = True           #if True: SESSION_COOKIE_AGE is interpreted as: since last activity

#*********localization*************************
# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Amsterdam'
DATE_FORMAT = "Y-m-d"
DATETIME_FORMAT = "Y-m-d G:i"
TIME_FORMAT  = "G:i"
# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'
#~ LANGUAGE_CODE = 'nl'
# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

#*************************************************************************
#*********other django setting. please consult django docs.***************
#set in bots.ini
#~ DEBUG = True
#~ TEMPLATE_DEBUG = DEBUG
SITE_ID = 1
# Make this unique, and don't share it with anybody.
SECRET_KEY = 'm@-u37qiujmeqfbu$daaaaz)sp^7an4u@h=wfx9dd$$$zl2i*x9#awojdcw'

ADMINS = (
    ('bots', 'your_email@domain.com'),
    )



#save uploaded file (=plugin) always to file. no path for temp storage is used, so system default is used.
FILE_UPLOAD_HANDLERS = (
    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
    )
# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
    #'django.template.loaders.eggs.load_template_source',
    )
MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    #~ 'django.middleware.csrf.CsrfViewMiddleware',     #needed for django >= 1.2.*
    )
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    #~ 'django.contrib.sites',
    'django.contrib.admin',
    'bots',
    )
TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.request",
    )
