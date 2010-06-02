import unittest
import bots.inmessage as inmessage
import bots.botslib as botslib
import bots.xml2botsgrammar as xml2botsgrammar
import utilsunit
import filecmp 

'''plugin unitinmessageedifact.zip'''


class Test01(unittest.TestCase):
    def test01(self):
        ''' 0401	Errors in records'''
        self.failUnless(filecmp.cmp('botssys/infile/xml2botsgrammar/cmpgrammar.py','botssys/infile/xml2botsgrammar/grammar.py'))


if __name__ == '__main__':
    xml2botsgrammar.start('botssys/infile/xml2botsgrammar/test.xml','botssys/infile/xml2botsgrammar/grammar.py')
    unittest.main()
