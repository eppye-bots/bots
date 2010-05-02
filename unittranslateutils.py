import unittest
import bots.botsglobal as botsglobal
import bots.inmessage as inmessage
import bots.botslib as botslib
import bots.transform as transform
import pickle
import bots.botsinit as botsinit
import utilsunit

'''plugin unittranslateutils.zip '''
#as the max length is 

class TestTranslate(unittest.TestCase):
    def setUp(self):
        pass

    def testpersist(self):
        #~ inn = inmessage.edifromfile(editype='edifact',messagetype='orderswithenvelope',filename='botssys/infile/tests/inisout02.edi')
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
        value= u'xxxxxxxxxxxxxxxxx'
        value2= u'IEFJUKAHE*FMhr\u0302\u0267t4hr f.wch shjeriw'
        value3= u'1'*1024
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
        transform.persist_update(domein,botskey,value)   #is not there. gives no error...

    #~ def testcodeconversion(self):
        #~ self.assertEqual('TESTOUT',transform.codeconversion('aperakrff2qualifer','TESTIN'),'basis')
        #~ self.assertRaises(botslib.CodeConversionError,transform.codeconversion,'aperakrff2qualifer','TESTINNOT') 
        #~ self.assertEqual('TESTIN',transform.rcodeconversion('aperakrff2qualifer','TESTOUT'),'basis')
        #~ self.assertRaises(botslib.CodeConversionError,transform.rcodeconversion,'aperakrff2qualifer','TESTINNOT') 
        
        #~ #need article in ccodelist: 
        #~ self.assertEqual('TESTOUT',transform.codetconversion('artikel','TESTIN'),'basis')
        #~ self.assertRaises(botslib.CodeConversionError,transform.codetconversion,'artikel','TESTINNOT') 
        #~ self.assertEqual('TESTIN',transform.rcodetconversion('artikel','TESTOUT'),'basis')
        #~ self.assertRaises(botslib.CodeConversionError,transform.rcodetconversion,'artikel','TESTINNOT') 
        #~ self.assertEqual('TESTATTR1',transform.codetconversion('artikel','TESTIN','attr1'),'basis')

    def testunique(self):
        newdomain = 'test' + transform.unique('test')
        self.assertEqual('1',transform.unique(newdomain),'init new domain')
        self.assertEqual('2',transform.unique(newdomain),'next one')
        
    def testunique(self):
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

if __name__ == '__main__':
    botsinit.generalinit('/home/hje/botsup/bots/config')
    #~ botslib.initbotscharsets()
    botsinit.initenginelogging()
    botsinit.connect() 
    try:
        unittest.main()
    except:
        pass
    botsglobal.db.close()
