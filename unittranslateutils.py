import pickle
import unittest
import utilsunit
import bots.botsglobal as botsglobal
import bots.botslib as botslib
import bots.botsinit as botsinit
import bots.inmessage as inmessage
import bots.transform as transform

'''plugin unittranslateutils.zip '''
#as the max length is 

class TestTranslate(unittest.TestCase):
    def setUp(self):
        pass

    def testpersist(self):
        #~ inn = inmessage.parse_edi_file(editype='edifact',messagetype='orderswithenvelope',filename='botssys/infile/tests/inisout02.edi')
        domein=u'test'
        botskey=u'test'
        value= u'xxxxxxxxxxxxxxxxx'
        value2= u'IEFJUKAHE*FMhrt4hr f.wch shjeriw'
        value3= u'1'*3024
        transform.persist_delete(domein,botskey)
        #~ self.assertRaises(botslib.PersistError,transform.persist_add,domein,botskey,value3)   #content is too long
        transform.persist_add(domein,botskey,value)
        self.assertRaises(botslib.PersistError,transform.persist_add,domein,botskey,value)   #is already present
        self.assertEqual(value,transform.persist_lookup(domein,botskey),'basis')
        transform.persist_update(domein,botskey,value2)
        self.assertEqual(value2,transform.persist_lookup(domein,botskey),'basis')
        #~ self.assertRaises(botslib.PersistError,transform.persist_update,domein,botskey,value3)   #content is too long
        transform.persist_delete(domein,botskey)
        self.assertEqual(None,transform.persist_lookup(domein,botskey),'basis')
        transform.persist_update(domein,botskey,value)   #test-tet is not there. gives no error...

    def testpersistunicode(self):
        domein=u'test'
        botskey=u'1235:\ufb52\ufb66\ufedb'
        botskey3=u'135:\ufb52\ufb66\ufedb'
        value= u'xxxxxxxxxxxxxxxxx'
        value2= u'IEFJUKAHE*FMhr\u0302\u0267t4hr f.wch shjeriw'
        value3= u'1/2/d'*3024
        transform.persist_delete(domein,botskey)
        transform.persist_delete(domein,botskey3)
        transform.persist_add(domein,botskey3,value3)
        self.assertEqual(value3,transform.persist_lookup(domein,botskey3),'basis')
        transform.persist_add(domein,botskey,value)
        self.assertRaises(botslib.PersistError,transform.persist_add,domein,botskey,value)   #is already present
        self.assertEqual(value,transform.persist_lookup(domein,botskey),'basis')
        transform.persist_update(domein,botskey,value2)
        self.assertEqual(value2,transform.persist_lookup(domein,botskey),'basis')
        #~ self.assertRaises(botslib.PersistError,transform.persist_update,domein,botskey,value3)   #content is too long
        transform.persist_delete(domein,botskey)
        self.assertEqual(None,transform.persist_lookup(domein,botskey),'basis')
        transform.persist_update(domein,botskey,value)   #is not there. gives no error...

    def testcodeconversion(self):
        #codeconversion via tabel ccode OLD functionnames: 
        self.assertEqual('TESTOUT',transform.codetconversion('artikel','TESTIN'),'basis')
        self.assertEqual('TESTOUT',transform.safecodetconversion('artikel','TESTIN'),'basis')
        self.assertEqual('TESTINNOT',transform.safecodetconversion('artikel','TESTINNOT'),'basis')
        self.assertRaises(botslib.CodeConversionError,transform.codetconversion,'artikel','TESTINNOT') 
        self.assertEqual('TESTIN',transform.rcodetconversion('artikel','TESTOUT'),'basis')
        self.assertEqual('TESTIN',transform.safercodetconversion('artikel','TESTOUT'),'basis')
        self.assertEqual('TESTINNOT',transform.safercodetconversion('artikel','TESTINNOT'),'basis')
        self.assertRaises(botslib.CodeConversionError,transform.rcodetconversion,'artikel','TESTINNOT') 
        #attributes
        self.assertEqual('TESTATTR1',transform.codetconversion('artikel','TESTIN','attr1'),'basis')
        self.assertEqual('TESTATTR1',transform.safecodetconversion('artikel','TESTIN','attr1'),'basis')

        #codeconversion via tabel ccode: 
        self.assertEqual('TESTOUT',transform.ccode('artikel','TESTIN'),'basis')
        self.assertEqual('TESTOUT',transform.safe_ccode('artikel','TESTIN'),'basis')
        self.assertEqual('TESTINNOT',transform.safe_ccode('artikel','TESTINNOT'),'basis')
        self.assertRaises(botslib.CodeConversionError,transform.ccode,'artikel','TESTINNOT') 
        self.assertEqual('TESTIN',transform.reverse_ccode('artikel','TESTOUT'),'basis')
        self.assertEqual('TESTIN',transform.safe_reverse_ccode('artikel','TESTOUT'),'basis')
        self.assertEqual('TESTINNOT',transform.safe_reverse_ccode('artikel','TESTINNOT'),'basis')
        self.assertRaises(botslib.CodeConversionError,transform.reverse_ccode,'artikel','TESTINNOT') 
        #attributes
        self.assertEqual('TESTATTR1',transform.ccode('artikel','TESTIN','attr1'),'basis')
        self.assertEqual('TESTATTR1',transform.safe_ccode('artikel','TESTIN','attr1'),'basis')

    def testgetcodeset(self):
        self.assertEqual([u'TESTOUT'],transform.getcodeset('artikel','TESTIN'),'test getcodeset')
        self.assertEqual([u'1', u'2', u'4', u'5'],transform.getcodeset('list','list'),'test getcodeset')
        
    def testdatemask(self):
        self.assertEqual(u'20121231',transform.datemask('12/31/2012','MM/DD/YYYY','YYYYMMDD'),'test datemask')
        self.assertEqual(u'201231',transform.datemask('12/31/2012','MM/DD/YYYY','YYMMDD'),'test datemask')
        
    def testuseoneof(self):
        self.assertEqual(u'test',transform.useoneof(None,'test'),'test useoneof')
        self.assertEqual(u'test',transform.useoneof('test','test1','test2'),'test useoneof')
        self.assertEqual(None,transform.useoneof(),'test useoneof')
        self.assertEqual(None,transform.useoneof(()),'test useoneof')
        self.assertEqual(None,transform.useoneof(''),'test useoneof')
        self.assertEqual(None,transform.useoneof(None,None,None,None),'test useoneof')
        
    def testdateformat(self):
        self.assertEqual(None,transform.dateformat(''),'test dateformat')
        self.assertEqual(None,transform.dateformat(None),'test dateformat')
        self.assertEqual(u'102',transform.dateformat('12345678'),'test dateformat')
        self.assertEqual(None,transform.dateformat('123456789'),'test dateformat')
        self.assertEqual(None,transform.dateformat('1234567'),'test dateformat')
        self.assertEqual(u'203',transform.dateformat('123456789012'),'test dateformat')
        self.assertEqual(u'718',transform.dateformat('1234567890123456'),'test dateformat')
        
    def testtruncate(self):
        self.assertEqual(None,transform.truncate(5,None),'test truncate')
        self.assertEqual(u'artik',transform.truncate(5,'artikel'),'test truncate')
        self.assertEqual(u'artikel',transform.truncate(10,'artikel'),'test truncate')
        self.assertEqual(u'a',transform.truncate(1,'artikel'),'test truncate')
        self.assertEqual(u'',transform.truncate(0,'artikel'),'test truncate')
        
    def testconcat(self):
        self.assertEqual(None,transform.concat(None,None),'test concatenate')
        self.assertEqual(u'artikel',transform.concat('artikel',None),'test concatenate')
        self.assertEqual(u'artikel',transform.concat(None,'artikel'),'test concatenate')
        self.assertEqual(u'artikel',transform.concat('','artikel'),'test concatenate')
        self.assertEqual(u'artikel1 artikel2',transform.concat('artikel1','artikel2'),'test concatenate')
        
    def testunique(self):
        newdomain = 'test' + transform.unique('test')
        self.assertEqual('1',transform.unique(newdomain),'init new domain')
        self.assertEqual('2',transform.unique(newdomain),'next one')
        
        newdomain = 'test' + transform.unique('test')
        self.assertEqual(True,transform.checkunique(newdomain,1),'init new domain')
        self.assertEqual(False,transform.checkunique(newdomain,1),'seq should be 2')
        self.assertEqual(False,transform.checkunique(newdomain,3),'seq should be 2')
        self.assertEqual(True,transform.checkunique(newdomain,2),'next one')
        
    def testean(self):
        self.assertEqual('123456789012',transform.addeancheckdigit('12345678901'),'UPC')
        self.assertEqual('2',transform.calceancheckdigit('12345678901'),'UPC')
        self.assertEqual(True,transform.checkean('123456789012'),'UPC')
        self.assertEqual(False,transform.checkean('123456789011'),'UPC')
        self.assertEqual(False,transform.checkean('123456789013'),'UPC')

        self.assertEqual('123456789012',transform.addeancheckdigit('12345678901'),'UPC')
        self.assertEqual('2',transform.calceancheckdigit('12345678901'),'UPC')
        self.assertEqual(True,transform.checkean('123456789012'),'UPC')
        self.assertEqual(False,transform.checkean('123456789011'),'UPC')
        self.assertEqual(False,transform.checkean('123456789013'),'UPC')

        self.assertEqual('12345670',transform.addeancheckdigit('1234567'),'EAN8')
        self.assertEqual('0',transform.calceancheckdigit('1234567'),'EAN8')
        self.assertEqual(True,transform.checkean('12345670'),'EAN8')
        self.assertEqual(False,transform.checkean('12345679'),'EAN8')
        self.assertEqual(False,transform.checkean('12345671'),'EAN8')

        self.assertEqual('1234567890128',transform.addeancheckdigit('123456789012'),'EAN13')
        self.assertEqual('8',transform.calceancheckdigit('123456789012'),'EAN13')
        self.assertEqual(True,transform.checkean('1234567890128'),'EAN13')
        self.assertEqual(False,transform.checkean('1234567890125'),'EAN13')
        self.assertEqual(False,transform.checkean('1234567890120'),'EAN13')

        self.assertEqual('12345678901231',transform.addeancheckdigit('1234567890123'),'EAN14')
        self.assertEqual('1',transform.calceancheckdigit('1234567890123'),'EAN14')
        self.assertEqual(True,transform.checkean('12345678901231'),'EAN14')
        self.assertEqual(False,transform.checkean('12345678901230'),'EAN14')
        self.assertEqual(False,transform.checkean('12345678901236'),'EAN14')

        self.assertEqual('123456789012345675',transform.addeancheckdigit('12345678901234567'),'UPC')
        self.assertEqual('5',transform.calceancheckdigit('12345678901234567'),'UPC')
        self.assertEqual(True,transform.checkean('123456789012345675'),'UPC')
        self.assertEqual(False,transform.checkean('123456789012345670'),'UPC')
        self.assertEqual(False,transform.checkean('123456789012345677'),'UPC')

def testunique_runcounter():
    if 1 != transform.unique_runcounter('test'):
        raise Exception('test')
    if 1 != transform.unique_runcounter('test2'):
        raise Exception('test')
    if 2 != transform.unique_runcounter('test'):
        raise Exception('test')
    if 3 != transform.unique_runcounter('test'):
        raise Exception('test')
    if 2 != transform.unique_runcounter('test2'):
        raise Exception('test')

if __name__ == '__main__':
    botsinit.generalinit('config')
    botsglobal.logger = botsinit.initenginelogging('engine')
    botsinit.connect() 
    unittest.main()
    testunique_runcounter()
    botsglobal.db.close()
