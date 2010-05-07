try:
    from pysqlite2 import dbapi2 as sqlite  #prefer external modules for pylite
except ImportError:
    import sqlite3 as sqlite    #works OK for python26

#~ #bots engine uses: 
#~ ''' SELECT *
    #~ FROM  ta
    #~ WHERE idta=%(idta)s ''',
    #~ {'idta':12345})
#~ #SQLite wants:
#~ ''' SELECT *
    #~ FROM  ta
    #~ WHERE idta=:idta ''',
    #~ {'idta': 12345}
    
import re
reformatparamstyle = re.compile(u'%\((?P<name>[^)]+)\)s')

def adapter4bool(boolfrompython):
    #SQLite expects a string
    if boolfrompython:
        return '1'
    else:
        return '0'

def converter4bool(strfromdb):
    #SQLite returns a string
    if strfromdb == '1':
        return True
    else:
        return False

sqlite.register_adapter(bool,adapter4bool)
sqlite.register_converter('BOOLEAN',converter4bool)

def connect(database):
    con = sqlite.connect(database, factory=BotsConnection,detect_types=sqlite.PARSE_DECLTYPES, timeout=99.0, isolation_level='IMMEDIATE')
    con.row_factory = sqlite.Row
    con.execute('''PRAGMA synchronous=OFF''')
    return con

class BotsConnection(sqlite.Connection):
    def cursor(self):
        return sqlite.Connection.cursor(self, factory=BotsCursor)

class BotsCursor(sqlite.Cursor):
    def execute(self,string,parameters=None):
        if parameters is None:
            sqlite.Cursor.execute(self,string)
        else:
            sqlite.Cursor.execute(self,reformatparamstyle.sub(u''':\g<name>''',string),parameters)
    #~ def execute(self,string,*args):
        #~ sqlite.Cursor.execute(self,reformatparamstyle.sub(u''':\g<name>''',string),*args)

