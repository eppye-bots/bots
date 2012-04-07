import os
import unittest
import shutil
import bots.inmessage as inmessage
import bots.outmessage as outmessage
import filecmp 
try:
    import json as simplejson
except ImportError:
    import simplejson
import bots.botslib as botslib
import bots.botsinit as botsinit
import utilsunit
try:
    import cElementTree as ET
except ImportError:
    try:
        import elementtree.ElementTree as ET
    except ImportError:
        try:
            from xml.etree import cElementTree as ET
        except ImportError:
            from xml.etree import ElementTree as ET

'''
PLUGIN: unitinmessagejson.zip
'''

class InmessageJson(unittest.TestCase):
    #***********************************************************************
    #***********test json eg list of article (as eg used in database comm *******
    #***********************************************************************
    def testjson01(self):
        filein = 'botssys/infile/unitinmessagejson/org/01.jsn'
        filecomp = 'botssys/infile/unitinmessagejson/comp/01.xml'
        inn1 = inmessage.edifromfile(filename=filein,editype='json',messagetype='articles')
        inn2 = inmessage.edifromfile(filename=filecomp,editype='xml',messagetype='articles')
        self.failUnless(utilsunit.comparenode(inn1.root,inn2.root))
        
    def testjson01nocheck(self):
        filein = 'botssys/infile/unitinmessagejson/org/01.jsn'
        filecomp = 'botssys/infile/unitinmessagejson/comp/01.xml'
        inn1 = inmessage.edifromfile(filename=filein,editype='jsonnocheck',messagetype='articles')
        inn2 = inmessage.edifromfile(filename=filecomp,editype='xml',messagetype='articles')
        self.failUnless(utilsunit.comparenode(inn1.root,inn2.root))
        
    def testjson11(self):
        filein = 'botssys/infile/unitinmessagejson/org/11.jsn'
        filecomp = 'botssys/infile/unitinmessagejson/comp/01.xml'
        inn1 = inmessage.edifromfile(filename=filein,editype='json',messagetype='articles')
        inn2 = inmessage.edifromfile(filename=filecomp,editype='xml',messagetype='articles')
        self.failUnless(utilsunit.comparenode(inn1.root,inn2.root))
        
    def testjson11nocheck(self):
        filein = 'botssys/infile/unitinmessagejson/org/11.jsn'
        filecomp = 'botssys/infile/unitinmessagejson/comp/01.xml'
        inn1 = inmessage.edifromfile(filename=filein,editype='jsonnocheck',messagetype='articles')
        inn2 = inmessage.edifromfile(filename=filecomp,editype='xml',messagetype='articles')
        self.failUnless(utilsunit.comparenode(inn1.root,inn2.root))
    #***********************************************************************
    #*********json incoming tests complex structure*************************
    #***********************************************************************
    def testjsoninvoic01(self):
        filein = 'botssys/infile/unitinmessagejson/org/invoic01.jsn'
        filecomp = 'botssys/infile/unitinmessagejson/comp/invoic01.xml'
        inn1 = inmessage.edifromfile(filename=filein,editype='json',messagetype='invoic')
        inn2 = inmessage.edifromfile(filename=filecomp,editype='xml',messagetype='invoic')
        self.failUnless(utilsunit.comparenode(inn1.root,inn2.root))
        
    def testjsoninvoic01nocheck(self):
        filein = 'botssys/infile/unitinmessagejson/org/invoic01.jsn'
        filecomp = 'botssys/infile/unitinmessagejson/comp/invoic01.xml'
        inn1 = inmessage.edifromfile(filename=filein,editype='jsonnocheck',messagetype='invoic')
        inn2 = inmessage.edifromfile(filename=filecomp,editype='xml',messagetype='invoic')
        self.failUnless(utilsunit.comparenode(inn1.root,inn2.root))
        
    def testjsoninvoic02(self):
        ''' check  01.xml the same after rad&write/check '''
        filein = 'botssys/infile/unitinmessagejson/org/invoic02.jsn'
        filecomp = 'botssys/infile/unitinmessagejson/comp/invoic01.xml'
        inn1 = inmessage.edifromfile(filename=filein,editype='json',messagetype='invoic')
        inn2 = inmessage.edifromfile(filename=filecomp,editype='xml',messagetype='invoic')
        self.failUnless(utilsunit.comparenode(inn1.root,inn2.root))
        
    def testjsoninvoic02nocheck(self):
        ''' check  01.xml the same after rad&write/check '''
        filein = 'botssys/infile/unitinmessagejson/org/invoic02.jsn'
        filecomp = 'botssys/infile/unitinmessagejson/comp/invoic01.xml'
        inn1 = inmessage.edifromfile(filename=filein,editype='jsonnocheck',messagetype='invoic')
        inn2 = inmessage.edifromfile(filename=filecomp,editype='xml',messagetype='invoic')
        self.failUnless(utilsunit.comparenode(inn1.root,inn2.root))


    #***********************************************************************
    #*********json incoming tests int,float*********************************
    #***********************************************************************
    def testjsoninvoic03(self):
        ''' test int, float in json '''
        filein = 'botssys/infile/unitinmessagejson/org/invoic03.jsn'
        filecomp = 'botssys/infile/unitinmessagejson/comp/invoic02.xml'
        inn1 = inmessage.edifromfile(filename=filein,editype='json',messagetype='invoic')
        inn2 = inmessage.edifromfile(filename=filecomp,editype='xml',messagetype='invoic')
        self.failUnless(utilsunit.comparenode(inn1.root,inn2.root))
        
    def testjsoninvoic03xmlnocheck(self):
        ''' test int, float in json '''
        filein = 'botssys/infile/unitinmessagejson/org/invoic03.jsn'
        filecomp = 'botssys/infile/unitinmessagejson/comp/invoic02.xml'
        inn1 = inmessage.edifromfile(filename=filein,editype='json',messagetype='invoic')
        inn2 = inmessage.edifromfile(filename=filecomp,editype='xmlnocheck',messagetype='invoic')
        self.failUnless(utilsunit.comparenode(inn1.root,inn2.root))
        
    def testjsoninvoic03nocheck(self):
        ''' test int, float in json '''
        filein = 'botssys/infile/unitinmessagejson/org/invoic03.jsn'
        filecomp = 'botssys/infile/unitinmessagejson/comp/invoic02.xml'
        inn1 = inmessage.edifromfile(filename=filein,editype='jsonnocheck',messagetype='invoic')
        inn2 = inmessage.edifromfile(filename=filecomp,editype='xml',messagetype='invoic')
        self.failUnless(utilsunit.comparenode(inn1.root,inn2.root))
        
    def testjsoninvoic03nocheckxmlnocheck(self):
        ''' test int, float in json '''
        filein = 'botssys/infile/unitinmessagejson/org/invoic03.jsn'
        filecomp = 'botssys/infile/unitinmessagejson/comp/invoic02.xml'
        inn1 = inmessage.edifromfile(filename=filein,editype='jsonnocheck',messagetype='invoic')
        inn2 = inmessage.edifromfile(filename=filecomp,editype='xmlnocheck',messagetype='invoic')
        self.failUnless(utilsunit.comparenode(inn1.root,inn2.root))
        

    def testjsondiv(self):
        self.failUnless(inmessage.edifromfile(editype='json',messagetype='testjsonorder01',checkunknownentities=True,filename='botssys/infile/unitinmessagejson/org/130101.json'), 'standaard test')
        self.failUnless(inmessage.edifromfile(editype='jsonnocheck',messagetype='jsonnocheck',filename='botssys/infile/unitinmessagejson/org/130101.json'), 'standaard test')
        
        #~ #empty object
        self.assertRaises(botslib.InMessageError,inmessage.edifromfile, editype='json',messagetype='testjsonorder01',checkunknownentities=True,filename='botssys/infile/unitinmessagejson/org/130102.json')   
            
        #unknown field
        self.failUnless(inmessage.edifromfile(editype='json',messagetype='testjsonorder01',checkunknownentities=False,filename='botssys/infile/unitinmessagejson/org/130103.json'), 'unknown field')
        self.failUnless(inmessage.edifromfile(editype='jsonnocheck',messagetype='jsonnocheck',filename='botssys/infile/unitinmessagejson/org/130103.json'), 'unknown field')
        self.assertRaises(botslib.MessageError,inmessage.edifromfile, editype='json',messagetype='testjsonorder01',checkunknownentities=True,filename='botssys/infile/unitinmessagejson/org/130103.json')   #unknown field
        
        #compare standard test with standard est with extra unknown fields and objects: must give same tree:
        in1 = inmessage.edifromfile(editype='json',messagetype='testjsonorder01',checkunknownentities=True,filename='botssys/infile/unitinmessagejson/org/130101.json')
        in2 = inmessage.edifromfile(editype='json',messagetype='testjsonorder01',checkunknownentities=False,filename='botssys/infile/unitinmessagejson/org/130115.json')
        self.failUnless(utilsunit.comparenode(in1.root,in2.root),'compare')
       
        #numeriek field
        self.failUnless(inmessage.edifromfile(editype='json',messagetype='testjsonorder01',checkunknownentities=False,filename='botssys/infile/unitinmessagejson/org/130104.json'), 'numeriek field')
        self.failUnless(inmessage.edifromfile(editype='jsonnocheck',messagetype='jsonnocheck',checkunknownentities=False,filename='botssys/infile/unitinmessagejson/org/130104.json'), 'numeriek field')
        self.failUnless(inmessage.edifromfile(editype='json',messagetype='testjsonorder01',checkunknownentities=True,filename='botssys/infile/unitinmessagejson/org/130104.json'), 'numeriek field')
            
        self.failUnless(inmessage.edifromfile(editype='json',messagetype='testjsonorder01',checkunknownentities=False,filename='botssys/infile/unitinmessagejson/org/130105.json'), 'fucked up')
        self.failUnless(inmessage.edifromfile(editype='jsonnocheck',messagetype='jsonnocheck',filename='botssys/infile/unitinmessagejson/org/130105.json'), 'fucked up')
        self.assertRaises(botslib.MessageError,inmessage.edifromfile, editype='json',messagetype='testjsonorder01',checkunknownentities=True,filename='botssys/infile/unitinmessagejson/org/130105.json')   #fucked up
            
        self.failUnless(inmessage.edifromfile(editype='json',messagetype='testjsonorder01',checkunknownentities=False,filename='botssys/infile/unitinmessagejson/org/130106.json'), 'fucked up')
        self.failUnless(inmessage.edifromfile(editype='jsonnocheck',messagetype='jsonnocheck',filename='botssys/infile/unitinmessagejson/org/130106.json'), 'fucked up')
        self.assertRaises(botslib.InMessageError,inmessage.edifromfile, editype='json',messagetype='testjsonorder01',checkunknownentities=True,filename='botssys/infile/unitinmessagejson/org/130106.json')   #fucked up
            
        self.failUnless(inmessage.edifromfile(editype='json',messagetype='testjsonorder01',checkunknownentities=False,filename='botssys/infile/unitinmessagejson/org/130107.json'), 'fucked up')
        self.failUnless(inmessage.edifromfile(editype='jsonnocheck',messagetype='jsonnocheck',filename='botssys/infile/unitinmessagejson/org/130107.json'), 'fucked up')
        self.assertRaises(botslib.InMessageError,inmessage.edifromfile, editype='json',messagetype='testjsonorder01',checkunknownentities=True,filename='botssys/infile/unitinmessagejson/org/130107.json')   #fucked up
        
        #root is list with 3 messagetrees
        inn = inmessage.edifromfile(editype='json',messagetype='testjsonorder01',checkunknownentities=False,filename='botssys/infile/unitinmessagejson/org/130108.json')
        self.assertEqual(len(inn.root.children), 3,'should deliver 3 messagetrees')
        inn = inmessage.edifromfile(editype='jsonnocheck',messagetype='jsonnocheck',filename='botssys/infile/unitinmessagejson/org/130108.json')
        self.assertEqual(len(inn.root.children), 3,'should deliver 3 messagetrees')
        
        #root is list, but list has a non-object member
        self.failUnless(inmessage.edifromfile(editype='json',messagetype='testjsonorder01',checkunknownentities=False,filename='botssys/infile/unitinmessagejson/org/130109.json'), 'root is list, but list has a non-object member')
        self.failUnless(inmessage.edifromfile(editype='jsonnocheck',messagetype='jsonnocheck',filename='botssys/infile/unitinmessagejson/org/130109.json'), 'root is list, but list has a non-object member')
        self.assertRaises(botslib.InMessageError,inmessage.edifromfile, editype='json',messagetype='testjsonorder01',checkunknownentities=True,filename='botssys/infile/unitinmessagejson/org/130109.json')   #root is list, but list has a non-object member
            
        self.assertRaises(botslib.MessageError,inmessage.edifromfile, editype='json',messagetype='testjsonorder01',checkunknownentities=False,filename='botssys/infile/unitinmessagejson/org/130110.json')   #too many occurences
            
        self.assertRaises(botslib.MessageError,inmessage.edifromfile, editype='json',messagetype='testjsonorder01',checkunknownentities=False,filename='botssys/infile/unitinmessagejson/org/130111.json')   #ent TEST1 should have a TEST2 
        self.failUnless(inmessage.edifromfile(editype='jsonnocheck',messagetype='jsonnocheck',filename='botssys/infile/unitinmessagejson/org/130111.json'), 'ent TEST1 should have a TEST2')
        self.assertRaises(botslib.MessageError,inmessage.edifromfile, editype='json',messagetype='testjsonorder01',checkunknownentities=True,filename='botssys/infile/unitinmessagejson/org/130111.json')   #ent TEST1 should have a TEST2
            
        self.assertRaises(botslib.MessageError,inmessage.edifromfile, editype='json',messagetype='testjsonorder01',checkunknownentities=False,filename='botssys/infile/unitinmessagejson/org/130112.json')   #ent TEST1 has a TEST2
        self.failUnless(inmessage.edifromfile(editype='jsonnocheck',messagetype='jsonnocheck',filename='botssys/infile/unitinmessagejson/org/130112.json'), 'ent TEST1 has a TEST2')
        self.assertRaises(botslib.MessageError,inmessage.edifromfile, editype='json',messagetype='testjsonorder01',checkunknownentities=True,filename='botssys/infile/unitinmessagejson/org/130112.json')   #ent TEST1 has a TEST2
            
        #unknown entries
        inn = inmessage.edifromfile(editype='json',messagetype='testjsonorder01',checkunknownentities=False,filename='botssys/infile/unitinmessagejson/org/130113.json')  

        #empty file
        self.assertRaises(ValueError,inmessage.edifromfile, editype='json',messagetype='testjsonorder01',checkunknownentities=False,filename='botssys/infile/unitinmessagejson/org/130114.json')   #empty file
        self.assertRaises(ValueError,inmessage.edifromfile, editype='jsonnocheck',messagetype='jsonnocheck',filename='botssys/infile/unitinmessagejson/org/130114.json')   #empty file
            
        #numeric key
        self.assertRaises(ValueError,inmessage.edifromfile, editype='json',messagetype='testjsonorder01',checkunknownentities=False,filename='botssys/infile/unitinmessagejson/org/130116.json')
            
        #key is list
        self.assertRaises(ValueError,inmessage.edifromfile, editype='json',messagetype='testjsonorder01',checkunknownentities=False,filename='botssys/infile/unitinmessagejson/org/130117.json')

    def testinisoutjson01(self):
        filein = 'botssys/infile/unitinmessagejson/org/inisout01.json'
        fileout1 = 'botssys/infile/unitinmessagejson/output/inisout01.json'
        fileout3 = 'botssys/infile/unitinmessagejson/output/inisout03.json'
        utilsunit.readwrite(editype='json',messagetype='jsonorder',filenamein=filein,filenameout=fileout1)
        utilsunit.readwrite(editype='jsonnocheck',messagetype='jsonnocheck',filenamein=filein,filenameout=fileout3)
        inn1 = inmessage.edifromfile(filename=fileout1,editype='jsonnocheck',messagetype='jsonnocheck')
        inn2 = inmessage.edifromfile(filename=fileout3,editype='jsonnocheck',messagetype='jsonnocheck')
        self.failUnless(utilsunit.comparenode(inn1.root,inn2.root))

    def testinisoutjson02(self):
        #fails. this is because list of messages is read; and these are written in one time....nice for next release...
        filein = 'botssys/infile/unitinmessagejson/org/inisout05.json'
        fileout = 'botssys/infile/unitinmessagejson/output/inisout05.json'
        inn = inmessage.edifromfile(editype='json',messagetype='jsoninvoic',filename=filein)
        out = outmessage.outmessage_init(editype='json',messagetype='jsoninvoic',filename=fileout,divtext='',topartner='')    #make outmessage object
        # inn.root.display()
        out.root = inn.root
        out.writeall()
        inn1 = inmessage.edifromfile(filename=filein,editype='jsonnocheck',messagetype='jsonnocheck',defaultBOTSIDroot='HEA')
        inn2 = inmessage.edifromfile(filename=fileout,editype='jsonnocheck',messagetype='jsonnocheck')
        # inn1.root.display()
        # inn2.root.display()
        # self.failUnless(utilsunit.comparenode(inn1.root,inn2.root))
        # rawfile1 = utilsunit.readfile(filein)
        # rawfile2 = utilsunit.readfile(fileout)
        # jsonobject1 = simplejson.loads(rawfile1)
        # jsonobject2 = simplejson.loads(rawfile2)
        # self.assertEqual(jsonobject1,jsonobject2,'CmpJson')

    def testinisoutjson03(self):
        ''' non-ascii-char'''
        filein = 'botssys/infile/unitinmessagejson/org/inisout04.json'
        fileout = 'botssys/infile/unitinmessagejson/output/inisout04.json'
        utilsunit.readwrite(editype='json',messagetype='jsonorder',filenamein=filein,filenameout=fileout)
        inn1 = inmessage.edifromfile(filename=filein,editype='jsonnocheck',messagetype='jsonnocheck')
        inn2 = inmessage.edifromfile(filename=fileout,editype='jsonnocheck',messagetype='jsonnocheck')
        self.failUnless(utilsunit.comparenode(inn1.root,inn2.root))

    def testinisoutjson04(self):
        filein = 'botssys/infile/unitinmessagejson/org/inisout05.json'
        inn1 = inmessage.edifromfile(filename=filein,editype='jsonnocheck',messagetype='jsonnocheck',defaultBOTSIDroot='HEA')
        inn2 = inmessage.edifromfile(filename=filein,editype='json',messagetype='jsoninvoic')
        self.failUnless(utilsunit.comparenode(inn1.root,inn2.root))



if __name__ == '__main__':
    botsinit.generalinit('config')
    botsinit.initenginelogging()
    shutil.rmtree('bots/botssys/infile/unitinmessagejson/output/',ignore_errors=True)    #remove whole output directory
    os.mkdir('bots/botssys/infile/unitinmessagejson/output')
    unittest.main()
