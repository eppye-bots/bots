import unittest
import bots.botslib as botslib
import bots.botsinit as botsinit
import bots.inmessage as inmessage
import bots.outmessage as outmessage 
from bots.botsconfig import *
import utilsunit

''' plugin unitformats '''
#python 2.6 treats -0 different. in outmessage this is adapted, for inmessage: python 2.6 does this correct

testdummy={MPATH:'dummy for tests'}
class TestFormatFieldVariableOutmessage(unittest.TestCase):
    def setUp(self):
        self.edi = outmessage.outmessage_init(messagetype='edifact',editype='edifact')
    def test_out_formatfield_var_R(self):
        self.edi.ta_info['lengthnumericbare']=True
        self.edi.ta_info['decimaal']='.'
        tfield1 = ['TEST1','M',3,'R',True,0,       0,       'R']
        #                    length    decimals minlength  format
        self.assertEqual(self.edi._formatfield('',tfield1,testdummy), '','empty string')
        self.assertEqual(self.edi._formatfield('1',tfield1,testdummy), '1', 'basic')
        self.assertEqual(self.edi._formatfield(' 1',tfield1,testdummy), '1', 'basic')
        self.assertEqual(self.edi._formatfield('1 ',tfield1,testdummy), '1', 'basic')
        self.assertEqual(self.edi._formatfield('0',tfield1,testdummy), '0','zero stays zero')
        self.assertEqual(self.edi._formatfield('-0',tfield1,testdummy), '-0','neg.zero stays neg.zero')
        self.assertEqual(self.edi._formatfield('-0.00',tfield1,testdummy), '-0.00','')
        self.assertEqual(self.edi._formatfield('-.12',tfield1,testdummy), '-0.12','no zero before dec,sign is OK')
        self.assertEqual(self.edi._formatfield('123',tfield1,testdummy), '123','numeric field at max')
        self.assertEqual(self.edi._formatfield('001',tfield1,testdummy), '1','leading zeroes are removed')
        self.assertEqual(self.edi._formatfield('0.10',tfield1,testdummy), '0.10','keep zeroes after last dec.digit')
        self.assertEqual(self.edi._formatfield('-1.23',tfield1,testdummy), '-1.23','numeric field at max with minus and decimal sign')
        self.assertEqual(self.edi._formatfield('0001',tfield1,testdummy), '1','strips leading zeroes if possobel')
        self.assertEqual(self.edi._formatfield('+123',tfield1,testdummy), '123','strips leading zeroes if possobel')
        self.edi.ta_info['decimaal']=','
        self.assertEqual(self.edi._formatfield('1.23',tfield1,testdummy), '1,23','other dec.sig, replace')
        self.edi.ta_info['decimaal']='.'
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1234',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'-1.234',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1<3',tfield1,testdummy)    #wrong char
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1-3',tfield1,testdummy)    #'-' in middel of number
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'123-',tfield1,testdummy)    #'-' at end of number
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1,3',tfield1,testdummy)    #',', where ',' is not traid sep.
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1+3',tfield1,testdummy)    #'+' in middle of number (no exp)
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1E3',tfield1,testdummy)    #'+' in middle of number (no exp)
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'13+',tfield1,testdummy)    #'+' at end
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'0.100',tfield1,testdummy)   #field too big
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'.',tfield1,testdummy)   #no num
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'-',tfield1,testdummy)   #no num
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'.001',tfield1,testdummy)   #bots adds 0 before dec, thus too big
        #~ #test filling up to min length
        tfield2 = ['TEST1', 'M', 8,   'R', True,   0,      5,'R']
        self.assertEqual(self.edi._formatfield('12345',tfield2,testdummy), '12345','just large enough')
        self.assertEqual(self.edi._formatfield('0.1000',tfield2,testdummy), '0.1000','keep zeroes after last dec.digit')
        self.assertEqual(self.edi._formatfield('00001',tfield2,testdummy), '00001','keep leading zeroes')
        self.assertEqual(self.edi._formatfield('123',tfield2,testdummy), '00123','add leading zeroes')
        self.assertEqual(self.edi._formatfield('.1',tfield2,testdummy), '0000.1','add leading zeroes')
        #~ #test exp
        self.assertEqual(self.edi._formatfield('12E+3',tfield2,testdummy), '12000','Exponent notation is possible')
        self.assertEqual(self.edi._formatfield('12E3',tfield2,testdummy), '12000','Exponent notation is possible->to std notation')
        self.assertEqual(self.edi._formatfield('12e+3',tfield2,testdummy), '12000','Exponent notation is possible; e->E')
        self.assertEqual(self.edi._formatfield('12e3',tfield2,testdummy), '12000','Exponent notation is possible; e->E')
        self.assertEqual(self.edi._formatfield('12345E+3',tfield2,testdummy), '12345000','do not count + and E')
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'12345678E+3',tfield2,testdummy)   #too big with exp
        tfield3 = ['TEST1', 'M', 8,   'R', True,   3,      5,'R']
        #~ print '\n>>>',self.edi._formatfield('12E-3',tfield3,testdummy)
        #~ self.assertEqual(self.edi._formatfield('12E-3',tfield3,testdummy), '00.012','Exponent notation is possible')
        #~ self.assertEqual(self.edi._formatfield('12e-3',tfield2,testdummy), '00.012','Exponent notation is possible; e->E')
        #~ self.assertEqual(self.edi._formatfield('12345678E-3',tfield2,testdummy), '12345.678','do not count + and E')
        #~ self.assertEqual(self.edi._formatfield('12345678E-7',tfield2,testdummy), '1.2345678','do not count + and E')
        #~ self.assertEqual(self.edi._formatfield('123456E-7',tfield2,testdummy), '0.0123456','do not count + and E')
        #~ self.assertEqual(self.edi._formatfield('1234567E-7',tfield2,testdummy), '0.1234567','do not count + and E')
        #~ self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'12345678E-8',tfield2,testdummy)   #gets 0.12345678, is too big
        #~ self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'12345678E+3',tfield2,testdummy)   #too big with exp
        tfield4 = ['TEST1', 'M', 80,   'R', True,   3,      0,'R']
        self.assertEqual(self.edi._formatfield('12345678901234560',tfield4,testdummy), '12345678901234560','lot of digits')
        #test for lentgh checks if:
        self.edi.ta_info['lengthnumericbare']=False
        self.assertEqual(self.edi._formatfield('-1.45',tfield2,testdummy), '-1.45','just large enough')
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'-12345678',tfield2,testdummy) #field too large

    def test_out_formatfield_var_N(self):
        self.edi.ta_info['decimaal']='.'
        self.edi.ta_info['lengthnumericbare']=True
        tfield1 = ['TEST1','M',5,'N',True,2,       0,       'N']
        #                    length    decimals minlength  format
        self.assertEqual(self.edi._formatfield('',tfield1,testdummy), '','empty string')
        self.assertEqual(self.edi._formatfield('1',tfield1,testdummy), '1.00', 'basic')
        self.assertEqual(self.edi._formatfield(' 1',tfield1,testdummy), '1.00', 'basic')
        self.assertEqual(self.edi._formatfield('1 ',tfield1,testdummy), '1.00', 'basic')
        self.assertEqual(self.edi._formatfield('0',tfield1,testdummy), '0.00','zero stays zero')
        self.assertEqual(self.edi._formatfield('-0',tfield1,testdummy), '-0.00','neg.zero stays neg.zero')
        self.assertEqual(self.edi._formatfield('-0.00',tfield1,testdummy), '-0.00','')
        self.assertEqual(self.edi._formatfield('-0.001',tfield1,testdummy), '-0.00','')
        self.assertEqual(self.edi._formatfield('-.12',tfield1,testdummy), '-0.12','no zero before dec,sign is OK')
        self.assertEqual(self.edi._formatfield('123',tfield1,testdummy), '123.00','numeric field at max')
        self.assertEqual(self.edi._formatfield('001',tfield1,testdummy), '1.00','leading zeroes are removed')
        self.assertEqual(self.edi._formatfield('0.10',tfield1,testdummy), '0.10','keep zeroes after last dec.digit')
        self.assertEqual(self.edi._formatfield('123.1049',tfield1,testdummy), '123.10','keep zeroes after last dec.digit')
        self.assertEqual(self.edi._formatfield('-1.23',tfield1,testdummy), '-1.23','numeric field at max with minus and decimal sign')
        self.assertEqual(self.edi._formatfield('0001',tfield1,testdummy), '1.00','strips leading zeroes if possobel')
        self.assertEqual(self.edi._formatfield('+123',tfield1,testdummy), '123.00','strips leading zeroes if possobel')
        self.edi.ta_info['decimaal']=','
        self.assertEqual(self.edi._formatfield('1.23',tfield1,testdummy), '1,23','other dec.sig, replace')
        self.edi.ta_info['decimaal']='.'
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1234',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'-1234.56',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1<3',tfield1,testdummy)    #wrong char
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1-3',tfield1,testdummy)    #'-' in middel of number
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'123-',tfield1,testdummy)    #'-' at end of number
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1,3',tfield1,testdummy)    #',', where ',' is not traid sep.
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1+3',tfield1,testdummy)    #'+' in middle of number (no exp)
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1E3',tfield1,testdummy)    #'+' in middle of number (no exp)
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'13+',tfield1,testdummy)    #'+' at end
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1234.100',tfield1,testdummy)   #field too big
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'.',tfield1,testdummy)   #no num
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'-',tfield1,testdummy)   #no num
        # #test filling up to min length
        tfield23 = ['TEST1', 'M', 8,   'N', True,   0,      5,'N']
        #~ print self.edi._formatfield('12345.5',tfield23,testdummy)
        self.assertEqual(self.edi._formatfield('12345.5',tfield23,testdummy), '12346','just large enough')
        tfield2 = ['TEST1', 'M', 8,   'N', True,   2,      5,'N']
        self.assertEqual(self.edi._formatfield('123.45',tfield2,testdummy), '123.45','just large enough')
        self.assertEqual(self.edi._formatfield('123.4549',tfield2,testdummy), '123.45','just large enough')
        #~ print self.edi._formatfield('123.455',tfield2,testdummy)
        self.assertEqual(self.edi._formatfield('123.455',tfield2,testdummy), '123.46','just large enough')
        self.assertEqual(self.edi._formatfield('0.1000',tfield2,testdummy), '000.10','keep zeroes after last dec.digit')
        self.assertEqual(self.edi._formatfield('00001',tfield2,testdummy), '001.00','keep leading zeroes')
        self.assertEqual(self.edi._formatfield('12',tfield2,testdummy), '012.00','add leading zeroes')
        self.assertEqual(self.edi._formatfield('.1',tfield2,testdummy), '000.10','add leading zeroes')
        #test exp; bots tries to convert to normal
        self.assertEqual(self.edi._formatfield('178E+3',tfield2,testdummy), '178000.00','add leading zeroes')
        self.assertEqual(self.edi._formatfield('-178E+3',tfield2,testdummy), '-178000.00','add leading zeroes')
        self.assertEqual(self.edi._formatfield('-178e-3',tfield2,testdummy), '-000.18','add leading zeroes')
        self.assertEqual(self.edi._formatfield('-178e-5',tfield2,testdummy), '-000.00','add leading zeroes')
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'178E+4',tfield2,testdummy)   #too big with exp
        tfield4 = ['TEST1', 'M', 80,   'N', True,   3,      0,'N']
        self.assertEqual(self.edi._formatfield('12345678901234560',tfield4,testdummy), '12345678901234560.000','lot of digits')
        self.assertEqual(self.edi._formatfield('1234567890123456789012345',tfield4,testdummy), '1234567890123456789012345.000','lot of digits')

    def test_out_formatfield_var_I(self):
        self.edi.ta_info['lengthnumericbare']=True
        self.edi.ta_info['decimaal']='.'
        tfield1 = ['TEST1','M',5,'I',True,2,       0,       'I']
        #                    length    decimals minlength  format
        self.assertEqual(self.edi._formatfield('',tfield1,testdummy), '','empty string')
        self.assertEqual(self.edi._formatfield('1',tfield1,testdummy), '100', 'basic')
        self.assertEqual(self.edi._formatfield(' 1',tfield1,testdummy), '100', 'basic')
        self.assertEqual(self.edi._formatfield('1 ',tfield1,testdummy), '100', 'basic')
        self.assertEqual(self.edi._formatfield('0',tfield1,testdummy), '0','zero stays zero')
        self.assertEqual(self.edi._formatfield('-0',tfield1,testdummy), '-0','neg.zero stays neg.zero')
        self.assertEqual(self.edi._formatfield('-0.00',tfield1,testdummy), '-0','')
        self.assertEqual(self.edi._formatfield('-0.001',tfield1,testdummy), '-0','')
        self.assertEqual(self.edi._formatfield('-.12',tfield1,testdummy), '-12','no zero before dec,sign is OK')  #TODO: puts ) in front
        self.assertEqual(self.edi._formatfield('123',tfield1,testdummy), '12300','numeric field at max')
        self.assertEqual(self.edi._formatfield('001',tfield1,testdummy), '100','leading zeroes are removed')
        self.assertEqual(self.edi._formatfield('0.10',tfield1,testdummy), '10','keep zeroes after last dec.digit')
        self.assertEqual(self.edi._formatfield('123.1049',tfield1,testdummy), '12310','keep zeroes after last dec.digit')
        self.assertEqual(self.edi._formatfield('-1.23',tfield1,testdummy), '-123','numeric field at max with minus and decimal sign')
        self.assertEqual(self.edi._formatfield('0001',tfield1,testdummy), '100','strips leading zeroes if possobel')
        self.assertEqual(self.edi._formatfield('+123',tfield1,testdummy), '12300','strips leading zeroes if possobel')
        self.edi.ta_info['decimaal']=','
        self.assertEqual(self.edi._formatfield('1.23',tfield1,testdummy), '123','other dec.sig, replace')
        self.edi.ta_info['decimaal']='.'
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1234',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'-1234.56',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1<3',tfield1,testdummy)    #wrong char
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1-3',tfield1,testdummy)    #'-' in middel of number
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'123-',tfield1,testdummy)    #'-' at end of number
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1,3',tfield1,testdummy)    #',', where ',' is not traid sep.
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1+3',tfield1,testdummy)    #'+' in middle of number (no exp)
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1E3',tfield1,testdummy)    #'+' in middle of number (no exp)
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'13+',tfield1,testdummy)    #'+' at end
        self.assertEqual(self.edi._formatfield('+13',tfield1,testdummy), '1300','other dec.sig, replace')
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1+3',tfield1,testdummy)    #'+' in middle of number
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1234.100',tfield1,testdummy)   #field too big
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'.',tfield1,testdummy)   #no num
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'-',tfield1,testdummy)   #no num
        #~ #test filling up to min length
        tfield2 = ['TEST1', 'M', 8,   'I', True,   2,      5,'I']
        self.assertEqual(self.edi._formatfield('123.45',tfield2,testdummy), '12345','just large enough')
        self.assertEqual(self.edi._formatfield('123.4549',tfield2,testdummy), '12345','just large enough')
        self.assertEqual(self.edi._formatfield('123.455',tfield2,testdummy), '12346','just large enough')
        self.assertEqual(self.edi._formatfield('0.1000',tfield2,testdummy), '00010','keep zeroes after last dec.digit')
        self.assertEqual(self.edi._formatfield('00001',tfield2,testdummy), '00100','keep leading zeroes')
        self.assertEqual(self.edi._formatfield('12',tfield2,testdummy), '01200','add leading zeroes')
        self.assertEqual(self.edi._formatfield('.1',tfield2,testdummy), '00010','add leading zeroes')
        #test exp; bots tries to convert to normal
        self.assertEqual(self.edi._formatfield('178E+3',tfield2,testdummy), '17800000','add leading zeroes')
        self.assertEqual(self.edi._formatfield('-178E+3',tfield2,testdummy), '-17800000','add leading zeroes')
        self.assertEqual(self.edi._formatfield('-178e-3',tfield2,testdummy), '-00018','add leading zeroes')
        self.assertEqual(self.edi._formatfield('-178e-5',tfield2,testdummy), '-00000','add leading zeroes')
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'178E+4',tfield2,testdummy)   #too big with exp
        tfield4 = ['TEST1', 'M', 80,   'I', True,   3,      0,'I']
        self.assertEqual(self.edi._formatfield('123456789012340',tfield4,testdummy), '123456789012340000','lot of digits')
        
    def test_out_formatfield_var_D(self):
        tfield1 = ['TEST1', 'M', 20,   'D', True,   0,      0,'D']
        #                    length            decimals minlength 
        self.assertEqual(self.edi._formatfield('20071001',tfield1,testdummy), '20071001','basic')
        self.assertEqual(self.edi._formatfield('071001',tfield1,testdummy), '071001','basic')
        self.assertEqual(self.edi._formatfield('99991001',tfield1,testdummy), '99991001','max year')
        self.assertEqual(self.edi._formatfield('00011001',tfield1,testdummy), '00011001','min year')
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'2007093112',tfield1,testdummy) #too long
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'20070931',tfield1,testdummy) #no valid date
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'-0070931',tfield1,testdummy) #no valid date
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'70931',tfield1,testdummy) #too short
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'0931',tfield1,testdummy) #too short
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'0931BC',tfield1,testdummy) #alfanum
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'OOOOBC',tfield1,testdummy) #alfanum
        
    def test_out_formatfield_var_T(self):
        tfield1 = ['TEST1', 'M', 10,   'T', True,   0,      0,'T']
        #                    length            decimals minlength 
        self.assertEqual(self.edi._formatfield('2359',tfield1,testdummy), '2359','basic')
        self.assertEqual(self.edi._formatfield('0000',tfield1,testdummy), '0000','basic')
        self.assertEqual(self.edi._formatfield('000000',tfield1,testdummy), '000000','basic')
        self.assertEqual(self.edi._formatfield('230000',tfield1,testdummy), '230000','basic')
        self.assertEqual(self.edi._formatfield('235959',tfield1,testdummy), '235959','basic')
        self.assertEqual(self.edi._formatfield('123456',tfield1,testdummy), '123456','basic')
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'12345678',tfield1,testdummy) #no valid time
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'240001',tfield1,testdummy) #no valid time
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'126101',tfield1,testdummy) #no valid time
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'120062',tfield1,testdummy) #no valid time - python allows 61 secnds?
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'240000',tfield1,testdummy) #no valid time
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'250001',tfield1,testdummy) #no valid time
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'-12000',tfield1,testdummy) #no valid time
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'120',tfield1,testdummy) #no valid time
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'0931233',tfield1,testdummy) #too short
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'11PM',tfield1,testdummy) #alfanum
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'TIME',tfield1,testdummy) #alfanum
        tfield2 = ['TEST1', 'M', 4,   'T', True,   0,      4,'T']
        #                    length            decimals minlength 
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'230001',tfield2,testdummy) #time too long
        tfield3 = ['TEST1', 'M', 6,   'T', True,   0,      6,'T']
        #                    length            decimals minlength 
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'2300',tfield3,testdummy) #time too short
        
    def test_out_formatfield_var_A(self):
        tfield1 = ['TEST1', 'M', 5,   'A', True,   0,      0,'A']
        #                    length            decimals minlength 
        self.assertEqual(self.edi._formatfield('abcde',tfield1,testdummy), 'abcde','basic')
        self.assertEqual(self.edi._formatfield('',tfield1,testdummy), '','basic')
        self.assertEqual(self.edi._formatfield('a	b',tfield1,testdummy), 'a	b','basic')
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'abcdef',tfield1,testdummy) #no valid date
        tfield1 = ['TEST1', 'M', 5,   'A', True,   0,      2,'A']
        #                    length            decimals minlength 
        self.assertEqual(self.edi._formatfield('abcde',tfield1,testdummy), 'abcde','basic')
        self.assertEqual(self.edi._formatfield('a	b',tfield1,testdummy), 'a	b','basic')
        self.assertEqual(self.edi._formatfield('aa',tfield1,testdummy), 'aa','basic')
        self.assertEqual(self.edi._formatfield('aaa',tfield1,testdummy), 'aaa','basic')
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'a',tfield1,testdummy) #field too small
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,' ',tfield1,testdummy) #field too small
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'',tfield1,testdummy) #field too small
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'abcdef',tfield1,testdummy) #no valid date
        
class TestFormatFieldFixedOutmessage(unittest.TestCase):
    def setUp(self):
        self.edi = outmessage.outmessage_init(editype='fixed',messagetype='ordersfixed')
    def test_out_formatfield_fixedR(self):
        self.edi.ta_info['lengthnumericbare']=False
        self.edi.ta_info['decimaal']='.'
        tfield1 = ['TEST1','M',3,'R',True,0,       3,       'R']
        #                    length    decimals minlength  format
        self.assertEqual(self.edi._formatfield('',tfield1,testdummy), '000','empty string')
        self.assertEqual(self.edi._formatfield('1',tfield1,testdummy), '001', 'basic')
        self.assertEqual(self.edi._formatfield(' 1',tfield1,testdummy), '001', 'basic')
        self.assertEqual(self.edi._formatfield('1 ',tfield1,testdummy), '001', 'basic')
        self.assertEqual(self.edi._formatfield('0',tfield1,testdummy), '000','zero stays zero')
        self.assertEqual(self.edi._formatfield('-0',tfield1,testdummy), '-00','neg.zero stays neg.zero')
        tfield3 = ['TEST1','M',5,'R',True,2,       3,       'R']
        self.assertEqual(self.edi._formatfield('-0.00',tfield3,testdummy), '-0.00','')
        self.assertEqual(self.edi._formatfield('0.10',tfield3,testdummy), '0.10','keep zeroes after last dec.digit')
        
        self.assertEqual(self.edi._formatfield('123',tfield1,testdummy), '123','numeric field at max')
        self.assertEqual(self.edi._formatfield('001',tfield1,testdummy), '001','leading zeroes are removed')
        self.assertEqual(self.edi._formatfield('0001',tfield1,testdummy), '001','strips leading zeroes if possobel')
        self.assertEqual(self.edi._formatfield('+123',tfield1,testdummy), '123','strips leading zeroes if possobel')
        self.edi.ta_info['decimaal']=','
        self.assertEqual(self.edi._formatfield('1.2',tfield1,testdummy), '1,2','other dec.sig, replace')
        self.edi.ta_info['decimaal']='.'
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'.12',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'-.12',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1234',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'-1.234',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1<3',tfield1,testdummy)    #wrong char
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1-3',tfield1,testdummy)    #'-' in middel of number
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'123-',tfield1,testdummy)    #'-' at end of number
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1,3',tfield1,testdummy)    #',', where ',' is not traid sep.
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1+3',tfield1,testdummy)    #'+' in middle of number (no exp)
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1E3',tfield1,testdummy)    #'+' in middle of number (no exp)
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'13+',tfield1,testdummy)    #'+' at end
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1+3',tfield1,testdummy)    #'+' in middle of number
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'0.100',tfield1,testdummy)   #field too big
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'.',tfield1,testdummy)   #no num
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'-',tfield1,testdummy)   #no num
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'.001',tfield1,testdummy)   #bots adds 0 before dec, thus too big
        # #test filling up to min length
        tfield2 = ['TEST1', 'M', 8,   'R', True,   0,      8,'R']
        self.assertEqual(self.edi._formatfield('12345',tfield2,testdummy),   '00012345','just large enough')
        self.assertEqual(self.edi._formatfield('0.1000',tfield2,testdummy),  '000.1000','keep zeroes after last dec.digit')
        self.assertEqual(self.edi._formatfield('00001',tfield2,testdummy),   '00000001','keep leading zeroes')
        self.assertEqual(self.edi._formatfield('123',tfield2,testdummy),     '00000123','add leading zeroes')
        self.assertEqual(self.edi._formatfield('.1',tfield2,testdummy),      '000000.1','add leading zeroes')
        self.assertEqual(self.edi._formatfield('-1.23',tfield2,testdummy),   '-0001.23','numeric field at max with minus and decimal sign')
        #test exp
        self.assertEqual(self.edi._formatfield('12E+3',tfield2,testdummy),   '00012000','Exponent notation is possible')
        self.assertEqual(self.edi._formatfield('12E3',tfield2,testdummy),    '00012000','Exponent notation is possible->to std notation')
        self.assertEqual(self.edi._formatfield('12e+3',tfield2,testdummy),   '00012000','Exponent notation is possible; e->E')
        self.assertEqual(self.edi._formatfield('12e3',tfield2,testdummy),    '00012000','Exponent notation is possible; e->E')
        self.assertEqual(self.edi._formatfield('4567E+3',tfield2,testdummy), '04567000','do not count + and E')
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'12345678E+3',tfield2,testdummy)   #too big with exp
        #~ #print '>>',self.edi._formatfield('12E-3',tfield2,testdummy)
        #~ self.assertEqual(self.edi._formatfield('12E-3',tfield2,testdummy),       '0000.012','Exponent notation is possible')
        #~ self.assertEqual(self.edi._formatfield('12e-3',tfield2,testdummy),       '0000.012','Exponent notation is possible; e->E')
        #~ self.assertEqual(self.edi._formatfield('1234567E-3',tfield2,testdummy),  '1234.567','do not count + and E')
        #~ self.assertEqual(self.edi._formatfield('1234567E-6',tfield2,testdummy),  '1.234567','do not count + and E')
        #~ self.assertEqual(self.edi._formatfield('123456E-6',tfield2,testdummy),   '0.123456','do not count + and E')
        #~ self.assertEqual(self.edi._formatfield('-12345E-5',tfield2,testdummy), '-0.12345','do not count + and E')
        #~ self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'12345678E-8',tfield2,testdummy)   #gets 0.12345678, is too big
        #~ self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'12345678E+3',tfield2,testdummy)   #too big with exp
        tfield4 = ['TEST1', 'M', 30,   'R', True,   3,      30,'R']
        self.assertEqual(self.edi._formatfield('12345678901234560',tfield4,testdummy), '000000000000012345678901234560','lot of digits')
        tfield5 = ['TEST1','M',4,'R',True,2,       4,       'R']
        self.assertEqual(self.edi._formatfield('0.00',tfield5,testdummy), '0.00','lot of digits')
        tfield6 = ['TEST1','M',5,'R',True,2,       5,       'R']
        self.assertEqual(self.edi._formatfield('12.45',tfield6,testdummy), '12.45','lot of digits')

    def test_out_formatfield_fixedRL(self):
        self.edi.ta_info['lengthnumericbare']=False
        self.edi.ta_info['decimaal']='.'
        tfield1 = ['TEST1','M',3,'RL',True,0,       3,       'R']
        #                    length    decimals minlength  format
        self.assertEqual(self.edi._formatfield('',tfield1,testdummy), '0  ','empty string')
        self.assertEqual(self.edi._formatfield('1',tfield1,testdummy), '1  ', 'basic')
        self.assertEqual(self.edi._formatfield(' 1',tfield1,testdummy), '1  ', 'basic')
        self.assertEqual(self.edi._formatfield('1 ',tfield1,testdummy), '1  ', 'basic')
        self.assertEqual(self.edi._formatfield('0',tfield1,testdummy), '0  ','zero stays zero')
        self.assertEqual(self.edi._formatfield('-0',tfield1,testdummy), '-0 ','neg.zero stays neg.zero')
        tfield3 = ['TEST1','M',5,'RL',True,2,       3,       'R']
        self.assertEqual(self.edi._formatfield('-0.00',tfield3,testdummy), '-0.00','')
        self.assertEqual(self.edi._formatfield('0.10',tfield3,testdummy), '0.10','keep zeroes after last dec.digit')
        
        self.assertEqual(self.edi._formatfield('123',tfield1,testdummy), '123','numeric field at max')
        self.assertEqual(self.edi._formatfield('001',tfield1,testdummy), '1  ','leading zeroes are removed')
        self.assertEqual(self.edi._formatfield('0001',tfield1,testdummy), '1  ','strips leading zeroes if possobel')
        self.assertEqual(self.edi._formatfield('+123',tfield1,testdummy), '123','strips leading zeroes if possobel')
        self.edi.ta_info['decimaal']=','
        self.assertEqual(self.edi._formatfield('1.2',tfield1,testdummy), '1,2','other dec.sig, replace')
        self.edi.ta_info['decimaal']='.'
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'.12',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'-.12',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1234',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'-1.234',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1<3',tfield1,testdummy)    #wrong char
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1-3',tfield1,testdummy)    #'-' in middel of number
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'123-',tfield1,testdummy)    #'-' at end of number
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1,3',tfield1,testdummy)    #',', where ',' is not traid sep.
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1+3',tfield1,testdummy)    #'+' in middle of number (no exp)
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1E3',tfield1,testdummy)    #'+' in middle of number (no exp)
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'13+',tfield1,testdummy)    #'+' at end
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1+3',tfield1,testdummy)    #'+' in middle of number
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'0.100',tfield1,testdummy)   #field too big
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'.',tfield1,testdummy)   #no num
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'-',tfield1,testdummy)   #no num
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'.001',tfield1,testdummy)   #bots adds 0 before dec, thus too big
        # #test filling up to min length
        tfield2 = ['TEST1', 'M', 8,   'RL', True,   0,      8,'R']
        self.assertEqual(self.edi._formatfield('12345',tfield2,testdummy),   '12345   ','just large enough')
        self.assertEqual(self.edi._formatfield('0.1000',tfield2,testdummy),  '0.1000  ','keep zeroes after last dec.digit')
        self.assertEqual(self.edi._formatfield('00001',tfield2,testdummy),   '1       ','keep leading zeroes')
        self.assertEqual(self.edi._formatfield('123',tfield2,testdummy),     '123     ','add leading zeroes')
        self.assertEqual(self.edi._formatfield('.1',tfield2,testdummy),      '0.1     ','add leading zeroes')
        self.assertEqual(self.edi._formatfield('-1.23',tfield2,testdummy),   '-1.23   ','numeric field at max with minus and decimal sign')
        #test exp
        self.assertEqual(self.edi._formatfield('12E+3',tfield2,testdummy),   '12000   ','Exponent notation is possible')
        self.assertEqual(self.edi._formatfield('12E3',tfield2,testdummy),    '12000   ','Exponent notation is possible->to std notation')
        self.assertEqual(self.edi._formatfield('12e+3',tfield2,testdummy),   '12000   ','Exponent notation is possible; e->E')
        self.assertEqual(self.edi._formatfield('12e3',tfield2,testdummy),    '12000   ','Exponent notation is possible; e->E')
        self.assertEqual(self.edi._formatfield('4567E+3',tfield2,testdummy), '4567000 ','do not count + and E')
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'12345678E+3',tfield2,testdummy)   #too big with exp
        #~ #print '>>',self.edi._formatfield('12E-3',tfield2,testdummy)
        #~ self.assertEqual(self.edi._formatfield('12E-3',tfield2,testdummy),       '0000.012','Exponent notation is possible')
        #~ self.assertEqual(self.edi._formatfield('12e-3',tfield2,testdummy),       '0000.012','Exponent notation is possible; e->E')
        #~ self.assertEqual(self.edi._formatfield('1234567E-3',tfield2,testdummy),  '1234.567','do not count + and E')
        #~ self.assertEqual(self.edi._formatfield('1234567E-6',tfield2,testdummy),  '1.234567','do not count + and E')
        #~ self.assertEqual(self.edi._formatfield('123456E-6',tfield2,testdummy),   '0.123456','do not count + and E')
        #~ self.assertEqual(self.edi._formatfield('-12345E-5',tfield2,testdummy), '-0.12345','do not count + and E')
        #~ self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'12345678E-8',tfield2,testdummy)   #gets 0.12345678, is too big
        #~ self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'12345678E+3',tfield2,testdummy)   #too big with exp
        tfield4 = ['TEST1', 'M', 30,   'RL', True,   3,      30,'R']
        self.assertEqual(self.edi._formatfield('12345678901234560',tfield4,testdummy), '12345678901234560             ','lot of digits')
        tfield5 = ['TEST1','M',4,'RL',True,2,       4,       'N']
        self.assertEqual(self.edi._formatfield('0.00',tfield5,testdummy), '0.00','lot of digits')
        tfield6 = ['TEST1','M',5,'RL',True,2,       5,       'N']
        self.assertEqual(self.edi._formatfield('12.45',tfield6,testdummy), '12.45','lot of digits')

    def test_out_formatfield_fixedRR(self):
        self.edi.ta_info['lengthnumericbare']=False
        self.edi.ta_info['decimaal']='.'
        tfield1 = ['TEST1','M',3,'RR',True,0,       3,       'R']
        #                    length    decimals minlength  format
        self.assertEqual(self.edi._formatfield('',tfield1,testdummy),   '  0','empty string')
        self.assertEqual(self.edi._formatfield('1',tfield1,testdummy),  '  1', 'basic')
        self.assertEqual(self.edi._formatfield(' 1',tfield1,testdummy), '  1', 'basic')
        self.assertEqual(self.edi._formatfield('1 ',tfield1,testdummy), '  1', 'basic')
        self.assertEqual(self.edi._formatfield('0',tfield1,testdummy),  '  0','zero stays zero')
        self.assertEqual(self.edi._formatfield('-0',tfield1,testdummy), ' -0','neg.zero stays neg.zero')
        tfield3 = ['TEST1','M',5,'RR',True,2,       3,       'R']
        self.assertEqual(self.edi._formatfield('-0.00',tfield3,testdummy), '-0.00','')
        self.assertEqual(self.edi._formatfield('0.10',tfield3,testdummy),  '0.10','keep zeroes after last dec.digit')
        
        self.assertEqual(self.edi._formatfield('123',tfield1,testdummy),  '123','numeric field at max')
        self.assertEqual(self.edi._formatfield('001',tfield1,testdummy),  '  1','leading zeroes are removed')
        self.assertEqual(self.edi._formatfield('0001',tfield1,testdummy), '  1','strips leading zeroes if possobel')
        self.assertEqual(self.edi._formatfield('+123',tfield1,testdummy), '123','strips leading zeroes if possobel')
        self.edi.ta_info['decimaal']=','
        self.assertEqual(self.edi._formatfield('1.2',tfield1,testdummy),  '1,2','other dec.sig, replace')
        self.edi.ta_info['decimaal']='.'
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,  '.12',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,  '-.12',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,  '1234',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,  '-1.234',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,  '1<3',tfield1,testdummy)    #wrong char
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,  '1-3',tfield1,testdummy)    #'-' in middel of number
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,  '123-',tfield1,testdummy)    #'-' at end of number
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,  '1,3',tfield1,testdummy)    #',', where ',' is not traid sep.
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,  '1+3',tfield1,testdummy)    #'+' in middle of number (no exp)
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,  '1E3',tfield1,testdummy)    #'+' in middle of number (no exp)
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,  '13+',tfield1,testdummy)    #'+' at end
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,  '1+3',tfield1,testdummy)    #'+' in middle of number
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,  '0.100',tfield1,testdummy)   #field too big
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,  '.',tfield1,testdummy)   #no num
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,  '-',tfield1,testdummy)   #no num
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,  '.001',tfield1,testdummy)   #bots adds 0 before dec, thus too big
        # #test filling up to min length
        tfield2 = ['TEST1', 'M', 8,   'RR', True,   0,      8,'R']
        self.assertEqual(self.edi._formatfield('12345',tfield2,testdummy),   '   12345','just large enough')
        self.assertEqual(self.edi._formatfield('0.1000',tfield2,testdummy),  '  0.1000','keep zeroes after last dec.digit')
        self.assertEqual(self.edi._formatfield('00001',tfield2,testdummy),   '       1','keep leading zeroes')
        self.assertEqual(self.edi._formatfield('123',tfield2,testdummy),     '     123','add leading zeroes')
        self.assertEqual(self.edi._formatfield('.1',tfield2,testdummy),      '     0.1','add leading zeroes')
        self.assertEqual(self.edi._formatfield('-1.23',tfield2,testdummy),   '   -1.23','numeric field at max with minus and decimal sign')
        #test exp
        self.assertEqual(self.edi._formatfield('12E+3',tfield2,testdummy),   '   12000','Exponent notation is possible')
        self.assertEqual(self.edi._formatfield('12E3',tfield2,testdummy),    '   12000','Exponent notation is possible->to std notation')
        self.assertEqual(self.edi._formatfield('12e+3',tfield2,testdummy),   '   12000','Exponent notation is possible; e->E')
        self.assertEqual(self.edi._formatfield('12e3',tfield2,testdummy),    '   12000','Exponent notation is possible; e->E')
        self.assertEqual(self.edi._formatfield('4567E+3',tfield2,testdummy), ' 4567000','do not count + and E')
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'12345678E+3',tfield2,testdummy)   #too big with exp
        #~ #print '>>',self.edi._formatfield('12E-3',tfield2,testdummy)
        #~ self.assertEqual(self.edi._formatfield('12E-3',tfield2,testdummy),       '0000.012','Exponent notation is possible')
        #~ self.assertEqual(self.edi._formatfield('12e-3',tfield2,testdummy),       '0000.012','Exponent notation is possible; e->E')
        #~ self.assertEqual(self.edi._formatfield('1234567E-3',tfield2,testdummy),  '1234.567','do not count + and E')
        #~ self.assertEqual(self.edi._formatfield('1234567E-6',tfield2,testdummy),  '1.234567','do not count + and E')
        #~ self.assertEqual(self.edi._formatfield('123456E-6',tfield2,testdummy),   '0.123456','do not count + and E')
        #~ self.assertEqual(self.edi._formatfield('-12345E-5',tfield2,testdummy), '-0.12345','do not count + and E')
        #~ self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'12345678E-8',tfield2,testdummy)   #gets 0.12345678, is too big
        #~ self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'12345678E+3',tfield2,testdummy)   #too big with exp
        tfield4 = ['TEST1', 'M', 30,   'RR', True,   3,      30,'R']
        self.assertEqual(self.edi._formatfield('12345678901234560',tfield4,testdummy), '             12345678901234560','lot of digits')
        tfield5 = ['TEST1','M',4,'RR',True,2,       4,       'N']
        self.assertEqual(self.edi._formatfield('0.00',tfield5,testdummy), '0.00','lot of digits')
        tfield6 = ['TEST1','M',5,'RR',True,2,       5,       'N']
        self.assertEqual(self.edi._formatfield('12.45',tfield6,testdummy), '12.45','lot of digits')

    def test_out_formatfield_fixedN(self):
        self.edi.ta_info['decimaal']='.'
        self.edi.ta_info['lengthnumericbare']=False
        tfield1 = ['TEST1','M',5,'N',True,2,       5,       'N']
        #                    length    decimals minlength  format
        self.assertEqual(self.edi._formatfield('',tfield1,testdummy), '00.00','empty string')
        self.assertEqual(self.edi._formatfield('1',tfield1,testdummy), '01.00', 'basic')
        self.assertEqual(self.edi._formatfield(' 1',tfield1,testdummy), '01.00', 'basic')
        self.assertEqual(self.edi._formatfield('1 ',tfield1,testdummy), '01.00', 'basic')
        self.assertEqual(self.edi._formatfield('0',tfield1,testdummy), '00.00','zero stays zero')
        self.assertEqual(self.edi._formatfield('-0',tfield1,testdummy), '-0.00','neg.zero stays neg.zero')
        self.assertEqual(self.edi._formatfield('-0.00',tfield1,testdummy), '-0.00','')
        self.assertEqual(self.edi._formatfield('-0.001',tfield1,testdummy), '-0.00','')
        self.assertEqual(self.edi._formatfield('-.12',tfield1,testdummy), '-0.12','no zero before dec,sign is OK')
        self.assertEqual(self.edi._formatfield('001',tfield1,testdummy), '01.00','leading zeroes are removed')
        self.assertEqual(self.edi._formatfield('0.10',tfield1,testdummy), '00.10','keep zeroes after last dec.digit')
        self.assertEqual(self.edi._formatfield('12.1049',tfield1,testdummy), '12.10','keep zeroes after last dec.digit')
        self.assertEqual(self.edi._formatfield('-1.23',tfield1,testdummy), '-1.23','numeric field at max with minus and decimal sign')
        self.assertEqual(self.edi._formatfield('0001',tfield1,testdummy), '01.00','strips leading zeroes if possobel')
        self.assertEqual(self.edi._formatfield('+13',tfield1,testdummy), '13.00','strips leading zeroes if possobel')
        self.edi.ta_info['decimaal']=','
        self.assertEqual(self.edi._formatfield('1.23',tfield1,testdummy), '01,23','other dec.sig, replace')
        self.edi.ta_info['decimaal']='.'
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'123.1049',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'123',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1234',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'-1234.56',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1<3',tfield1,testdummy)    #wrong char
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1-3',tfield1,testdummy)    #'-' in middel of number
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'123-',tfield1,testdummy)    #'-' at end of number
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1,3',tfield1,testdummy)    #',', where ',' is not traid sep.
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1+3',tfield1,testdummy)    #'+' in middle of number (no exp)
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1E3',tfield1,testdummy)    #'+' in middle of number (no exp)
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'13+',tfield1,testdummy)    #'+' at end
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1234.100',tfield1,testdummy)   #field too big
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'.',tfield1,testdummy)   #no num
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'-',tfield1,testdummy)   #no num
        # #test filling up to min length
        tfield2 = ['TEST1', 'M', 8,   'N', True,   2,      8,'N']
        self.assertEqual(self.edi._formatfield('123.45',tfield2,testdummy),   '00123.45','just large enough')
        self.assertEqual(self.edi._formatfield('123.4549',tfield2,testdummy), '00123.45','just large enough')
        self.assertEqual(self.edi._formatfield('123.455',tfield2,testdummy),  '00123.46','just large enough')
        self.assertEqual(self.edi._formatfield('0.1000',tfield2,testdummy),   '00000.10','keep zeroes after last dec.digit')
        self.assertEqual(self.edi._formatfield('00001',tfield2,testdummy),    '00001.00','keep leading zeroes')
        self.assertEqual(self.edi._formatfield('12',tfield2,testdummy),       '00012.00','add leading zeroes')
        self.assertEqual(self.edi._formatfield('.1',tfield2,testdummy),       '00000.10','add leading zeroes')
        #test exp; bots tries to convert to normal
        self.assertEqual(self.edi._formatfield('78E+3',tfield2,testdummy),    '78000.00','add leading zeroes')
        self.assertEqual(self.edi._formatfield('-8E+3',tfield2,testdummy),    '-8000.00','add leading zeroes')
        self.assertEqual(self.edi._formatfield('-178e-3',tfield2,testdummy),  '-0000.18','add leading zeroes')
        self.assertEqual(self.edi._formatfield('-178e-5',tfield2,testdummy),  '-0000.00','add leading zeroes')
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'178E+4',tfield2,testdummy)   #too big with exp
        tfield4 = ['TEST1', 'M', 30,   'N', True,   3,      30,'N']
        self.assertEqual(self.edi._formatfield('1234567890123456',tfield4,testdummy), '00000000001234567890123456.000','lot of digits')
        #test N format, zero decimals
        tfield7 = ['TEST1', 'M',  5,   'N', True,   0,       5,  'N']
        #                    length    decimals minlength  format
        self.assertEqual(self.edi._formatfield('12345',tfield7,testdummy),  '12345','')
        self.assertEqual(self.edi._formatfield('1.234',tfield7,testdummy),  '00001','')
        self.assertEqual(self.edi._formatfield('123.4',tfield7,testdummy),  '00123','')
        self.assertEqual(self.edi._formatfield('0.0',tfield7,testdummy),    '00000','')

    def test_out_formatfield_fixedNL(self):
        self.edi.ta_info['decimaal']='.'
        self.edi.ta_info['lengthnumericbare']=False
        tfield1 = ['TEST1','M',5,'NL',True,2,       5,       'N']
        #                    length    decimals minlength  format
        self.assertEqual(self.edi._formatfield('',tfield1,testdummy), '0.00 ','empty string')
        self.assertEqual(self.edi._formatfield('1',tfield1,testdummy), '1.00 ', 'basic')
        self.assertEqual(self.edi._formatfield(' 1',tfield1,testdummy), '1.00 ', 'basic')
        self.assertEqual(self.edi._formatfield('1 ',tfield1,testdummy), '1.00 ', 'basic')
        self.assertEqual(self.edi._formatfield('0',tfield1,testdummy), '0.00 ','zero stays zero')
        self.assertEqual(self.edi._formatfield('-0',tfield1,testdummy), '-0.00','neg.zero stays neg.zero')
        self.assertEqual(self.edi._formatfield('-0.00',tfield1,testdummy), '-0.00','')
        self.assertEqual(self.edi._formatfield('-0.001',tfield1,testdummy), '-0.00','')
        self.assertEqual(self.edi._formatfield('-.12',tfield1,testdummy), '-0.12','no zero before dec,sign is OK')
        self.assertEqual(self.edi._formatfield('001',tfield1,testdummy), '1.00 ','leading zeroes are removed')
        self.assertEqual(self.edi._formatfield('0.10',tfield1,testdummy), '0.10 ','keep zeroes after last dec.digit')
        self.assertEqual(self.edi._formatfield('12.1049',tfield1,testdummy), '12.10','keep zeroes after last dec.digit')
        self.assertEqual(self.edi._formatfield('-1.23',tfield1,testdummy), '-1.23','numeric field at max with minus and decimal sign')
        self.assertEqual(self.edi._formatfield('0001',tfield1,testdummy), '1.00 ','strips leading zeroes if possobel')
        self.assertEqual(self.edi._formatfield('+13',tfield1,testdummy), '13.00','strips leading zeroes if possobel')
        self.edi.ta_info['decimaal']=','
        self.assertEqual(self.edi._formatfield('1.23',tfield1,testdummy), '1,23 ','other dec.sig, replace')
        self.edi.ta_info['decimaal']='.'
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'123.1049',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'123',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1234',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'-1234.56',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1<3',tfield1,testdummy)    #wrong char
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1-3',tfield1,testdummy)    #'-' in middel of number
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'123-',tfield1,testdummy)    #'-' at end of number
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1,3',tfield1,testdummy)    #',', where ',' is not traid sep.
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1+3',tfield1,testdummy)    #'+' in middle of number (no exp)
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1E3',tfield1,testdummy)    #'+' in middle of number (no exp)
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'13+',tfield1,testdummy)    #'+' at end
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1234.100',tfield1,testdummy)   #field too big
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'.',tfield1,testdummy)   #no num
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'-',tfield1,testdummy)   #no num
        # #test filling up to min length
        tfield2 = ['TEST1', 'M', 8,   'NL', True,   2,      8,'N']
        self.assertEqual(self.edi._formatfield('123.45',tfield2,testdummy),   '123.45  ','just large enough')
        self.assertEqual(self.edi._formatfield('123.4549',tfield2,testdummy), '123.45  ','just large enough')
        self.assertEqual(self.edi._formatfield('123.455',tfield2,testdummy),  '123.46  ','just large enough')
        self.assertEqual(self.edi._formatfield('0.1000',tfield2,testdummy),   '0.10    ','keep zeroes after last dec.digit')
        self.assertEqual(self.edi._formatfield('00001',tfield2,testdummy),    '1.00    ','keep leading zeroes')
        self.assertEqual(self.edi._formatfield('12',tfield2,testdummy),       '12.00   ','add leading zeroes')
        self.assertEqual(self.edi._formatfield('.1',tfield2,testdummy),       '0.10    ','add leading zeroes')
        #test exp; bots tries to convert to normal
        self.assertEqual(self.edi._formatfield('78E+3',tfield2,testdummy),    '78000.00','add leading zeroes')
        self.assertEqual(self.edi._formatfield('-8E+3',tfield2,testdummy),    '-8000.00','add leading zeroes')
        self.assertEqual(self.edi._formatfield('-178e-3',tfield2,testdummy),  '-0.18   ','add leading zeroes')
        self.assertEqual(self.edi._formatfield('-178e-5',tfield2,testdummy),  '-0.00   ','add leading zeroes')
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'178E+4',tfield2,testdummy)   #too big with exp
        tfield4 = ['TEST1', 'M', 30,   'NL', True,   3,      30,'N']
        self.assertEqual(self.edi._formatfield('1234567890123456',tfield4,testdummy), '1234567890123456.000          ','lot of digits')
        #test N format, zero decimals
        tfield7 = ['TEST1', 'M',  5,   'NL', True,   0,       5,  'N']
        #                    length    decimals minlength  format
        self.assertEqual(self.edi._formatfield('12345',tfield7,testdummy),  '12345','')
        self.assertEqual(self.edi._formatfield('1.234',tfield7,testdummy),  '1    ','')
        self.assertEqual(self.edi._formatfield('123.4',tfield7,testdummy),  '123  ','')
        self.assertEqual(self.edi._formatfield('0.0',tfield7,testdummy),    '0    ','')

    def test_out_formatfield_fixedNR(self):
        self.edi.ta_info['decimaal']='.'
        self.edi.ta_info['lengthnumericbare']=False
        tfield1 = ['TEST1','M',5,'NR',True,2,       5,       'N']
        #                    length    decimals minlength  format
        self.assertEqual(self.edi._formatfield('',tfield1,testdummy), ' 0.00','empty string')
        self.assertEqual(self.edi._formatfield('1',tfield1,testdummy), ' 1.00', 'basic')
        self.assertEqual(self.edi._formatfield(' 1',tfield1,testdummy), ' 1.00', 'basic')
        self.assertEqual(self.edi._formatfield('1 ',tfield1,testdummy), ' 1.00', 'basic')
        self.assertEqual(self.edi._formatfield('0',tfield1,testdummy), ' 0.00','zero stays zero')
        self.assertEqual(self.edi._formatfield('-0',tfield1,testdummy), '-0.00','neg.zero stays neg.zero')
        self.assertEqual(self.edi._formatfield('-0.00',tfield1,testdummy), '-0.00','')
        self.assertEqual(self.edi._formatfield('-0.001',tfield1,testdummy), '-0.00','')
        self.assertEqual(self.edi._formatfield('-.12',tfield1,testdummy), '-0.12','no zero before dec,sign is OK')
        self.assertEqual(self.edi._formatfield('001',tfield1,testdummy), ' 1.00','leading zeroes are removed')
        self.assertEqual(self.edi._formatfield('0.10',tfield1,testdummy), ' 0.10','keep zeroes after last dec.digit')
        self.assertEqual(self.edi._formatfield('12.1049',tfield1,testdummy), '12.10','keep zeroes after last dec.digit')
        self.assertEqual(self.edi._formatfield('-1.23',tfield1,testdummy), '-1.23','numeric field at max with minus and decimal sign')
        self.assertEqual(self.edi._formatfield('0001',tfield1,testdummy), ' 1.00','strips leading zeroes if possobel')
        self.assertEqual(self.edi._formatfield('+13',tfield1,testdummy), '13.00','strips leading zeroes if possobel')
        self.edi.ta_info['decimaal']=','
        self.assertEqual(self.edi._formatfield('1.23',tfield1,testdummy), ' 1,23','other dec.sig, replace')
        self.edi.ta_info['decimaal']='.'
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'123.1049',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'123',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1234',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'-1234.56',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1<3',tfield1,testdummy)    #wrong char
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1-3',tfield1,testdummy)    #'-' in middel of number
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'123-',tfield1,testdummy)    #'-' at end of number
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1,3',tfield1,testdummy)    #',', where ',' is not traid sep.
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1+3',tfield1,testdummy)    #'+' in middle of number (no exp)
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1E3',tfield1,testdummy)    #'+' in middle of number (no exp)
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'13+',tfield1,testdummy)    #'+' at end
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1234.100',tfield1,testdummy)   #field too big
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'.',tfield1,testdummy)   #no num
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'-',tfield1,testdummy)   #no num
        # #test filling up to min length
        tfield2 = ['TEST1', 'M', 8,   'NR', True,   2,      8,'N']
        self.assertEqual(self.edi._formatfield('123.45',tfield2,testdummy),   '  123.45','just large enough')
        self.assertEqual(self.edi._formatfield('123.4549',tfield2,testdummy), '  123.45','just large enough')
        self.assertEqual(self.edi._formatfield('123.455',tfield2,testdummy),  '  123.46','just large enough')
        self.assertEqual(self.edi._formatfield('0.1000',tfield2,testdummy),   '    0.10','keep zeroes after last dec.digit')
        self.assertEqual(self.edi._formatfield('00001',tfield2,testdummy),    '    1.00','keep leading zeroes')
        self.assertEqual(self.edi._formatfield('12',tfield2,testdummy),       '   12.00','add leading zeroes')
        self.assertEqual(self.edi._formatfield('.1',tfield2,testdummy),       '    0.10','add leading zeroes')
        #test exp; bots tries to convert to normal
        self.assertEqual(self.edi._formatfield('78E+3',tfield2,testdummy),    '78000.00','add leading zeroes')
        self.assertEqual(self.edi._formatfield('-8E+3',tfield2,testdummy),    '-8000.00','add leading zeroes')
        self.assertEqual(self.edi._formatfield('-178e-3',tfield2,testdummy),  '   -0.18','add leading zeroes')
        self.assertEqual(self.edi._formatfield('-178e-5',tfield2,testdummy),  '   -0.00','add leading zeroes')
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'178E+4',tfield2,testdummy)   #too big with exp
        tfield4 = ['TEST1', 'M', 30,   'NR', True,   3,      30,'N']
        self.assertEqual(self.edi._formatfield('1234567890123456',tfield4,testdummy), '          1234567890123456.000','lot of digits')
        #test N format, zero decimals
        tfield7 = ['TEST1', 'M',  5,   'NR', True,   0,       5,  'N']
        #                    length    decimals minlength  format
        self.assertEqual(self.edi._formatfield('12345',tfield7,testdummy),  '12345','')
        self.assertEqual(self.edi._formatfield('1.234',tfield7,testdummy),  '    1','')
        self.assertEqual(self.edi._formatfield('123.4',tfield7,testdummy),  '  123','')
        self.assertEqual(self.edi._formatfield('0.0',tfield7,testdummy),    '    0','')

    def test_out_formatfield_fixedI(self):
        self.edi.ta_info['lengthnumericbare']=False
        self.edi.ta_info['decimaal']='.'
        tfield1 = ['TEST1','M',5,'I',True,2,       5,       'I']
        #                    length    decimals minlength  format
        self.assertEqual(self.edi._formatfield('',tfield1,testdummy), '00000','empty string is initialised as 00000')
        self.assertEqual(self.edi._formatfield('1',tfield1,testdummy), '00100', 'basic')
        self.assertEqual(self.edi._formatfield(' 1',tfield1,testdummy), '00100', 'basic')
        self.assertEqual(self.edi._formatfield('1 ',tfield1,testdummy), '00100', 'basic')
        self.assertEqual(self.edi._formatfield('0',tfield1,testdummy), '00000','zero stays zero')
        self.assertEqual(self.edi._formatfield('-0',tfield1,testdummy), '-0000','neg.zero stays neg.zero')
        self.assertEqual(self.edi._formatfield('-0.00',tfield1,testdummy), '-0000','')
        self.assertEqual(self.edi._formatfield('-0.001',tfield1,testdummy), '-0000','')
        self.assertEqual(self.edi._formatfield('-.12',tfield1,testdummy), '-0012','no zero before dec,sign is OK')  #TODO: puts ) in front
        self.assertEqual(self.edi._formatfield('123',tfield1,testdummy), '12300','numeric field at max')
        self.assertEqual(self.edi._formatfield('001',tfield1,testdummy), '00100','leading zeroes are removed')
        self.assertEqual(self.edi._formatfield('0.10',tfield1,testdummy), '00010','keep zeroes after last dec.digit')
        self.assertEqual(self.edi._formatfield('123.1049',tfield1,testdummy), '12310','keep zeroes after last dec.digit')
        self.assertEqual(self.edi._formatfield('-1.23',tfield1,testdummy), '-0123','numeric field at max with minus and decimal sign')
        self.assertEqual(self.edi._formatfield('0001',tfield1,testdummy), '00100','strips leading zeroes if possobel')
        self.assertEqual(self.edi._formatfield('+123',tfield1,testdummy), '12300','strips leading zeroes if possobel')
        self.edi.ta_info['decimaal']=','
        self.assertEqual(self.edi._formatfield('1.23',tfield1,testdummy), '00123','other dec.sig, replace')
        self.edi.ta_info['decimaal']='.'
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1234',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'-1234.56',tfield1,testdummy) #field too large
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1<3',tfield1,testdummy)    #wrong char
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1-3',tfield1,testdummy)    #'-' in middel of number
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'123-',tfield1,testdummy)    #'-' at end of number
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1,3',tfield1,testdummy)    #',', where ',' is not traid sep.
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1+3',tfield1,testdummy)    #'+' in middle of number (no exp)
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1E3',tfield1,testdummy)    #'+' in middle of number (no exp)
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'13+',tfield1,testdummy)    #'+' at end
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1234.100',tfield1,testdummy)   #field too big
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'.',tfield1,testdummy)   #no num
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'-',tfield1,testdummy)   #no num
        #~ #test filling up to min length
        tfield2 = ['TEST1', 'M', 8,   'I', True,   2,      8,'I']
        self.assertEqual(self.edi._formatfield('123.45',tfield2,testdummy), '00012345','just large enough')
        self.assertEqual(self.edi._formatfield('123.4549',tfield2,testdummy), '00012345','just large enough')
        self.assertEqual(self.edi._formatfield('123.455',tfield2,testdummy), '00012346','just large enough')
        self.assertEqual(self.edi._formatfield('0.1000',tfield2,testdummy), '00000010','keep zeroes after last dec.digit')
        self.assertEqual(self.edi._formatfield('00001',tfield2,testdummy), '00000100','keep leading zeroes')
        self.assertEqual(self.edi._formatfield('12',tfield2,testdummy), '00001200','add leading zeroes')
        self.assertEqual(self.edi._formatfield('.1',tfield2,testdummy), '00000010','add leading zeroes')
        #test exp; bots tries to convert to normal
        self.assertEqual(self.edi._formatfield('178E+3',tfield2,testdummy),  '17800000','add leading zeroes')
        self.assertEqual(self.edi._formatfield('-17E+3',tfield2,testdummy),  '-1700000','add leading zeroes')
        self.assertEqual(self.edi._formatfield('-178e-3',tfield2,testdummy), '-0000018','add leading zeroes')
        self.assertEqual(self.edi._formatfield('-178e-5',tfield2,testdummy), '-0000000','add leading zeroes')
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'178E+4',tfield2,testdummy)   #too big with exp
        tfield4 = ['TEST1', 'M', 80,   'I', True,   3,      0,'I']
        self.assertEqual(self.edi._formatfield('123456789012340',tfield4,testdummy), '123456789012340000','lot of digits')

    def test_out_formatfield_fixedD(self):
        tfield1 = ['TEST1', 'M', 8,   'D', True,   0,      8,'D']
        #                    length            decimals minlength 
        self.assertEqual(self.edi._formatfield('20071001',tfield1,testdummy), '20071001','basic')
        self.assertEqual(self.edi._formatfield('99991001',tfield1,testdummy), '99991001','max year')
        self.assertEqual(self.edi._formatfield('00011001',tfield1,testdummy), '00011001','min year')
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'2007093112',tfield1,testdummy) #too long
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'20070931',tfield1,testdummy) #no valid date
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'-0070931',tfield1,testdummy) #no valid date
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'70931',tfield1,testdummy) #too short
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'0931',tfield1,testdummy) #too short
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'0931BC',tfield1,testdummy) #alfanum
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'OOOOBC',tfield1,testdummy) #alfanum
        tfield2 = ['TEST1', 'M', 6,   'D', True,   0,      6,'D']
        #                    length            decimals minlength 
        self.assertEqual(self.edi._formatfield('071001',tfield2,testdummy), '071001','basic')
    def test_out_formatfield_fixedT(self):
        tfield1 = ['TEST1', 'M', 4,   'T', True,   0,      4,'T']
        #                    length            decimals minlength 
        self.assertEqual(self.edi._formatfield('2359',tfield1,testdummy), '2359','basic')
        self.assertEqual(self.edi._formatfield('0000',tfield1,testdummy), '0000','basic')
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'2401',tfield1,testdummy) #no valid date
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1261',tfield1,testdummy) #no valid date
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1262',tfield1,testdummy) #no valid date - python allows 61 secnds?
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'2400',tfield1,testdummy) #no valid date
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'2501',tfield1,testdummy) #no valid date
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'-1200',tfield1,testdummy) #no valid date
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'120',tfield1,testdummy) #too short
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'093123',tfield1,testdummy) #too long
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'11PM',tfield1,testdummy) #alfanum
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'TIME',tfield1,testdummy) #alfanum
        tfield2 = ['TEST1', 'M', 6,   'T', True,   0,      6,'T']
        #                    length            decimals minlength 
        self.assertEqual(self.edi._formatfield('000000',tfield2,testdummy), '000000','basic')
        self.assertEqual(self.edi._formatfield('230000',tfield2,testdummy), '230000','basic')
        self.assertEqual(self.edi._formatfield('235959',tfield2,testdummy), '235959','basic')
        self.assertEqual(self.edi._formatfield('123456',tfield2,testdummy), '123456','basic')
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'240001',tfield2,testdummy) #no valid date
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'126101',tfield2,testdummy) #no valid date
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'120062',tfield2,testdummy) #no valid date - python allows 61 secnds?
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'240000',tfield2,testdummy) #no valid date
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'250001',tfield2,testdummy) #no valid date
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'-12000',tfield2,testdummy) #no valid date
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'120',tfield2,testdummy) #too short
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'0931233',tfield2,testdummy) #too short
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'1100PM',tfield2,testdummy) #alfanum
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'11TIME',tfield2,testdummy) #alfanum
    def test_out_formatfield_fixedA(self):
        tfield1 = ['TEST1', 'M', 5,   'A', True,   0,      5,'A']
        #                    length            decimals minlength 
        self.assertEqual(self.edi._formatfield('abcde',tfield1,testdummy), 'abcde','basic')
        self.assertEqual(self.edi._formatfield('',tfield1,testdummy), '     ','basic')
        self.assertEqual(self.edi._formatfield('ab   ',tfield1,testdummy), 'ab   ','basic')
        self.assertEqual(self.edi._formatfield('a	b',tfield1,testdummy), 'a	b  ','basic')
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'abcdef',tfield1,testdummy) #no valid date
        tfield1 = ['TEST1', 'M', 5,   'A', True,   0,      5,'A']
        #                    length            decimals minlength 
        self.assertEqual(self.edi._formatfield('abcde',tfield1,testdummy), 'abcde','basic')
        self.assertEqual(self.edi._formatfield('ab   ',tfield1,testdummy), 'ab   ','basic')
        self.assertEqual(self.edi._formatfield('a	b',tfield1,testdummy), 'a	b  ','basic')
        self.assertEqual(self.edi._formatfield('a',tfield1,testdummy), 'a    ','basic')
        self.assertEqual(self.edi._formatfield('  ',tfield1,testdummy), '     ','basic')
        self.assertEqual(self.edi._formatfield('     ',tfield1,testdummy), '     ','basic')
        self.assertEqual(self.edi._formatfield(' ',tfield1,testdummy), '     ','basic')
        self.assertEqual(self.edi._formatfield('',tfield1,testdummy), '     ','basic')
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'abcdef',tfield1,testdummy) #no valid date
    def test_out_formatfield_fixedAR(self):
        tfield1 = ['TEST1', 'M', 5,   'AR', True,   0,      5,'A']
        #                    length            decimals minlength 
        self.assertEqual(self.edi._formatfield('abcde',tfield1,testdummy), 'abcde','basic')
        self.assertEqual(self.edi._formatfield('',tfield1,testdummy), '     ','basic')
        self.assertEqual(self.edi._formatfield('ab ',tfield1,testdummy), '  ab ','basic')
        self.assertEqual(self.edi._formatfield('a	b',tfield1,testdummy), '  a	b','basic')
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'abcdef',tfield1,testdummy) #no valid date
        tfield1 = ['TEST1', 'M', 5,   'AR', True,   0,      5,'A']
        #                    length            decimals minlength 
        self.assertEqual(self.edi._formatfield('abcde',tfield1,testdummy), 'abcde','basic')
        self.assertEqual(self.edi._formatfield('ab ',tfield1,testdummy), '  ab ','basic')
        self.assertEqual(self.edi._formatfield('a	b',tfield1,testdummy), '  a	b','basic')
        self.assertEqual(self.edi._formatfield('a',tfield1,testdummy), '    a','basic')
        self.assertEqual(self.edi._formatfield('  ',tfield1,testdummy), '     ','basic')
        self.assertEqual(self.edi._formatfield('     ',tfield1,testdummy), '     ','basic')
        self.assertEqual(self.edi._formatfield(' ',tfield1,testdummy), '     ','basic')
        self.assertEqual(self.edi._formatfield('',tfield1,testdummy), '     ','basic')
        self.assertRaises(botslib.OutMessageError,self.edi._formatfield,'abcdef',tfield1,testdummy) #no valid date

class TestFormatFieldInmessage(unittest.TestCase):
    #both var and fixed fields are tested. Is not much difference (white-box testing)
    def setUp(self):
        #need to have a inmessage-object for tests. Read is a edifile and a grammar.
        self.edi = inmessage.edifromfile(frompartner='',
                                        topartner='',
                                        filename='botssys/infile/unitformats/formats01.edi',
                                        messagetype='edifact',
                                        testindicator='0',
                                        editype='edifact',
                                        charset='UNOA',
                                        alt='')

    def testformatfieldR(self):
        self.edi.ta_info['lengthnumericbare']=True
        tfield1 = ['TEST1','M',3,'N',True,0,       0,       'R']
        #                    length    decimals minlength  format
        self.assertEqual(self.edi._formatfield('',tfield1,testdummy), '0', 'empty numeric string is accepted, is zero')
        self.assertEqual(self.edi._formatfield('1',tfield1,testdummy), '1', 'basic')
        self.assertEqual(self.edi._formatfield('0',tfield1,testdummy), '0','zero stays zero')
        self.assertEqual(self.edi._formatfield('-0',tfield1,testdummy), '-0','neg.zero stays neg.zero')
        self.assertEqual(self.edi._formatfield('-0.00',tfield1,testdummy), '-0.00','')
        self.assertEqual(self.edi._formatfield('-.12',tfield1,testdummy), '-0.12','no zero before dec,sign is OK')
        self.assertEqual(self.edi._formatfield('123',tfield1,testdummy), '123','numeric field at max')
        self.assertEqual(self.edi._formatfield('001',tfield1,testdummy), '1','leading zeroes are removed')
        self.assertEqual(self.edi._formatfield('0.10',tfield1,testdummy), '0.10','keep zeroes after last dec.digit')
        self.assertEqual(self.edi._formatfield('-1.23',tfield1,testdummy), '-1.23','numeric field at max with minus and decimal sign')
        self.edi.ta_info['decimaal']=','
        self.assertEqual(self.edi._formatfield('1,23-',tfield1,testdummy), '-1.23','other dec.sig, replace')
        self.edi.ta_info['decimaal']='.'
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'1234',tfield1,testdummy) #field too large
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'0001',tfield1,testdummy) #leading zeroes; field too large
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'-1.234',tfield1,testdummy) #field too large
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'1<3',tfield1,testdummy)    #wrong char
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'1-3',tfield1,testdummy)    #'-' in middel of number
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'1,3',tfield1,testdummy)    #',', where ',' is not traid sep.
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'1+3',tfield1,testdummy)    #'+' in middle of number
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'13+',tfield1,testdummy)    #'+' in middle of number
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'0.100',tfield1,testdummy)   #field too big
        #test field to short
        tfield2 = ['TEST1', 'M', 8,   'N', True,   0,      5,'R']
        self.assertEqual(self.edi._formatfield('12345',tfield2,testdummy), '12345','just large enough')
        self.assertEqual(self.edi._formatfield('0.1000',tfield2,testdummy), '0.1000','keep zeroes after last dec.digit')
        self.assertEqual(self.edi._formatfield('00001',tfield2,testdummy), '1','remove leading zeroes')
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'1235',tfield2,testdummy) #field too short
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'-12.34',tfield2,testdummy) #field too short
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'-',tfield2,testdummy) #field too short
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'.',tfield2,testdummy) #field too short
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'-.',tfield2,testdummy) #field too short
        #WARN: dubious tests. This is Bots filosophy: be flexible in input, be right in output.
        self.assertEqual(self.edi._formatfield('123-',tfield1,testdummy), '-123','numeric field minus at end')
        self.assertEqual(self.edi._formatfield('.001',tfield1,testdummy), '0.001','if no zero before dec.sign, length>max.length')
        self.assertEqual(self.edi._formatfield('+13',tfield1,testdummy), '13','plus is allowed')   #WARN: if plus used, plus is countd in length!! 
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'12E+3',tfield2,testdummy) #field too large
        tfield4 = ['TEST1', 'M', 8,   'N', True,   3,      0,'R']
        self.assertEqual(self.edi._formatfield('123.4561',tfield4,testdummy), '123.4561','no checking to many digits incoming') #should round here?
        tfield4 = ['TEST1', 'M', 80,   'N', True,   3,      0,'R']
        self.assertEqual(self.edi._formatfield('12345678901234560',tfield4,testdummy), '12345678901234560','lot of digits')
        self.edi.ta_info['lengthnumericbare']=False
        self.assertEqual(self.edi._formatfield('-1.45',tfield2,testdummy), '-1.45','just large enough')
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'-12345678',tfield2,testdummy) #field too large
    def testformatfieldN(self):
        self.edi.ta_info['lengthnumericbare']=True
        tfield1 = ['TEST1', 'M', 3,   'R', True,   2,      0,'N']
        #                    length            decimals minlength 
        
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'',tfield1,testdummy) #empty string
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'1',tfield1,testdummy) #empty string
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'0',tfield1,testdummy) #empty string
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'-0',tfield1,testdummy) #empty string
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'01.00',tfield1,testdummy) #empty string
        self.assertEqual(self.edi._formatfield('1.00',tfield1,testdummy), '1.00', 'basic')
        self.assertEqual(self.edi._formatfield('0.00',tfield1,testdummy), '0.00','zero stays zero')
        self.assertEqual(self.edi._formatfield('-0.00',tfield1,testdummy), '-0.00','neg.zero stays neg.zero')
        self.assertEqual(self.edi._formatfield('-.12',tfield1,testdummy), '-0.12','no zero before dec,sign is OK')
        self.assertEqual(self.edi._formatfield('1.23',tfield1,testdummy), '1.23','numeric field at max')
        self.assertEqual(self.edi._formatfield('0.10',tfield1,testdummy), '0.10','keep zeroes after last dec.digit')
        self.assertEqual(self.edi._formatfield('-1.23',tfield1,testdummy), '-1.23','numeric field at max with minus and decimal sign')
        self.edi.ta_info['decimaal']=','
        self.assertEqual(self.edi._formatfield('1,23-',tfield1,testdummy), '-1.23','other dec.sig, replace')
        self.edi.ta_info['decimaal']='.'
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'1234',tfield1,testdummy) #field too large
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'0001',tfield1,testdummy) #leading zeroes; field too large
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'-1.234',tfield1,testdummy) #field too large
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'1<3',tfield1,testdummy)    #wrong char
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'1-3',tfield1,testdummy)    #'-' in middel of number
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'1,3',tfield1,testdummy)    #',', where ',' is not traid sep.
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'1+3',tfield1,testdummy)    #'+' in middle of number
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'13+',tfield1,testdummy)    #'+' in middle of number
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'0.100',tfield1,testdummy)   #field too big
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'12E+3',tfield1,testdummy)   #no exp
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'.',tfield1,testdummy)   #no exp
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'-',tfield1,testdummy)   #no exp
        #test field to short
        tfield2 = ['TEST1', 'M', 8,   'R', True,   4,      5,'N']
        self.assertEqual(self.edi._formatfield('1.2345',tfield2,testdummy), '1.2345','just large enough')
        self.assertEqual(self.edi._formatfield('0.1000',tfield2,testdummy), '0.1000','keep zeroes after last dec.digit')
        self.assertEqual(self.edi._formatfield('001.1234',tfield2,testdummy), '1.1234','remove leading zeroes')
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'1235',tfield2,testdummy) #field too short
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'-12.34',tfield2,testdummy) #field too short
        #WARN: dubious tests. This is Bots filosophy: be flexible in input, be right in output.
        self.assertEqual(self.edi._formatfield('1234.1234-',tfield2,testdummy), '-1234.1234','numeric field - minus at end')
        self.assertEqual(self.edi._formatfield('.01',tfield1,testdummy), '0.01','if no zero before dec.sign, length>max.length')
        self.assertEqual(self.edi._formatfield('+13.1234',tfield2,testdummy), '13.1234','plus is allowed')   #WARN: if plus used, plus is counted in length!! 
        tfield3 = ['TEST1', 'M', 18,   'R', True,   0,      0,'N']
        tfield4 = ['TEST1', 'M', 8,   'R', True,   3,      0,'N']
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'123.4561',tfield4,testdummy) #to many digits

    def testformatfieldI(self):
        self.edi.ta_info['lengthnumericbare']=True
        tfield1 = ['TEST1', 'M', 5,   'I', True,   2,      0,'I']
        #                    length            decimals minlength 
        self.assertEqual(self.edi._formatfield('',tfield1,testdummy), '0.00', 'empty numeric is accepted, is zero')
        self.assertEqual(self.edi._formatfield('123',tfield1,testdummy), '1.23', 'basic')
        self.assertEqual(self.edi._formatfield('1',tfield1,testdummy), '0.01', 'basic')
        self.assertEqual(self.edi._formatfield('0',tfield1,testdummy), '0.00','zero stays zero')
        self.assertEqual(self.edi._formatfield('-0',tfield1,testdummy), '-0.00','neg.zero stays neg.zero')
        self.assertEqual(self.edi._formatfield('-000',tfield1,testdummy), '-0.00','')
        self.assertEqual(self.edi._formatfield('-12',tfield1,testdummy), '-0.12','no zero before dec,sign is OK')
        self.assertEqual(self.edi._formatfield('12345',tfield1,testdummy), '123.45','numeric field at max')
        self.assertEqual(self.edi._formatfield('00001',tfield1,testdummy), '0.01','leading zeroes are removed')
        self.assertEqual(self.edi._formatfield('010',tfield1,testdummy), '0.10','keep zeroes after last dec.digit')
        self.assertEqual(self.edi._formatfield('-99123',tfield1,testdummy), '-991.23','numeric field at max with minus and decimal sign')
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'123456',tfield1,testdummy) #field too large
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'000100',tfield1,testdummy)   #field too large
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'000001',tfield1,testdummy) #leading zeroes; field too large
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'12<3',tfield1,testdummy)    #wrong char
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'12-3',tfield1,testdummy)    #'-' in middel of number
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'12,3',tfield1,testdummy)    #','.
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'12+3',tfield1,testdummy)    #'+' in middle of number
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'123+',tfield1,testdummy)    #'+'
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'12E+3',tfield1,testdummy)    #'+'
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'-',tfield1,testdummy) #only -
        #~ #test field to short
        tfield2 = ['TEST1', 'M', 8,   'I', True,   2,      5,'I']
        self.assertEqual(self.edi._formatfield('12345',tfield2,testdummy), '123.45','just large enough')
        self.assertEqual(self.edi._formatfield('10000',tfield2,testdummy), '100.00','keep zeroes after last dec.digit')
        self.assertEqual(self.edi._formatfield('00100',tfield2,testdummy), '1.00','remove leading zeroes')
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'1235',tfield2,testdummy) #field too short
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'-1234',tfield2,testdummy) #field too short
        tfield3 = ['TEST1', 'M', 18,   'I', True,   0,      0,'I']
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'12E+3',tfield3,testdummy) #no exponent
        #~ #WARN: dubious tests. This is Bots filosophy: be flexible in input, be right in output.
        self.assertEqual(self.edi._formatfield('123-',tfield1,testdummy), '-1.23','numeric field minus at end')
        self.assertEqual(self.edi._formatfield('+13',tfield1,testdummy), '0.13','plus is allowed')   #WARN: if plus used, plus is countd in length!! 

    def testformatfieldD(self):
        tfield1 = ['TEST1', 'M', 20,   'D', True,   0,      0,'D']
        #                    length            decimals minlength 
        self.assertEqual(self.edi._formatfield('20071001',tfield1,testdummy), '20071001','basic')
        self.assertEqual(self.edi._formatfield('071001',tfield1,testdummy), '071001','basic')
        self.assertEqual(self.edi._formatfield('99991001',tfield1,testdummy), '99991001','max year')
        self.assertEqual(self.edi._formatfield('00011001',tfield1,testdummy), '00011001','min year')
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'2007093112',tfield1,testdummy) #too long
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'20070931',tfield1,testdummy) #no valid date
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'-0070931',tfield1,testdummy) #no valid date
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'70931',tfield1,testdummy) #too short
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'0931',tfield1,testdummy) #too short
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'0931BC',tfield1,testdummy) #alfanum
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'OOOOBC',tfield1,testdummy) #alfanum
    def testformatfieldT(self):
        tfield1 = ['TEST1', 'M', 10,   'T', True,   0,      0,'T']
        #                    length            decimals minlength 
        self.assertEqual(self.edi._formatfield('2359',tfield1,testdummy), '2359','basic')
        self.assertEqual(self.edi._formatfield('0000',tfield1,testdummy), '0000','basic')
        self.assertEqual(self.edi._formatfield('000000',tfield1,testdummy), '000000','basic')
        self.assertEqual(self.edi._formatfield('230000',tfield1,testdummy), '230000','basic')
        self.assertEqual(self.edi._formatfield('235959',tfield1,testdummy), '235959','basic')
        self.assertEqual(self.edi._formatfield('123456',tfield1,testdummy), '123456','basic')
        self.assertEqual(self.edi._formatfield('0931233',tfield1,testdummy), '0931233','basic')
        self.assertEqual(self.edi._formatfield('09312334',tfield1,testdummy), '09312334','basic')
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'240001',tfield1,testdummy) #no valid date
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'126101',tfield1,testdummy) #no valid date
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'120062',tfield1,testdummy) #no valid date - python allows 61 secnds?
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'240000',tfield1,testdummy) #no valid date
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'250001',tfield1,testdummy) #no valid date
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'-12000',tfield1,testdummy) #no valid date
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'120',tfield1,testdummy) #too short
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'11PM',tfield1,testdummy) #alfanum
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'TIME',tfield1,testdummy) #alfanum
    def testformatfieldA(self):
        tfield1 = ['TEST1', 'M', 5,   'T', True,   0,      0,'A']
        #                    length            decimals minlength 
        self.assertEqual(self.edi._formatfield('abcde',tfield1,testdummy), 'abcde','basic')
        self.assertEqual(self.edi._formatfield('',tfield1,testdummy), '','basic')
        self.assertEqual(self.edi._formatfield('',tfield1,testdummy), '','basic')
        self.assertEqual(self.edi._formatfield('   ab',tfield1,testdummy), 'ab','basic')
        self.assertEqual(self.edi._formatfield('ab   ',tfield1,testdummy), 'ab','basic')
        self.assertEqual(self.edi._formatfield('	ab',tfield1,testdummy), 'ab','basic')
        self.assertEqual(self.edi._formatfield('ab	',tfield1,testdummy), 'ab','basic')
        self.assertEqual(self.edi._formatfield('a	b',tfield1,testdummy), 'a	b','basic')
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'abcdef',tfield1,testdummy) #no valid date
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'ab    ',tfield1,testdummy) #no valid date
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'    ab',tfield1,testdummy) #no valid date - python allows 61 secnds?
        tfield1 = ['TEST1', 'M', 5,   'T', True,   0,      2,'A']
        #                    length            decimals minlength 
        self.assertEqual(self.edi._formatfield('abcde',tfield1,testdummy), 'abcde','basic')
        self.assertEqual(self.edi._formatfield('  ab',tfield1,testdummy), 'ab','basic')
        self.assertEqual(self.edi._formatfield('ab   ',tfield1,testdummy), 'ab','basic')
        self.assertEqual(self.edi._formatfield('	ab',tfield1,testdummy), 'ab','basic')
        self.assertEqual(self.edi._formatfield('ab	',tfield1,testdummy), 'ab','basic')
        self.assertEqual(self.edi._formatfield('a	b',tfield1,testdummy), 'a	b','basic')
        self.assertEqual(self.edi._formatfield('  ',tfield1,testdummy), '','basic')
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'a',tfield1,testdummy) #no valid date
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'abcdef',tfield1,testdummy) #no valid date
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'ab    ',tfield1,testdummy) #no valid date
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'    ab',tfield1,testdummy) #no valid date - python allows 61 secnds?
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,' ',tfield1,testdummy) #no valid date - python allows 61 secnds?
        self.assertRaises(botslib.InMessageFieldError,self.edi._formatfield,'',tfield1,testdummy) #no valid date - python allows 61 secnds?

    def testEdifact0402(self):
        # old format test are run
        self.assertRaises(botslib.InMessageFieldError,inmessage.edifromfile,editype='edifact',
            messagetype='edifact',filename='botssys/infile/unitformats/040201F.edi')
        self.assertRaises(botslib.InMessageFieldError,inmessage.edifromfile,editype='edifact',
            messagetype='edifact',filename='botssys/infile/unitformats/040202F.edi')
        self.assertRaises(botslib.InMessageFieldError,inmessage.edifromfile,editype='edifact',
            messagetype='edifact',filename='botssys/infile/unitformats/040203F.edi')
        self.assertRaises(botslib.InMessageFieldError,inmessage.edifromfile,editype='edifact',
            messagetype='edifact',filename='botssys/infile/unitformats/040204F.edi')
        self.assertRaises(botslib.InMessageFieldError,inmessage.edifromfile,editype='edifact',
            messagetype='edifact',filename='botssys/infile/unitformats/040205F.edi')
        self.assertRaises(botslib.InMessageError,inmessage.edifromfile,editype='edifact',
            messagetype='edifact',filename='botssys/infile/unitformats/040206F.edi')
        self.assertRaises(botslib.InMessageError,inmessage.edifromfile,editype='edifact',
            messagetype='edifact',filename='botssys/infile/unitformats/040207F.edi')
        self.assertRaises(botslib.InMessageError,inmessage.edifromfile,editype='edifact',
            messagetype='edifact',filename='botssys/infile/unitformats/040208F.edi')
        self.assertRaises(botslib.InMessageError,inmessage.edifromfile,editype='edifact',
            messagetype='edifact',filename='botssys/infile/unitformats/040209F.edi')
        self.assertRaises(botslib.InMessageFieldError,inmessage.edifromfile,editype='edifact',
            messagetype='edifact',filename='botssys/infile/unitformats/040210F.edi')
        self.assertRaises(botslib.InMessageFieldError,inmessage.edifromfile,editype='edifact',
            messagetype='edifact',filename='botssys/infile/unitformats/040211F.edi')
        self.assertRaises(botslib.InMessageFieldError,inmessage.edifromfile,editype='edifact',
            messagetype='edifact',filename='botssys/infile/unitformats/040212F.edi')
        self.failUnless(inmessage.edifromfile(editype='edifact',
            messagetype='edifact',filename='botssys/infile/unitformats/040214T.edi'), 'standaard test')
        self.assertRaises(botslib.InMessageFieldError,inmessage.edifromfile,editype='edifact',
            messagetype='edifact',filename='botssys/infile/unitformats/040215F.edi')
        self.assertRaises(botslib.InMessageFieldError,inmessage.edifromfile,editype='edifact',
            messagetype='edifact',filename='botssys/infile/unitformats/040217F.edi')
        self.assertRaises(botslib.InMessageFieldError,inmessage.edifromfile,editype='edifact',
            messagetype='edifact',filename='botssys/infile/unitformats/040218F.edi')
        self.assertRaises(botslib.InMessageFieldError,inmessage.edifromfile,editype='edifact',
            messagetype='edifact',filename='botssys/infile/unitformats/040219F.edi')
            


if __name__ == '__main__':
    botsinit.generalinit('config')
    #~ botslib.initbotscharsets()
    botsinit.initenginelogging()
    unittest.main()
