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

''' pluging unitinisout.zip'''

class Testinisoutedifact(unittest.TestCase):
    def testedifact02(self):
        infile ='botssys/infile/unitinisout/org/inisout02.edi'
        outfile='botssys/infile/unitinisout/output/inisout02.edi'
        inn = inmessage.edifromfile(editype='edifact',messagetype='orderswithenvelope',filename=infile)
        out = outmessage.outmessage_init(editype='edifact',messagetype='orderswithenvelope',filename=outfile,divtext='',topartner='')    #make outmessage object
        out.root =  inn.root
        out.writeall()
        self.failUnless(filecmp.cmp('bots/' + outfile,'bots/' + infile))
        
    def testedifact03(self):
        #~ #takes quite long
        infile ='botssys/infile/unitinisout/org/inisout03.edi'
        outfile='botssys/infile/unitinisout/output/inisout03.edi'
        inn = inmessage.edifromfile(editype='edifact',messagetype='invoicwithenvelope',filename=infile)
        out = outmessage.outmessage_init(editype='edifact',messagetype='invoicwithenvelope',filename=outfile,divtext='',topartner='')    #make outmessage object
        out.root =  inn.root
        out.writeall()
        self.failUnless(filecmp.cmp('bots/' + outfile,'bots/' + infile))
        
    def testedifact04(self):
        utilsunit.readwrite(editype='edifact',
                    messagetype='orderswithenvelope',
                    filenamein='botssys/infile/unitinisout/0406edifact/040601.edi',
                    filenameout='botssys/infile/unitinisout/output/040601.edi')
        utilsunit.readwrite(editype='edifact',
                    messagetype='orderswithenvelope',
                    filenamein='botssys/infile/unitinisout/0406edifact/040602.edi',
                    filenameout='botssys/infile/unitinisout/output/040602.edi')
        utilsunit.readwrite(editype='edifact',
                    messagetype='orderswithenvelope',
                    filenamein='botssys/infile/unitinisout/0406edifact/040603.edi',
                    filenameout='botssys/infile/unitinisout/output/040603.edi')
        utilsunit.readwrite(editype='edifact',
                    messagetype='orderswithenvelope',
                    filenamein='botssys/infile/unitinisout/0406edifact/040604.edi',
                    filenameout='botssys/infile/unitinisout/output/040604.edi')
        utilsunit.readwrite(editype='edifact',
                    messagetype='orderswithenvelope',
                    filenamein='botssys/infile/unitinisout/0406edifact/040605.edi',
                    filenameout='botssys/infile/unitinisout/output/040605.edi')
        utilsunit.readwrite(editype='edifact',
                    messagetype='orderswithenvelope',
                    filenamein='botssys/infile/unitinisout/0406edifact/040606.edi',
                    filenameout='botssys/infile/unitinisout/output/040606.edi')
        utilsunit.readwrite(editype='edifact',
                    messagetype='orderswithenvelope',
                    filenamein='botssys/infile/unitinisout/0406edifact/040607.edi',
                    filenameout='botssys/infile/unitinisout/output/040607.edi')
        utilsunit.readwrite(editype='edifact',
                    messagetype='orderswithenvelope',
                    filenamein='botssys/infile/unitinisout/0406edifact/040608.edi',
                    filenameout='botssys/infile/unitinisout/output/040608.edi')
        self.failUnless(filecmp.cmp('bots/botssys/infile/unitinisout/output/040601.edi','bots/botssys/infile/unitinisout/output/040602.edi'))
        self.failUnless(filecmp.cmp('bots/botssys/infile/unitinisout/output/040601.edi','bots/botssys/infile/unitinisout/output/040603.edi'))
        self.failUnless(filecmp.cmp('bots/botssys/infile/unitinisout/output/040601.edi','bots/botssys/infile/unitinisout/output/040604.edi'))
        self.failUnless(filecmp.cmp('bots/botssys/infile/unitinisout/output/040601.edi','bots/botssys/infile/unitinisout/output/040605.edi'))
        self.failUnless(filecmp.cmp('bots/botssys/infile/unitinisout/output/040601.edi','bots/botssys/infile/unitinisout/output/040606.edi'))
        self.failUnless(filecmp.cmp('bots/botssys/infile/unitinisout/output/040601.edi','bots/botssys/infile/unitinisout/output/040607.edi'))
        self.failUnless(filecmp.cmp('bots/botssys/infile/unitinisout/output/040601.edi','bots/botssys/infile/unitinisout/output/040608.edi'))

class Testinisoutinh(unittest.TestCase):
    def testinh01(self):
        filenamein='botssys/infile/unitinisout/org/inisout01.inh'
        filenameout='botssys/infile/unitinisout/output/inisout01.inh'
        inn = inmessage.edifromfile(editype='fixed',messagetype='invoicfixed',filename=filenamein)
        out = outmessage.outmessage_init(editype='fixed',messagetype='invoicfixed',filename=filenameout,divtext='',topartner='')    #make outmessage object
        out.root = inn.root
        out.writeall()
        self.failUnless(filecmp.cmp('bots/' + filenameout,'bots/' + filenamein))
        
    def testidoc01(self):
        filenamein='botssys/infile/unitinisout/org/inisout01.idoc'
        filenameout='botssys/infile/unitinisout/output/inisout01.idoc'
        inn = inmessage.edifromfile(editype='idoc',messagetype='WP_PLU02',filename=filenamein)
        out = outmessage.outmessage_init(editype='idoc',messagetype='WP_PLU02',filename=filenameout,divtext='',topartner='')    #make outmessage object
        out.root = inn.root
        out.writeall()
        self.failUnless(filecmp.cmp('bots/' + filenameout,'bots/' + filenamein))

class Testinisoutx12(unittest.TestCase):
    def testx12_01(self):
        filenamein='botssys/infile/unitinisout/org/inisout01.x12'
        filenameout='botssys/infile/unitinisout/output/inisout01.x12'
        inn = inmessage.edifromfile(editype='x12',messagetype='850withenvelope',filename=filenamein)
        out = outmessage.outmessage_init(editype='x12',messagetype='850withenvelope',filename=filenameout,divtext='',topartner='')    #make outmessage object
        out.root = inn.root
        out.writeall()
        linesfile1 = utilsunit.readfilelines('bots/' + filenamein)
        linesfile2 = utilsunit.readfilelines('bots/' + filenameout)
        self.assertEqual(linesfile1[0][:103],linesfile2[0][:103],'first part of ISA')
        for line1,line2 in zip(linesfile1[1:],linesfile2[1:]):
            self.assertEqual(line1,line2,'Cmplines')
        
    def testx12_02(self):
        filenamein='botssys/infile/unitinisout/org/inisout02.x12'
        filenameout='botssys/infile/unitinisout/output/inisout02.x12'
        inn = inmessage.edifromfile(editype='x12',messagetype='850withenvelope',filename=filenamein)
        out = outmessage.outmessage_init(add_crlfafterrecord_sep='',editype='x12',messagetype='850withenvelope',filename=filenameout,divtext='',topartner='')    #make outmessage object
        out.root = inn.root
        out.writeall()
        linesfile1 = utilsunit.readfile('bots/' + filenamein)
        linesfile2 = utilsunit.readfile('bots/' + filenameout)
        self.assertEqual(linesfile1[:103],linesfile2[:103],'first part of ISA')
        self.assertEqual(linesfile1[105:],linesfile2[103:],'rest of message')
        
class Testinisoutcsv(unittest.TestCase):
    def testcsv001(self):
        filenamein='botssys/infile/unitinisout/org/inisout01.csv'
        filenameout='botssys/infile/unitinisout/output/inisout01.csv'
        utilsunit.readwrite(editype='csv',messagetype='invoic',filenamein=filenamein,filenameout=filenameout)
        self.failUnless(filecmp.cmp('bots/' + filenameout,'bots/' + filenamein))

    def testcsv003(self):
        #utf-charset
        filenamein='botssys/infile/unitinisout/org/inisout03.csv'
        filenameout='botssys/infile/unitinisout/output/inisout03.csv'
        utilsunit.readwrite(editype='csv',messagetype='invoic',filenamein=filenamein,filenameout=filenameout)
        self.failUnless(filecmp.cmp('bots/' + filenameout,'bots/' + filenamein))
        #~ #utf-charset with BOM **error. BOM is not removed by python.
        #~ #utilsunit.readwrite(editype='csv',
        #~ #            messagetype='invoic',
        #~ #            filenamein='botssys/infile/unitinisout/inisout04.csv',
        #~ #            filenameout='botssys/infile/unitinisout/output/inisout04.csv')
        #~ #self.failUnless(filecmp.cmp('botssys/infile/unitinisout/output/inisout04.csv','botssys/infile/unitinisout/inisout04.csv'))


if __name__ == '__main__':
    botsinit.generalinit('/home/hje/botsup/bots/config')
    #~ botslib.initbotscharsets()
    botsinit.initenginelogging()
    shutil.rmtree('bots/botssys/infile/unitinisout/output',ignore_errors=True)    #remove whole output directory
    os.mkdir('bots/botssys/infile/unitinisout/output')
    unittest.main()
