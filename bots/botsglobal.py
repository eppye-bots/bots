#Globals used by Bots
db = None               #db-object
ini = None              #ini-file-object that is read (bots.ini)
logger = None           #logger or bots-engine
logmap = None           #logger for mapping in bots-engine
settings = None         #django's settings.py
usersysimportpath = None
routeid = ''            #current route. This is used to set routeid for Processes.
version = '3.0.0rc'       #bots version
minta4query = 0         #used in retry; this determines which ta's are queried in a route
