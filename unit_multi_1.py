#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
import datetime
import filecmp 
import shutil
import os
import sys
import logging
import subprocess
#import bots-modules
import utilsunit
import bots.botslib as botslib
import bots.botsinit as botsinit
import bots.botsglobal as botsglobal
import bots.transform as transform
from bots.botsconfig import *

'''
plugin 'unit_mulit_1'
enable routes
'''


def test_ccode_with_unicode():
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
        botslib.changeq(u'''DELETE FROM ccode ''')
        botslib.changeq(u'''DELETE FROM ccodetrigger''')
    except:
        print 'Error while deleting: ',botslib.txtexc()
        raise
    try:
        botslib.changeq(u'''INSERT INTO ccodetrigger (ccodeid)
                                VALUES (%(ccodeid)s)''',
                                {'ccodeid':domein})
        for key,value in tests:
            botslib.changeq(u'''INSERT INTO ccode (ccodeid_id,leftcode,rightcode,attr1,attr2,attr3,attr4,attr5,attr6,attr7,attr8)
                                    VALUES (%(ccodeid)s,%(leftcode)s,%(rightcode)s,'1','1','1','1','1','1','1','1')''',
                                    {'ccodeid':domein,'leftcode':key,'rightcode':value})
    except:
        print 'Error while updating: ',botslib.txtexc()
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
        print 'Error while quering db: ',botslib.txtexc()
        raise


def test_unique_in_run_counter():
    if 1 != transform.unique_runcounter('test'):
        raise Exception('test_unique_in_run_counter')
    if 1 != transform.unique_runcounter('test2'):
        raise Exception('test_unique_in_run_counter')
    if 2 != transform.unique_runcounter('test'):
        raise Exception('test_unique_in_run_counter')
    if 3 != transform.unique_runcounter('test'):
        raise Exception('test_unique_in_run_counter')
    if 2 != transform.unique_runcounter('test2'):
        raise Exception('test_unique_in_run_counter')

def test_partner_lookup():
    for s in ['attr1','attr2','attr3','attr4','attr5']:
        if transform.partnerlookup('test',s) != s:
            raise Exception('test_partner_lookup')
    #test lookup for not existing partner
    idpartner = 'partner_not_there'
    if transform.partnerlookup(idpartner,'attr1',safe=True) != idpartner:
        raise Exception('test_partner_lookup')
    try:
        transform.partnerlookup(idpartner,'attr1')
    except botslib.CodeConversionError,e:
        pass
    else:
        raise Exception('expect exception in test_partner_lookup')
    
    #test lookup where no value is in the database
    idpartner = 'test2'
    if transform.partnerlookup(idpartner,'attr1') != 'attr1':
        raise Exception('test_partner_lookup')
    try:
        transform.partnerlookup(idpartner,'attr2')
    except botslib.CodeConversionError,e:
        pass
    else:
        raise Exception('expect exception in test_partner_lookup')


if __name__=='__main__':
    pythoninterpreter = 'python2.7'
    botsinit.generalinit('config')
    utilsunit.dummylogger()
    botsinit.connect()
    botssys = botsglobal.ini.get('directories','botssys')
    shutil.rmtree(os.path.join(botssys,'outfile'),ignore_errors=True)    #remove whole output directory
    
    #mailbag ********
    subprocess.call([pythoninterpreter,'bots-engine.py','mailbagtest'])     #run bots
    utilsunit.comparedicts({'status':0,'lastreceived':13,'lasterror':0,'lastdone':13,'lastok':0,'lastopen':0,'send':39,'processerrors':0,'filesize':8469},utilsunit.getreportlastrun()) #check report
    shutil.rmtree(os.path.join(botssys,'outfile'),ignore_errors=True)    #remove whole output directory
    #*****************

    #passthroughtest ********
    subprocess.call([pythoninterpreter,'bots-engine.py','passthroughtest'])     #run bots
    utilsunit.comparedicts({'status':0,'lastreceived':4,'lasterror':0,'lastdone':4,'lastok':0,'lastopen':0,'send':4,'processerrors':0,'filesize':0},utilsunit.getreportlastrun()) #check report
    shutil.rmtree(os.path.join(botssys,'outfile'),ignore_errors=True)    #remove whole output directory
    #*****************

    #botsidnr ********
    subprocess.call([pythoninterpreter,'bots-engine.py','test_botsidnr','test_changedelete'])     #run bots
    utilsunit.comparedicts({'status':0,'lastreceived':2,'lasterror':0,'lastdone':2,'lastok':0,'lastopen':0,'send':2,'processerrors':0,'filesize':5813},utilsunit.getreportlastrun()) #check report
    infile ='infile/test_botsidnr/compare/unitnodebotsidnr1.edi'
    outfile='outfile/test_botsidnr/unitnodebotsidnr1.edi'
    infile2 ='infile/test_botsidnr/compare/unitnodebotsidnr2.edi'
    outfile2='outfile/test_botsidnr/unitnodebotsidnr2.edi'
    if not filecmp.cmp(os.path.join(botssys,infile),os.path.join(botssys,outfile)):
        raise Exception('error in file compare')
    if not filecmp.cmp(os.path.join(botssys,infile2),os.path.join(botssys,outfile2)):
        raise Exception('error in file2 compare')
    #*****************
    #*****************
    test_ccode_with_unicode()
    #*****************
    #*****************
    test_unique_in_run_counter()
    #*****************
    #*****************
    test_partner_lookup()
    #*****************
    #*****************
    #~ test_unique()
    #*****************
    #*****************
    logging.shutdown()
    botsglobal.db.close
    print 'Tests OK!!!' 
