#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

import datetime
#import bots-modules
import bots.botslib as botslib
import bots.botsglobal as botsglobal
import bots.botsinit as botsinit

'''
no plugin needed.
use for each database connection in configuration file
'''

def start():

    try:
        botsinit.generalinit('config')
        botsinit.initenginelogging()
    except:
        print 'Error reading bots.ini (before database connection).'
        raise

    try:
        botsinit.connect() 
    except:
        print 'Could not connect to database.'
        raise



    #*****************start test***************
    domein = 'test'
    tests = [(u'key1',u'leftcode'),
            (u'key2',u'~!@#$%^&*()_+}{:";][=-/.,<>?`'),
            (u'key3',u'?érýúíó?ás??lzcn?'),
            (u'key4',u'?ë?ÿüïöä´¨???è?ùì'),
            (u'key5',u'òà???UIÕÃ?Ñ`~'),
            (u'key6',u"a\xac\u1234\u20ac\U00008000"),
            (u'key7',u"abc_\u03a0\u03a3\u03a9.txt"),
            (u'key8',u"?ÉRÝÚÍÓ?ÁS??LZCN??"),
            (u'key9',u"Ë?¨YÜ¨IÏÏÖÄ???È?ÙÌÒ`À`Z?"),
            ]
    
    try:    #clean before test
        botslib.change(u'''DELETE FROM ccode ''')
        botslib.change(u'''DELETE FROM ccodetrigger''')
    except:
        print 'Error while deleting',botslib.txtexc()
        raise
        
    try:
        botslib.change(u'''INSERT INTO ccodetrigger (ccodeid)
                                VALUES (%(ccodeid)s)''',
                                {'ccodeid':domein})
        for key,value in tests:
            botslib.change(u'''INSERT INTO ccode (ccodeid_id,leftcode,rightcode,attr1,attr2,attr3,attr4,attr5,attr6,attr7,attr8)
                                    VALUES (%(ccodeid)s,%(leftcode)s,%(rightcode)s,'1','1','1','1','1','1','1','1')''',
                                    {'ccodeid':domein,'leftcode':key,'rightcode':value})
    except:
        print 'Error while updating',botslib.txtexc()
        raise
        
    try:
        for key,value in tests:
            print 'key',key
            for row in botslib.query(u'''SELECT rightcode
                                        FROM    ccode
                                        WHERE   ccodeid_id = %(ccodeid)s
                                        AND     leftcode = %(leftcode)s''',
                                        {'ccodeid':domein,'leftcode':key}):
                print '    ',key, type(row['rightcode']),type(value)
                if row['rightcode'] != value:
                    print 'failure in test "%s": result "%s" is not equal to "%s"'%(key,row['rightcode'],value)
                else:
                    print '    OK'
                break;
            else:
                print '??can not find testentry %s %s in db'%(key,value)
    except:
        print 'Error while quering db',botslib.txtexc()
        raise
 

    #*****************end test***************
    botsglobal.db.close()

if __name__=='__main__':
    start()
    print 'Run without error' 
