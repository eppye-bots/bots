try:
    from pysqlite2 import dbapi2 as sqlite  #prefer external modules for pylite
except ImportError:
    import sqlite3 as sqlite    #works OK for python26

import re
reformatparamstyle = re.compile(u'%\((?P<name>[^)]+)\)s')

#~ #bots engine uses:
#~ ''' SELECT *
    #~ FROM ta
    #~ WHERE idta=%(idta)s ''',
    #~ {'idta':12345})
#~ #SQLite wants:
#~ ''' SELECT *
    #~ FROM ta
    #~ WHERE idta=:idta ''',
    #~ {'idta': 12345}


sqlite.register_adapter(bool, lambda s: '1' if s else '0')
sqlite.register_converter('BOOLEAN', lambda s: s == '1')

def connect(database):
    con = sqlite.connect(database, factory=BotsConnection,detect_types=sqlite.PARSE_DECLTYPES, timeout=99.0, isolation_level='EXCLUSIVE')
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

