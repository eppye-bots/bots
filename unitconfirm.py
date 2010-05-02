import unittest
import filecmp 
import glob
import shutil
import os
import subprocess
import logging
import utilsunit
import bots.botslib as botslib
import bots.botsinit as botsinit
import bots.botsglobal as botsglobal
from bots.botsconfig import *

'''plugin unitconfirm.zip'''
botssys = 'bots/botssys'


class TestMain(unittest.TestCase):
    def testroutetestmdn(self):
        lijst = utilsunit.getdir(os.path.join(botssys,'outfile/confirm/mdn/*'))
        self.failUnless(len(lijst)==0)
        for row in botslib.query(u'''SELECT idta,confirmed,confirmidta
                                FROM    ta
                                WHERE   status=%(status)s
                                AND     statust=%(statust)s
                                AND     idroute=%(idroute)s
                                AND     confirmtype=%(confirmtype)s
                                AND     confirmasked=%(confirmasked)s
                                ORDER BY idta DESC
                                ''',
                                {'status':210,'statust':DONE,'idroute':'testmdn','confirmtype':'send-email-MDN','confirmasked':True}):
                                    
            self.failUnless(row[1])
            self.failUnless(row[2]!=0)
            break
        else:
            self.failUnless(1==0)
        for row in botslib.query(u'''SELECT idta,confirmed,confirmidta
                                FROM    ta
                                WHERE   status=%(status)s
                                AND     statust=%(statust)s
                                AND     idroute=%(idroute)s
                                AND     confirmtype=%(confirmtype)s
                                AND     confirmasked=%(confirmasked)s
                                ORDER BY idta DESC
                                ''',
                                {'status':510,'statust':DONE,'idroute':'testmdn','confirmtype':'ask-email-MDN','confirmasked':True}):
            self.failUnless(row[1])
            self.failUnless(row[2]!=0)
            break
        else:
            self.failUnless(1==0)
        

    def testroutetestmdn2(self):
        lijst = utilsunit.getdir(os.path.join(botssys,'outfile/confirm/mdn2/*'))
        self.failUnless(len(lijst)==0)
        for row in botslib.query(u'''SELECT idta,confirmed,confirmidta
                                FROM    ta
                                WHERE   status=%(status)s
                                AND     statust=%(statust)s
                                AND     idroute=%(idroute)s
                                AND     confirmtype=%(confirmtype)s
                                AND     confirmasked=%(confirmasked)s
                                ORDER BY idta DESC
                                ''',
                                {'status':510,'statust':DONE,'idroute':'testmdn2','confirmtype':'ask-email-MDN','confirmasked':True}):
            self.failUnless(not row[1])
            self.failUnless(row[2]==0)
            break
        else:
            self.failUnless(1==0)

    def testroutetest997(self):
        '''
        test997 1: pickup 850; send 850 (ask confirm) and 997
        test997 2: receive 997 and 850; send 997 
        test997 3: send 997 and 850 to trash
        test997 4: receive 997; 997 to trash
        '''
        lijst = utilsunit.getdir(os.path.join(botssys,'outfile/confirm/x12/*'))
        self.failUnless(len(lijst)==0)
        lijst = utilsunit.getdir(os.path.join(botssys,'outfile/confirm/trash/*'))
        self.failUnless(len(lijst)==3)
        counter=0
        for row in botslib.query(u'''SELECT idta,confirmed,confirmidta
                                FROM    ta
                                WHERE   status=%(status)s
                                AND     statust=%(statust)s
                                AND     idroute=%(idroute)s
                                AND     confirmtype=%(confirmtype)s
                                AND     confirmasked=%(confirmasked)s
                                ORDER BY idta DESC
                                ''',
                                {'status':400,'statust':DONE,'idroute':'test997','confirmtype':'ask-x12-997','confirmasked':True}):
            counter += 1
            if counter == 1:
                self.failUnless(not row[1])
                self.failUnless(row[2]==0)
            elif counter == 2:
                self.failUnless(row[1])
                self.failUnless(row[2]!=0)
            else:
                break
        else:
            self.failUnless(counter!=0)
        for row in botslib.query(u'''SELECT idta,confirmed,confirmidta
                                FROM    ta
                                WHERE   status=%(status)s
                                AND     statust=%(statust)s
                                AND     idroute=%(idroute)s
                                AND     confirmtype=%(confirmtype)s
                                AND     confirmasked=%(confirmasked)s
                                ORDER BY idta DESC
                                ''',
                                {'status':310,'statust':DONE,'idroute':'test997','confirmtype':'send-x12-997','confirmasked':True}):
            counter += 1
            if counter <= 2:
                self.failUnless(row[1])
                self.failUnless(row[2]!=0)
            else:
                break
        else:
            self.failUnless(counter!=0)

    def testrouteotherx12(self):
        lijst = utilsunit.getdir(os.path.join(botssys,'outfile/confirm/otherx12/*'))
        self.failUnless(len(lijst)==15)


if __name__ == '__main__':
    shutil.rmtree(os.path.join(botssys, 'outfile'),ignore_errors=True)    #remove whole output directory
    subprocess.call(['/home/hje/botsup/start-engine.py','-cconfig','--new'])
    botsinit.generalinit('/home/hje/botsup/bots/config')
    #~ botslib.initbotscharsets()
    botsinit.initenginelogging()
    botsinit.connect() 
    unittest.main()
    logging.shutdown()
    botsglobal.db.close