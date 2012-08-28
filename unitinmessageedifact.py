import unittest
import bots.inmessage as inmessage
import bots.botslib as botslib
import bots.botsinit as botsinit
import utilsunit

'''plugin unitinmessageedifact.zip
    in bots.ini: max_number_errors = 1

'''


class TestInmessage(unittest.TestCase):
    def testEdifact0401(self):
        ''' 0401	Errors in records'''
        self.assertRaises(botslib.InMessageError,inmessage.parse_edi_file,editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0401/040101.edi')
        self.assertRaises(botslib.InMessageError,inmessage.parse_edi_file,editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0401/040102.edi')
        self.assertRaises(botslib.InMessageError,inmessage.parse_edi_file,editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0401/040103.edi')
        self.assertRaises(botslib.InMessageError,inmessage.parse_edi_file,editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0401/040104.edi')
        self.assertRaises(botslib.InMessageError,inmessage.parse_edi_file,editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0401/040105.edi')
        self.assertRaises(botslib.InMessageError,inmessage.parse_edi_file,editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0401/040106.edi')
        self.assertRaises(botslib.MessageError,inmessage.parse_edi_file,editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0401/040107.edi')
        
    def testedifact0403(self):
        #~ #test charsets
        self.assertRaises(botslib.InMessageError,inmessage.parse_edi_file,editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0403/040301.edi')   #UNOA-regular OK for UNOA as UNOC
        self.assertRaises(botslib.InMessageError,inmessage.parse_edi_file,editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0403/040302F-generated.edi')    #UNOA-regular  OK for UNOA as UNOC
        in0= inmessage.parse_edi_file(editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0403/040303.edi')  #UNOA-regular  also UNOA-strict
        in1= inmessage.parse_edi_file(editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0403/040306.edi') #UNOA regular
        in2= inmessage.parse_edi_file(editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0403/T0000000005.edi') #UNOA regular
        in3= inmessage.parse_edi_file(editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0403/T0000000006.edi') #UNOA regular
        for in1node,in2node,in3node in zip(in1.nextmessage(),in2.nextmessage(),in3.nextmessage()):
            self.failUnless(utilsunit.comparenode(in1node.root,in2node.root),'compare')
            self.failUnless(utilsunit.comparenode(in1node.root,in3node.root),'compare')
        
        self.assertRaises(botslib.InMessageError,inmessage.parse_edi_file,editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0403/040305.edi')  #needs UNOA regular
        # in1= inmessage.parse_edi_file(editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0403/040305.edi') #needs UNOA extended
        
        in7= inmessage.parse_edi_file(editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0403/040304.edi')  #UNOB-regular
        in5= inmessage.parse_edi_file(editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0403/T0000000008.edi') #UNOB regular
        in4= inmessage.parse_edi_file(editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0403/T0000000007-generated.edi') #UNOB regular
        
        in6= inmessage.parse_edi_file(editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0403/T0000000009.edi') #UNOC
            
    def testedifact0404(self):
        #envelope tests
        self.assertRaises(botslib.InMessageError,inmessage.parse_edi_file,editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0404/040401.edi')
        self.assertRaises(botslib.InMessageError,inmessage.parse_edi_file,editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0404/040402.edi')
        self.failUnless(inmessage.parse_edi_file(editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0404/040403.edi'), 'standaard test')
        self.assertRaises(botslib.MessageError,inmessage.parse_edi_file,editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0404/040404.edi')
        self.assertRaises(botslib.MessageError,inmessage.parse_edi_file,editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0404/040405.edi')
        self.assertRaises(botslib.InMessageError,inmessage.parse_edi_file,editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0404/040406.edi')
        #self.assertRaises(botslib.InMessageError,inmessage.parse_edi_file,editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0404/040407.edi')  #syntax version '0'; is not checked anymore
        self.assertRaises(botslib.MessageError,inmessage.parse_edi_file,editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0404/040408.edi')
        self.assertRaises(botslib.MessageError,inmessage.parse_edi_file,editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0404/040409.edi')
        self.failUnless(inmessage.parse_edi_file(editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0404/040410.edi'), 'standaard test')
        self.assertRaises(botslib.InMessageError,inmessage.parse_edi_file,editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0404/040411.edi')
        self.assertRaises(botslib.InMessageError,inmessage.parse_edi_file,editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0404/040412.edi')
        self.assertRaises(botslib.MessageError,inmessage.parse_edi_file,editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0404/040413.edi')
        self.assertRaises(botslib.MessageError,inmessage.parse_edi_file,editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0404/040414.edi')
        self.assertRaises(botslib.InMessageError,inmessage.parse_edi_file,editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0404/040415.edi')
        self.assertRaises(botslib.InMessageError,inmessage.parse_edi_file,editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0404/040416.edi')
        self.assertRaises(botslib.InMessageError,inmessage.parse_edi_file,editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0404/040417.edi')
        self.assertRaises(botslib.InMessageError,inmessage.parse_edi_file,editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0404/040418.edi')
        
    def testedifact0407(self):
        #lex test with characters in strange places
        self.assertRaises(botslib.InMessageError,inmessage.parse_edi_file,editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0407/040701.edi')
        self.failUnless(inmessage.parse_edi_file(editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0407/040702.edi'), 'standaard test')
        self.assertRaises(botslib.InMessageError,inmessage.parse_edi_file,editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0407/040703.edi')
        self.assertRaises(botslib.InMessageError,inmessage.parse_edi_file,editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0407/040704.edi')
        self.failUnless(inmessage.parse_edi_file(editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0407/040705.edi'), 'standaard test')
        self.failUnless(inmessage.parse_edi_file(editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0407/040706.edi'), 'UNOA Crtl-Z at end')
        self.failUnless(inmessage.parse_edi_file(editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0407/040707.edi'), 'UNOB Crtl-Z at end')
        self.failUnless(inmessage.parse_edi_file(editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0407/040708.edi'), 'UNOC Crtl-Z at end')

    def testedifact0408(self):
        #differentenvelopingsamecontent: 1rst UNH per UNB, 2nd has 2 UNB for all UNH's, 3rd has UNG-UNE
        in1= inmessage.parse_edi_file(editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0408/040801.edi')
        in2= inmessage.parse_edi_file(editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0408/040802.edi')
        in3= inmessage.parse_edi_file(editype='edifact',messagetype='edifact',filename='botssys/infile/unitinmessageedifact/0408/040803.edi')
        for in1node,in2node,in3node in zip(in1.nextmessage(),in2.nextmessage(),in3.nextmessage()):
            self.failUnless(utilsunit.comparenode(in1node.root,in2node.root),'compare')
            self.failUnless(utilsunit.comparenode(in1node.root,in3node.root),'compare')


if __name__ == '__main__':
    botsinit.generalinit('config')
    botsinit.initenginelogging()
    unittest.main()
