#Globals used by Bots
version = '3.1.0'       #bots version
db = None               #db-object
ini = None              #ini-file-object that is read (bots.ini)
logger = None           #logger or bots-engine
logmap = None           #logger for mapping in bots-engine
settings = None         #django's settings.py
usersysimportpath = None
routeid = ''            #current route. This is used to set routeid for Processes.
minta4query = 0         #this determines which ta's are queried for a run
minta4query_crash = 0   #this determines which ta's are queried after crash
minta4query_route = 0   #this determines which ta's are queried for route
minta4query_routepart = 0   #this determines which ta's are queried for route-part
confirmrules = []       #confirmrules are read into memory at start of run
