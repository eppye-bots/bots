import os
import unittest
import shutil
import bots.inmessage as inmessage
import bots.outmessage as outmessage
import filecmp 
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
    #~ #***********************************************************************
    #~ #***********test json eg list of article (as eg used in database comm *******
    #~ #***********************************************************************
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
        
        #empty object
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
        #~ inn.root.display()
        out.root = inn.root
        out.writeall()
        inn1 = inmessage.edifromfile(filename=filein,editype='jsonnocheck',messagetype='jsonnocheck',defaultBOTSIDroot='HEA')
        inn2 = inmessage.edifromfile(filename=fileout,editype='jsonnocheck',messagetype='jsonnocheck')
        #~ inn1.root.display()
        #~ inn2.root.display()
        #~ self.failUnless(utilsunit.comparenode(inn1.root,inn2.root))
        #~ rawfile1 = utilsunit.readfile(filein)
        #~ rawfile2 = utilsunit.readfile(fileout)
        #~ jsonobject1 = simplejson.loads(rawfile1)
        #~ jsonobject2 = simplejson.loads(rawfile2)
        #~ self.assertEqual(jsonobject1,jsonobject2,'CmpJson')

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

#************************************************************************
#************************************************************************
#************************************************************************
#************************************************************************
#************************************************************************
    #~ def testxml01(self):
        #~ ''' check  01.xml the same after rad&write/check '''
        #~ filein = 'botssys/infile/unitinmessagejson/org/01.xml'
        #~ fileout = 'botssys/infile/unitinmessagejson/output/01.xml'
        #~ utilsunit.readwrite(editype='xml',messagetype='articles',filenamein=filein,filenameout=fileout)
        #~ self.failUnless(filecmp.cmp(filein,fileout))
        
    #~ def testxmlnocheck01(self):
        #~ ''' check  01.xml the same after rad&write/nocheck '''
        #~ filein = 'botssys/infile/unitinmessagejson/org/01.xml'
        #~ fileout = 'botssys/infile/unitinmessagejson/output/02.xml'
        #~ utilsunit.readwrite(editype='xmlnocheck',messagetype='articles',filenamein=filein,filenameout=fileout)
        #~ self.failUnless(filecmp.cmp(filein,fileout))
        
    #~ def testjson2xml(self):          
        #~ ''' check json->xml same output'''
        #~ filein = 'botssys/infile/unitinmessagejson/org/01.jsn'
        #~ fileout = 'botssys/infile/unitinmessagejson/output/02.xml'
        #~ filecomp = 'botssys/infile/unitinmessagejson/org/01.xml'
        #~ inn = inmessage.edifromfile(filename=filein,editype='json',messagetype='articles')
        #~ out = outmessage.outmessage_init(filename=fileout,editype='xml',messagetype='articles',divtext='',topartner='')    #make outmessage object
        #~ out.root = inn.root
        #~ out.writeall()
        #~ self.failUnless(filecmp.cmp(filecomp,fileout))

    #~ def testjsonnocheck2xmlnocheck11(self):
        #~ ''' check json->xml same output'''
        #~ filein = 'botssys/infile/unitinmessagejson/org/11.jsn'
        #~ fileout = 'botssys/infile/unitinmessagejson/output/12.xml'
        #~ filecomp = 'botssys/infile/unitinmessagejson/org/11.xml'
        #~ inn = inmessage.edifromfile(filename=filein,editype='jsonnocheck',messagetype='articles')
        #~ out = outmessage.outmessage_init(filename=fileout,editype='xmlnocheck',messagetype='articles',divtext='',topartner='')    #make outmessage object
        #~ out.root = inn.root
        #~ out.writeall()
        #~ self.failUnless(filecmp.cmp(filecomp,fileout))

    #~ def testxml2json(self):
        #~ ''' check xml -> json same output'''
        #~ filein = 'botssys/infile/unitinmessagejson/org/01.xml'
        #~ fileout = 'botssys/infile/unitinmessagejson/output/02.jsn'
        #~ fileout2 = 'botssys/infile/unitinmessagejson/output/03.xml'
        #~ inn = inmessage.edifromfile(filename=filein,editype='xml',messagetype='articles')
        #~ out = outmessage.outmessage_init(filename=fileout,editype='json',messagetype='articles',divtext='',topartner='')    #make outmessage object
        #~ out.root = inn.root
        #~ out.writeall()
        #~ inn = inmessage.edifromfile(filename=fileout,editype='json',messagetype='articles')
        #~ out = outmessage.outmessage_init(filename=fileout2,editype='xml',messagetype='articles',divtext='',topartner='')    #make outmessage object
        #~ out.root = inn.root
        #~ out.writeall()
        #~ self.failUnless(filecmp.cmp(filein,fileout2))

    #~ def testxmlnocheck2jsonnocheck(self):
        #~ ''' check xml -> json same output'''
        #~ filein = 'botssys/infile/unitinmessagejson/org/01.xml'
        #~ fileout = 'botssys/infile/unitinmessagejson/output/02.jsn'
        #~ fileout2 = 'botssys/infile/unitinmessagejson/output/03.xml'
        #~ inn = inmessage.edifromfile(filename=filein,editype='xmlnocheck',messagetype='articles')
        #~ out = outmessage.outmessage_init(filename=fileout,editype='jsonnocheck',messagetype='articles',divtext='',topartner='')    #make outmessage object
        #~ out.root = inn.root
        #~ out.writeall()
        #~ inn = inmessage.edifromfile(filename=fileout,editype='jsonnocheck',messagetype='articles')
        #~ out = outmessage.outmessage_init(filename=fileout2,editype='xmlnocheck',messagetype='articles',divtext='',topartner='')    #make outmessage object
        #~ out.root = inn.root
        #~ out.writeall()
        #~ self.failUnless(filecmp.cmp(filein,fileout2))
        
    #~ def testjsonnocheck2xmlnocheck(self):
        #~ ''' check json->xml same output'''
        #~ filein = 'botssys/infile/unitinmessagejson/org/01.jsn'
        #~ fileout = 'botssys/infile/unitinmessagejson/output/02.xml'
        #~ filecomp = 'botssys/infile/unitinmessagejson/org/01.xml'
        #~ inn = inmessage.edifromfile(filename=filein,editype='jsonnocheck',messagetype='articles')
        #~ out = outmessage.outmessage_init(filename=fileout,editype='xmlnocheck',messagetype='articles',divtext='',topartner='')    #make outmessage object
        #~ out.root = inn.root
        #~ out.writeall()
        #~ self.failUnless(filecmp.cmp(filecomp,fileout))



if __name__ == '__main__':
    botsinit.generalinit('/home/hje/botsup/bots/config')
    #~ botslib.initbotscharsets()
    botsinit.initenginelogging()
    shutil.rmtree('bots/botssys/infile/unitinmessagejson/output/',ignore_errors=True)    #remove whole output directory
    os.mkdir('bots/botssys/infile/unitinmessagejson/output')
    unittest.main()

'''
JSON-object: either object or array
    
Object/dict:
    'root' has ONE key/value pair
Array/list:
    
Bots2JSON:
-   recordid (BOTSID) is always extracted from record and used 1 level up.
-   So: BOTSID from botsroot is always extracted separate.
-   objects always in array. Is root a exception?    
JSON2Bots:
-   recordid (BOTSID) is always extracted from record and used 1 level up.
-   So: BOTSID from botsroot is always extracted separate.
-   objects always in array. Is root a exception?    
#############################
#####1 list of eg article####
Bots:
    {'BOTSID': 'articles'}
        {'BOTSID': 'article', 'ccodeid': 'artikel', 'leftcode': 'leftcode2','rightcode': 'rightcode'}
        {'BOTSID': 'article', 'ccodeid': 'artikel', 'leftcode': 'leftcode2','rightcode': 'rightcode'}
JSON var1 - OK, use like it is.
    {'articles': 
        [{'article': 
            [
            {'ccodeid': 'artikel', 'leftcode': 'leftcode', 'rightcode': 'rightcode'}, 
            {'ccodeid': 'artikel', 'leftcode': 'leftcode2', 'rightcode': 'rightcode'},
            ]
        }]
    }
JSON var2
read: create dummy root with root-BOTSID default or from syntax
write: syntax: skiproot=1
    {'article': 
        [
        {'ccodeid': 'artikel', 'leftcode': 'leftcode', 'rightcode': 'rightcode'}, 
        {'ccodeid': 'artikel', 'leftcode': 'leftcode2', 'rightcode': 'rightcode'},
        ]
    }
JSON var3 - Not advised structure... 
read create dummy root. Create root BOTSID (default, from syntax) and level 1 ROOT (default & from syntax)
write: syntax: skiproot=2

    [
    {'ccodeid': 'artikel', 'leftcode': 'leftcode', 'rightcode': 'rightcode'}, 
    {'ccodeid': 'artikel', 'leftcode': 'leftcode2', 'rightcode': 'rightcode'},
    ]
#############################
#####2 messagee####
Bots:
    {'BOTSID': 'message','sender':'sender','receiver':'receiver'
        {'BOTSID': 'line', 'lineid': '1', 'article': '8712345678906','qty': '1'}
        {'BOTSID': 'line', 'lineid': '2', 'article': '8712345678911','qty': '1'}
JSON var1 - OK, use like it is.
    {'message': 
     'line': 
            [
            {'lineid': '1', 'article': '8712345678906','qty': '1'}, 
            {'lineid': '2', 'article': '8712345678911','qty': '1'},
            ]
        }]
    }
JSON var2
read: create dummy root with root-BOTSID default or from syntax
write: syntax: skiproot=1
    {'article': 
        [
        {'ccodeid': 'artikel', 'leftcode': 'leftcode', 'rightcode': 'rightcode'}, 
        {'ccodeid': 'artikel', 'leftcode': 'leftcode2', 'rightcode': 'rightcode'},
        ]
    }
JSON var3 - Not advised structure... 
read create dummy root. Create root BOTSID (default, from syntax) and level 1 ROOT (default & from syntax)
write: syntax: skiproot=2

    [
    {'ccodeid': 'artikel', 'leftcode': 'leftcode', 'rightcode': 'rightcode'}, 
    {'ccodeid': 'artikel', 'leftcode': 'leftcode2', 'rightcode': 'rightcode'},
    ]
'''