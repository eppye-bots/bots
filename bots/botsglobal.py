#Globals used by Bots
incommunicate = False    #used to set all incommunication off
db = None               #db-object
ini = None              #ini-file-object that is read (bots.ini)
logger = None           #logger or bots-engine
logmap = None           #logger for mapping in bots-engine
settings = None         #djangoś settings.py
usersysimportpath = None
routeid = ''            #current route. This is used to set routeid for Processes.
preprocessnumber = 0    #different preprocessnumbers  are  needed for different preprocessing.
version = '2.2.0rc'       #bots version
minta4query = 0           #used in retry; this determines which ta's are queried in a route
######################################
