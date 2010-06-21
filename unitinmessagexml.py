import os
import unittest
import shutil
import bots.inmessage as inmessage
import bots.outmessage as outmessage
import filecmp 
import bots.botslib as botslib
import bots.botsinit as botsinit
import utilsunit

''' pluging unitinmessagexml.zip'''

class TestInmessage(unittest.TestCase):
    ''' Read messages; some should be OK (True), some shoudl give errors (False).
        Tets per editype.
    '''
    def setUp(self):
        pass

    def testxml(self):
        #~ #empty file
        self.assertRaises(SyntaxError,inmessage.edifromfile, editype='xmlnocheck',messagetype='xmlnocheck',filename='botssys/infile/unitinmessagexml/xml/110401.xml')
        self.assertRaises(SyntaxError,inmessage.edifromfile, editype='xml',messagetype='testxml', filename='botssys/infile/unitinmessagexml/xml/110401.xml')
        self.assertRaises(SyntaxError,inmessage.edifromfile, editype='xml',messagetype='testxml',checkunknownentities=True, filename='botssys/infile/unitinmessagexml/xml/110401.xml')
        self.assertRaises(SyntaxError,inmessage.edifromfile, editype='xml',messagetype='testxmlflatten', filename='botssys/infile/unitinmessagexml/xml/110401.xml')
        #only root record in 110402.xml
        self.failUnless(inmessage.edifromfile(editype='xmlnocheck',messagetype='xmlnocheck',filename='botssys/infile/unitinmessagexml/xml/110402.xml'), 'only a root tag; should be OK')
        self.assertRaises(botslib.MessageError,inmessage.edifromfile, editype='xml',messagetype='testxml',filename='botssys/infile/unitinmessagexml/xml/110402.xml')
        self.assertRaises(botslib.MessageError,inmessage.edifromfile, editype='xml',messagetype='testxml',checkunknownentities=True, filename='botssys/infile/unitinmessagexml/xml/110402.xml')
        self.assertRaises(botslib.MessageError,inmessage.edifromfile, editype='xml',messagetype='testxmlflatten',filename='botssys/infile/unitinmessagexml/xml/110402.xml')
            
        #root tag different from grammar
        self.assertRaises(botslib.InMessageError,inmessage.edifromfile, editype='xml',messagetype='testxml',filename='botssys/infile/unitinmessagexml/xml/110406.xml')
        self.assertRaises(botslib.InMessageError,inmessage.edifromfile, editype='xml',messagetype='testxml',checkunknownentities=True, filename='botssys/infile/unitinmessagexml/xml/110406.xml')
        self.assertRaises(botslib.InMessageError,inmessage.edifromfile, editype='xml',messagetype='testxmlflatten',filename='botssys/infile/unitinmessagexml/xml/110406.xml')
        #root tag is double
        self.assertRaises(SyntaxError,inmessage.edifromfile, editype='xmlnocheck',messagetype='xmlnocheck',filename='botssys/infile/unitinmessagexml/xml/110407.xml')
        #invalid: no closing tag
        self.assertRaises(SyntaxError,inmessage.edifromfile, editype='xmlnocheck',messagetype='xmlnocheck',filename='botssys/infile/unitinmessagexml/xml/110408.xml')
        #invalid: extra closing tag
        self.assertRaises(SyntaxError,inmessage.edifromfile, editype='xmlnocheck',messagetype='xmlnocheck',filename='botssys/infile/unitinmessagexml/xml/110409.xml')
        #invalid: mandatory xml-element missing
        self.failUnless(inmessage.edifromfile(editype='xmlnocheck',messagetype='xmlnocheck',filename='botssys/infile/unitinmessagexml/xml/110410.xml'), '')
        self.assertRaises(botslib.MessageError,inmessage.edifromfile, editype='xml',messagetype='testxml',filename='botssys/infile/unitinmessagexml/xml/110410.xml')
        self.assertRaises(botslib.MessageError,inmessage.edifromfile, editype='xml',messagetype='testxml',checkunknownentities=True, filename='botssys/infile/unitinmessagexml/xml/110410.xml')
        self.assertRaises(botslib.MessageError,inmessage.edifromfile, editype='xml',messagetype='testxmlflatten',filename='botssys/infile/unitinmessagexml/xml/110410.xml')
            
        #invalid: to many occurences
        self.assertRaises(botslib.MessageError,inmessage.edifromfile, editype='xml',messagetype='testxml',filename='botssys/infile/unitinmessagexml/xml/110411.xml')
        self.assertRaises(botslib.MessageError,inmessage.edifromfile, editype='xml',messagetype='testxml',checkunknownentities=True, filename='botssys/infile/unitinmessagexml/xml/110411.xml')
            
        #invalid: missing mandatory xml attribute
        self.assertRaises(botslib.MessageError,inmessage.edifromfile, editype='xml',messagetype='testxml',filename='botssys/infile/unitinmessagexml/xml/110412.xml')
        self.assertRaises(botslib.MessageError,inmessage.edifromfile, editype='xml',messagetype='testxml',checkunknownentities=True,filename='botssys/infile/unitinmessagexml/xml/110412.xml')
       
        #unknown xml element
        self.assertRaises(botslib.MessageError,inmessage.edifromfile, editype='xml',messagetype='testxml',checkunknownentities=True,filename='botssys/infile/unitinmessagexml/xml/110413.xml')
        self.assertRaises(botslib.InMessageError,inmessage.edifromfile, editype='xml',messagetype='testxml',checkunknownentities=True,filename='botssys/infile/unitinmessagexml/xml/110414.xml')
            
        #2x the same xml attribute
        self.assertRaises(SyntaxError,inmessage.edifromfile, editype='xml',messagetype='testxml',filename='botssys/infile/unitinmessagexml/xml/110415.xml')
        self.assertRaises(SyntaxError,inmessage.edifromfile, editype='xml',messagetype='testxml',checkunknownentities=True,filename='botssys/infile/unitinmessagexml/xml/110415.xml')
        
        #messages with all max occurences, use attributes, etc
        in1 = inmessage.edifromfile(editype='xml',messagetype='testxml',filename='botssys/infile/unitinmessagexml/xml/110416.xml') #all elements, attributes
        
        #other order of xml elements; should esult in the same node tree
        in1 = inmessage.edifromfile(editype='xml',messagetype='testxml',filename='botssys/infile/unitinmessagexml/xml/110417.xml') #as 18., other order of elements
        in2 = inmessage.edifromfile(editype='xml',messagetype='testxml',filename='botssys/infile/unitinmessagexml/xml/110418.xml') 
        self.failUnless(utilsunit.comparenode(in2.root,in1.root),'compare')

        #??what is tested here??
        inn7= inmessage.edifromfile(editype='xml',messagetype='testxml',checkunknownentities=True,filename='botssys/infile/unitinmessagexml/xml/110405.xml')  #with <?xml version="1.0" encoding="utf-8"?>
        inn8= inmessage.edifromfile(editype='xml',messagetype='testxmlflatten',checkunknownentities=True,filename='botssys/infile/unitinmessagexml/xml/110405.xml')  #with <?xml version="1.0" encoding="utf-8"?>
        self.failUnless(utilsunit.comparenode(inn7.root,inn8.root),'compare')
        
        #~ #test different file which should give equal results
        in1= inmessage.edifromfile(editype='xmlnocheck',messagetype='xmlnocheck',filename='botssys/infile/unitinmessagexml/xml/110403.xml')    #no grammar used
        in5= inmessage.edifromfile(editype='xmlnocheck',messagetype='xmlnocheck',filename='botssys/infile/unitinmessagexml/xml/110404.xml')    #no grammar used
        in6= inmessage.edifromfile(editype='xmlnocheck',messagetype='xmlnocheck',filename='botssys/infile/unitinmessagexml/xml/110405.xml')    #no grammar used
        in2= inmessage.edifromfile(editype='xml',messagetype='testxml',filename='botssys/infile/unitinmessagexml/xml/110403.xml')  #with <?xml version="1.0" encoding="utf-8"?>
        in3= inmessage.edifromfile(editype='xml',messagetype='testxml',filename='botssys/infile/unitinmessagexml/xml/110404.xml')  #without <?xml version="1.0" encoding="utf-8"?>
        in4= inmessage.edifromfile(editype='xml',messagetype='testxml',filename='botssys/infile/unitinmessagexml/xml/110405.xml')  #use cr/lf and whitespace for 'nice' xml
        self.failUnless(utilsunit.comparenode(in2.root,in1.root),'compare')
        self.failUnless(utilsunit.comparenode(in2.root,in3.root),'compare')
        self.failUnless(utilsunit.comparenode(in2.root,in4.root),'compare')
        self.failUnless(utilsunit.comparenode(in2.root,in5.root),'compare')
        self.failUnless(utilsunit.comparenode(in2.root,in6.root),'compare')

        #~ #test different file which should give equal results; flattenxml=True,
        in1= inmessage.edifromfile(editype='xmlnocheck',messagetype='xmlnocheck',filename='botssys/infile/unitinmessagexml/xml/110403.xml')    #no grammar used
        in5= inmessage.edifromfile(editype='xmlnocheck',messagetype='xmlnocheck',filename='botssys/infile/unitinmessagexml/xml/110404.xml')    #no grammar used
        in6= inmessage.edifromfile(editype='xmlnocheck',messagetype='xmlnocheck',filename='botssys/infile/unitinmessagexml/xml/110405.xml')    #no grammar used
        in4= inmessage.edifromfile(editype='xml',messagetype='testxmlflatten',filename='botssys/infile/unitinmessagexml/xml/110405.xml')  #use cr/lf and whitespace for 'nice' xml
        in2= inmessage.edifromfile(editype='xml',messagetype='testxmlflatten',filename='botssys/infile/unitinmessagexml/xml/110403.xml')  #with <?xml version="1.0" encoding="utf-8"?>
        in3= inmessage.edifromfile(editype='xml',messagetype='testxmlflatten',filename='botssys/infile/unitinmessagexml/xml/110404.xml')  #without <?xml version="1.0" encoding="utf-8"?>
        self.failUnless(utilsunit.comparenode(in2.root,in1.root),'compare')
        self.failUnless(utilsunit.comparenode(in2.root,in3.root),'compare')
        self.failUnless(utilsunit.comparenode(in2.root,in4.root),'compare')
        self.failUnless(utilsunit.comparenode(in2.root,in5.root),'compare')
        self.failUnless(utilsunit.comparenode(in2.root,in6.root),'compare')


class Testinisoutxml(unittest.TestCase):
    def testxml01a(self):
        ''' check  xml; new behaviour'''
        filenamein='botssys/infile/unitinmessagexml/xml/inisout02.xml'
        filenameout='botssys/infile/unitinmessagexml/output/inisout01a.xml'
        utilsunit.readwrite(editype='xml',messagetype='xmlorder',filenamein=filenamein,filenameout=filenameout)
        self.failUnless(filecmp.cmp('bots/' + filenameout,'bots/' + filenamein))
        
    def testxml02a(self):
        ''' check xmlnoccheck; new behaviour'''
        filenamein='botssys/infile/unitinmessagexml/xml/inisout02.xml'
        filenametmp='botssys/infile/unitinmessagexml/output/inisout02tmpa.xml'
        filenameout='botssys/infile/unitinmessagexml/output/inisout02a.xml'
        utilsunit.readwrite(editype='xmlnocheck',messagetype='xmlnocheck',filenamein=filenamein,filenameout=filenametmp)
        utilsunit.readwrite(editype='xml',messagetype='xmlorder',filenamein=filenametmp,filenameout=filenameout)
        self.failUnless(filecmp.cmp('bots/' + filenameout,'bots/' + filenamein))
        
    def testxml03(self):
        ''' check  xml (different grammar)'''
        filenamein='botssys/infile/unitinmessagexml/xml/110419.xml'
        filenameout='botssys/infile/unitinmessagexml/output/inisout03.xml'
        utilsunit.readwrite(editype='xml',messagetype='testxmlflatten',charset='utf-8',filenamein=filenamein,filenameout=filenameout)
        self.failUnless(filecmp.cmp('bots/' + filenamein,'bots/' + filenameout))
        
    def testxml04(self):
        ''' check xmlnoccheck'''
        filenamein='botssys/infile/unitinmessagexml/xml/110419.xml'
        filenametmp='botssys/infile/unitinmessagexml/output/inisout04tmp.xml'
        filenameout='botssys/infile/unitinmessagexml/output/inisout04.xml'
        utilsunit.readwrite(editype='xmlnocheck',messagetype='xmlnocheck',charset='utf-8',filenamein=filenamein,filenameout=filenametmp)
        utilsunit.readwrite(editype='xml',messagetype='testxmlflatten',charset='utf-8',filenamein=filenametmp,filenameout=filenameout)
        self.failUnless(filecmp.cmp('bots/' + filenamein,'bots/' + filenameout))

    def testxml05(self):
        ''' test xml;  iso-8859-1'''
        filenamein='botssys/infile/unitinmessagexml/xml/inisout03.xml'
        filenamecmp='botssys/infile/unitinmessagexml/xml/inisoutcompare05.xml'
        filenameout='botssys/infile/unitinmessagexml/output/inisout05.xml'
        utilsunit.readwrite(editype='xml',messagetype='testxml',filenamein=filenamein,filenameout=filenameout,charset='ISO-8859-1')
        self.failUnless(filecmp.cmp('bots/' + filenameout,'bots/' + filenamecmp))
        
    def testxml06(self):
        ''' test xmlnocheck; iso-8859-1'''
        filenamein='botssys/infile/unitinmessagexml/xml/inisout03.xml'
        filenametmp='botssys/infile/unitinmessagexml/output/inisout05tmp.xml'
        filenamecmp='botssys/infile/unitinmessagexml/xml/inisoutcompare05.xml'
        filenameout='botssys/infile/unitinmessagexml/output/inisout05a.xml'
        utilsunit.readwrite(editype='xmlnocheck',messagetype='xmlnocheck',filenamein=filenamein,filenameout=filenametmp,charset='ISO-8859-1')
        utilsunit.readwrite(editype='xml',messagetype='testxml',filenamein=filenametmp,filenameout=filenameout,charset='ISO-8859-1')
        self.failUnless(filecmp.cmp('bots/' + filenameout,'bots/' + filenamecmp))
        
    def testxml09(self):
        ''' BOM;; BOM is not written....'''
        filenamein='botssys/infile/unitinmessagexml/xml/inisout05.xml'
        filenamecmp='botssys/infile/unitinmessagexml/xml/inisout04.xml'
        filenameout='botssys/infile/unitinmessagexml/output/inisout09.xml'
        utilsunit.readwrite(editype='xml',messagetype='testxml',filenamein=filenamein,filenameout=filenameout,charset='utf-8')
        self.failUnless(filecmp.cmp('bots/' + filenameout,'bots/' + filenamecmp))
        
    def testxml10(self):
        ''' BOM;; BOM is not written....'''
        filenamein='botssys/infile/unitinmessagexml/xml/inisout05.xml'
        filenametmp='botssys/infile/unitinmessagexml/output/inisout10tmp.xml'
        filenameout='botssys/infile/unitinmessagexml/output/inisout10.xml'
        filenamecmp='botssys/infile/unitinmessagexml/xml/inisout04.xml'
        utilsunit.readwrite(editype='xmlnocheck',messagetype='xmlnocheck',filenamein=filenamein,filenameout=filenametmp)
        utilsunit.readwrite(editype='xml',messagetype='testxml',filenamein=filenametmp,filenameout=filenameout,charset='utf-8')
        self.failUnless(filecmp.cmp('bots/' + filenameout,'bots/' + filenamecmp))
        
    def testxml11(self):
        ''' check  xml; new behaviour; use standalone parameter'''
        filenamein='botssys/infile/unitinmessagexml/xml/inisout06.xml'
        filenameout='botssys/infile/unitinmessagexml/output/inisout11.xml'
        filenamecmp='botssys/infile/unitinmessagexml/xml/inisout02.xml'
        utilsunit.readwrite(editype='xml',messagetype='xmlorder',filenamein=filenamein,filenameout=filenameout,standalone=None)
        self.failUnless(filecmp.cmp('bots/' + filenameout,'bots/' + filenamecmp))
        
    def testxml11a(self):
        ''' check  xml; new behaviour; use standalone parameter'''
        filenamein='botssys/infile/unitinmessagexml/xml/inisout06.xml'
        filenameout='botssys/infile/unitinmessagexml/output/inisout11a.xml'
        utilsunit.readwrite(editype='xml',messagetype='xmlorder',filenamein=filenamein,filenameout=filenameout,standalone='no')
        self.failUnless(filecmp.cmp('bots/' + filenameout,'bots/' + filenamein))
        
    def testxml12(self):
        ''' check xmlnoccheck; new behaviour use standalone parameter'''
        filenamein='botssys/infile/unitinmessagexml/xml/inisout06.xml'
        filenametmp='botssys/infile/unitinmessagexml/output/inisout12tmp.xml'
        filenameout='botssys/infile/unitinmessagexml/output/inisout12.xml'
        utilsunit.readwrite(editype='xmlnocheck',messagetype='xmlnocheck',filenamein=filenamein,filenameout=filenametmp,standalone='no')
        utilsunit.readwrite(editype='xml',messagetype='xmlorder',filenamein=filenametmp,filenameout=filenameout,standalone='no')
        self.failUnless(filecmp.cmp('bots/' + filenameout,'bots/' + filenamein))
        
    def testxml13(self):
        ''' check  xml; read doctype&write doctype'''
        filenamein='botssys/infile/unitinmessagexml/xml/inisout13.xml'
        filenameout='botssys/infile/unitinmessagexml/output/inisout13.xml'
        utilsunit.readwrite(editype='xml',messagetype='xmlorder',filenamein=filenamein,filenameout=filenameout,DOCTYPE = 'mydoctype SYSTEM "mydoctype.dtd"')
        self.failUnless(filecmp.cmp('bots/' + filenameout,'bots/' + filenamein))
        
    def testxml14(self):
        ''' check xmlnoccheck;  read doctype&write doctype'''
        filenamein='botssys/infile/unitinmessagexml/xml/inisout13.xml'
        filenametmp='botssys/infile/unitinmessagexml/output/inisout14tmp.xml'
        filenameout='botssys/infile/unitinmessagexml/output/inisout14.xml'
        utilsunit.readwrite(editype='xmlnocheck',messagetype='xmlnocheck',filenamein=filenamein,filenameout=filenametmp,DOCTYPE = 'mydoctype SYSTEM "mydoctype.dtd"')
        utilsunit.readwrite(editype='xml',messagetype='xmlorder',filenamein=filenametmp,filenameout=filenameout,DOCTYPE = 'mydoctype SYSTEM "mydoctype.dtd"')
        self.failUnless(filecmp.cmp('bots/' + filenameout,'bots/' + filenamein))
        
    def testxml15(self):
        ''' check  xml; read processing_instructions&write processing_instructions'''
        filenamein='botssys/infile/unitinmessagexml/xml/inisout15.xml'
        filenameout='botssys/infile/unitinmessagexml/output/inisout15.xml'
        utilsunit.readwrite(editype='xml',messagetype='xmlorder',filenamein=filenamein,filenameout=filenameout,processing_instructions=[('xml-stylesheet' ,'href="mystylesheet.xsl" type="text/xml"'),('type-of-ppi' ,'attr1="value1" attr2="value2"')])
        self.failUnless(filecmp.cmp('bots/' + filenameout,'bots/' + filenamein))
        
    def testxml16(self):
        ''' check xmlnoccheck;  read processing_instructions&write processing_instructions'''
        filenamein='botssys/infile/unitinmessagexml/xml/inisout15.xml'
        filenametmp='botssys/infile/unitinmessagexml/output/inisout16tmp.xml'
        filenameout='botssys/infile/unitinmessagexml/output/inisout16.xml'
        utilsunit.readwrite(editype='xmlnocheck',messagetype='xmlnocheck',filenamein=filenamein,filenameout=filenametmp,processing_instructions=[('xml-stylesheet' ,'href="mystylesheet.xsl" type="text/xml"'),('type-of-ppi' ,'attr1="value1" attr2="value2"')])
        utilsunit.readwrite(editype='xml',messagetype='xmlorder',filenamein=filenametmp,filenameout=filenameout,processing_instructions=[('xml-stylesheet' ,'href="mystylesheet.xsl" type="text/xml"'),('type-of-ppi' ,'attr1="value1" attr2="value2"')])
        self.failUnless(filecmp.cmp('bots/' + filenameout,'bots/' + filenamein))
        
    def testxml17(self):
        ''' check  xml; read processing_instructions&doctype&comments. Do not write these.'''
        filenamein='botssys/infile/unitinmessagexml/xml/inisout17.xml'
        filenameout='botssys/infile/unitinmessagexml/output/inisout17.xml'
        filenamecmp='botssys/infile/unitinmessagexml/xml/inisout02.xml'
        utilsunit.readwrite(editype='xml',messagetype='xmlorder',filenamein=filenamein,filenameout=filenameout)
        self.failUnless(filecmp.cmp('bots/' + filenameout,'bots/' + filenamecmp))
        
    def testxml18(self):
        ''' check  xml; read processing_instructions&doctype&comments. Do not write these.'''
        filenamein='botssys/infile/unitinmessagexml/xml/inisout17.xml'
        filenametmp='botssys/infile/unitinmessagexml/output/inisout18tmp.xml'
        filenameout='botssys/infile/unitinmessagexml/output/inisout18.xml'
        filenamecmp='botssys/infile/unitinmessagexml/xml/inisout02.xml'
        utilsunit.readwrite(editype='xmlnocheck',messagetype='xmlnocheck',filenamein=filenamein,filenameout=filenametmp)
        utilsunit.readwrite(editype='xml',messagetype='xmlorder',filenamein=filenametmp,filenameout=filenameout)
        self.failUnless(filecmp.cmp('bots/' + filenameout,'bots/' + filenamecmp))
        
    def testxml19(self):
        ''' check  xml; indented; use lot of options.'''
        filenamein='botssys/infile/unitinmessagexml/xml/inisout02.xml'
        filenameout='botssys/infile/unitinmessagexml/output/inisout19.xml'
        filenamecmp='botssys/infile/unitinmessagexml/xml/inisout19.xml'
        utilsunit.readwrite(editype='xml',messagetype='xmlorder',filenamein=filenamein,filenameout=filenameout,indented=True,standalone='yes',DOCTYPE = 'mydoctype SYSTEM "mydoctype.dtd"',processing_instructions=[('xml-stylesheet' ,'href="mystylesheet.xsl" type="text/xml"'),('type-of-ppi' ,'attr1="value1" attr2="value2"')])
        self.failUnless(filecmp.cmp('bots/' + filenameout,'bots/' + filenamecmp))
        
    def testxml20(self):
        ''' check  xml; indented; use lot of options.'''
        filenamein='botssys/infile/unitinmessagexml/xml/inisout02.xml'
        filenametmp='botssys/infile/unitinmessagexml/output/inisout20tmp.xml'
        filenameout='botssys/infile/unitinmessagexml/output/inisout20.xml'
        filenamecmp='botssys/infile/unitinmessagexml/xml/inisout19.xml'
        utilsunit.readwrite(editype='xmlnocheck',messagetype='xmlnocheck',filenamein=filenamein,filenameout=filenametmp,indented=True,standalone='yes',DOCTYPE = 'mydoctype SYSTEM "mydoctype.dtd"',processing_instructions=[('xml-stylesheet' ,'href="mystylesheet.xsl" type="text/xml"'),('type-of-ppi' ,'attr1="value1" attr2="value2"')])
        utilsunit.readwrite(editype='xml',messagetype='xmlorder',filenamein=filenametmp,filenameout=filenameout,indented=True,standalone='yes',DOCTYPE = 'mydoctype SYSTEM "mydoctype.dtd"',processing_instructions=[('xml-stylesheet' ,'href="mystylesheet.xsl" type="text/xml"'),('type-of-ppi' ,'attr1="value1" attr2="value2"')])
        self.failUnless(filecmp.cmp('bots/' + filenameout,'bots/' + filenamecmp))
        



if __name__ == '__main__':
    botsinit.generalinit('config')
    #~ botslib.initbotscharsets()
    botsinit.initenginelogging()
    shutil.rmtree('bots/botssys/infile/unitinmessagexml/output',ignore_errors=True)    #remove whole output directory
    os.mkdir('bots/botssys/infile/unitinmessagexml/output')
    unittest.main()
