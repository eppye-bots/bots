import filecmp 
import shutil
import os
import sys
import subprocess
import logging
#import bots-modules
import bots.botslib as botslib
import bots.botsinit as botsinit
import bots.botsglobal as botsglobal
from bots.botsconfig import *

'''
plugin 'unittesterros'
activate routes!
in bots.ini: 
    debug = False
    max_number_errors = 25
all tests pass if finished with 'Tests OK!!!'
'''

def dummylogger():
    botsglobal.logger = logging.getLogger('dummy')
    botsglobal.logger.setLevel(logging.ERROR)
    botsglobal.logger.addHandler(logging.StreamHandler(sys.stdout))

def getreportlastrun():
    for row in botslib.query(u'''SELECT *
                            FROM    report
                            ORDER BY idta DESC
                            '''):
        #~ print row
        return row
    raise Exception('no report')

def geterrorlastrun():
    for row in botslib.query(u'''SELECT *
                            FROM    filereport
                            ORDER BY idta DESC
                            '''):
        #~ print row
        return row['errortext']
    raise Exception('no filereport')

def comparedicts(dict1,dict2):
    for key,value in dict1.items():
        if value != dict2[key]:
            raise Exception('error comparing "%s": should be %s but is %s (in db),'%(key,value,dict2[key]))

def removeWS(str):
    return ' '.join(str.split())


listoferrortests = [
    #edifact: all possible S and F errors
    {'infile':'ER01.edi','errortext':'''MessageError: [F19] Record "[['UNH'], ['ALI']]" too many fields in record; unknown field "ER" (line 5 position 14). [F18] Record "[['UNH'], ['NAD']]" too many subfields in composite; unknown subfield "9" (line 12 position 11). [F17] Record "[['UNH'], ['NAD']]" expect field but "9" is a subfield (line 13 position 8). [S03] Record "[['UNH'], ['DTM']]" occurs 1 times, min is 2. [F06] Record "[['UNH'], ['ALI']]" field "4183#5" too small (min 3): "ER". [S04] Record "[['UNH'], ['IMD']]" occurs 2 times, max is 1. [F05] Record "[['UNH'], ['NAD']]" field "3035" too big (max 3): "SUFF". [F02] Record "[['UNH'], ['NAD']]" field "3035" is mandatory. [F04] Record "[['UNH'], ['NAD']]" subfield "C082.3039" is mandatory: "{'3035': u'BU', 'BOTSID': u'NAD', 'C082.3055': u'9', 'BOTSIDnr': '1'}". [F09] Record "[['UNH'], ['LIN'], ['QTY']]" field "C186.6060" contains exponent: "E12". [F16] Record "[['UNH'], ['LIN'], ['QTY']]" numeric field "C186.6060" has non-numerical content: "E12". [F10] Record "[['UNH'], ['LIN'], ['QTY']]" field "C186.6060" too big (max 15): "1234567890123456789". [F16] Record "[['UNH'], ['LIN'], ['QTY']]" numeric field "C186.6060" has non-numerical content: "12JAJA". [F11] Record "[['UNH'], ['LIN'], ['QVR']]" field "C279.6064" too small (min 6): "123". [F03] Record "[['UNH'], ['LIN'], ['DOC']]" composite "C002" is mandatory.'''},
    #~ #edifact: all E errors 
    {'infile':'ER02.edi','errortext':'''MessageError: [E01] UNB-reference is "ER02.1"; should be equal to UNZ-reference "ER021". [E02] Count of messages in UNZ is 1; should be equal to number of messages 2. [E04] UNH-reference is "ER02.1.1"; should be equal to UNT-reference "ER02.11". [E06] Count of segments in UNT is invalid: "8.0". [E04] UNH-reference is "ER02.1.2"; should be equal to UNT-reference "ER02.12". [E05] Segmentcount in UNT is 8; should be equal to number of segments 9. [E01] UNB-reference is "ER02.2"; should be equal to UNZ-reference "ER022". [E03] Count of messages in UNZ is invalid: "2.0". [E04] UNH-reference is "ER02.2.1"; should be equal to UNT-reference "ER02.21". [E05] Segmentcount in UNT is 8; should be equal to number of segments 9. [E01] UNB-reference is "ER02.1"; should be equal to UNZ-reference "ER021". [E02] Count of messages in UNZ is 2; should be equal to number of messages 1. [E07] UNG-reference is "ER02.1.1"; should be equal to UNE-reference "ER02.11". [E09] Groupcount in UNE is invalid: "1.0".[E10] UNH-reference is "ER02.1.1"; should be equal to UNT-reference "ER02.11". [E12] Count of segments in UNT is invalid: "8.0". [E10] UNH-reference is "ER02.1.2"; should be equal to UNT-reference "ER02.12". [E11] Segmentcount in UNT is 8; should be equal to number of segments 9. [E01] UNB-reference is "ER02.2"; should be equal to UNZ-reference "ER022". [E03] Count of messages in UNZ is invalid: "2.0". [E07] UNG-reference is "ER02.2.1"; should be equal to UNE-reference "ER02.21". [E08] Groupcount in UNE is 2; should be equal to number of groups 1. [E10] UNH-reference is "ER02.2.1"; should be equal to UNT-reference "ER02.21". [E11] Segmentcount in UNT is 8; should be equal to number of segments 9.'''},
    #~ #no UNB in start of edifact file
    {'infile':'ER03.edi','errortext':'''InMessageError: No "UNB" at the start of edifact file.'''},
    #~ #no UNB after UNZ
    {'infile':'ER04.edi','errortext':'''InMessageError: Unknown data beyond end of message; mostly problem with separators or message structure: "[{1: u'UNH', 2: 1, 3: 21, 4: False}, {1: u'T0000000004-3', 2: 5, 3: 21, 4: False}, {1: u'ORDERS', 2: 19, 3: 21, 4: False}, {1: u'D', 2: 26, 3: 21, 4: True}, {1: u'96A', 2: 28, 3: 21, 4: True}, {1: u'UN', 2: 32, 3: 21, 4: True}, {1: u'EAN008', 2: 35, 3: 21, 4: True}]"'''},
    #~ #no UNZ (before another interchange)
    {'infile':'ER05.edi','errortext':'''InMessageError: Line:20 pos:1; record:"UNB" not in grammar; looked in grammar until mandatory record: "[['UNB'], ['UNZ']]".'''},
    #~ #no UNZ at end of file
    {'infile':'ER06.edi','errortext':'''InMessageError: Missing mandatory record "[['UNB'], ['UNZ']]".'''},
    #~ #no UNH
    {'infile':'ER07.edi','errortext':'''InMessageError: Line:2 pos:1; record:"BGM" not in grammar; looked in grammar until mandatory record: "[['UNB'], ['UNZ']]".'''},
    #~ #no BGM (M)
    {'infile':'ER08.edi','errortext':'''InMessageError: Line:3 pos:1; record:"DTM" not in grammar; looked in grammar until mandatory record: "[['UNH'], ['BGM']]".'''},
    #~ #unknown messagetype
    {'infile':'ER09.edi','errortext':'''InMessageError: No (valid) grammar for editype "edifact" messagetype "ORDERSD96AUNEAN004".'''},
    #~ #x12: all possible S and E errors
    {'infile':'ER01.x12','errortext':'''MessageError: [F17] Record "[['ST'], ['ZZ5']]" expect field but "123" is a subfield (line 18 position 13). [F18] Record "[['ST'], ['ZZ5']]" too many subfields in composite; unknown subfield "123" (line 19 position 13). [F19] Record "[['ST'], ['ZZ5']]" too many fields in record; unknown field "123" (line 20 position 7). [S03] Record "[['ST'], ['ZZ0']]" occurs 1 times, min is 2. [F02] Record "[['ST'], ['ZZA']]" field "ZZA02" is mandatory. [S04] Record "[['ST'], ['ZZA']]" occurs 2 times, max is 1. [F03] Record "[['ST'], ['ZZ1']]" composite "ZZ101" is mandatory. [F10] Record "[['ST'], ['ZZ1']]" field "ZZ101.01" too big (max 3): "1234". [F11] Record "[['ST'], ['ZZ1']]" field "ZZ101.01" too small (min 2): "1". [F09] Record "[['ST'], ['ZZ2']]" field "ZZ101.01" contains exponent: "TE". [F13] Record "[['ST'], ['ZZ2']]" numeric field "ZZ101.01" has non-numerical content: "TE". [F04] Record "[['ST'], ['ZZ2']]" subfield "ZZ101.02" is mandatory: "{'ZZ202': u'TE', 'ZZ101.01': u'TE', 'BOTSID': u'ZZ2', 'BOTSIDnr': '1'}". [F07] Record "[['ST'], ['ZZ3']]" date field "ZZ301.01" not a valid date: "20121312". [F08] Record "[['ST'], ['ZZ3']]" time field "ZZ301.02" not a valid time: "2500". [F11] Record "[['ST'], ['ZZ3']]" field "ZZ302" too small (min 5): "12". [F10] Record "[['ST'], ['ZZ3']]" field "ZZ302" too big (max 10): "12345678901". [F12] Record "[['ST'], ['ZZ3']]" field "ZZ302" has format "I" but contains decimal sign: "12345.67". [F05] Record "[['ST'], ['ZZ4']]" field "ZZ401.01" too big (max 4): "12345". [F06] Record "[['ST'], ['ZZ4']]" field "ZZ401.01" too small (min 4): "123". [F16] Record "[['ST'], ['ZZ5']]" numeric field "ZZ501.01" has non-numerical content: "123A".'''},
    #~ #x12: all E errors
    {'infile':'ER02.x12','errortext':'''MessageError: [F12] Record "[['ST'], ['SE']]" field "SE01" has format "I" but contains decimal sign: "6.0". [E13] ISA-reference is "000000001"; should be equal to IEA-reference "100000001". [E14] Count in IEA-IEA01 is 2; should be equal to number of groups 1. [E16] GS-reference is "11"; should be equal to GE-reference "1011". [E17] Count in GE-GE01 is 1; should be equal to number of transactions: 2. [E19] ST-reference is "000000111"; should be equal to SE-reference "100000111". [E21] Count of segments in SE is invalid: "6.0". [E13] ISA-reference is "000000002"; should be equal to IEA-reference "100000002". [E15] Count of messages in IEA is invalid: "1.0". [E18] Count of messages in GE is invalid: "2.0". [E16] GS-reference is "22"; should be equal to GE-reference "1022". [E17] Count in GE-GE01 is 1; should be equal to number of transactions: 2. [E19] ST-reference is "000000222"; should be equal to SE-reference "100000222". [E20] Count in SE-SE01 is 6; should be equal to number of segments 5. [F12] Record "[['ISA'], ['GS'], ['GE']]" field "GE01" has format "I" but contains decimal sign: "2.0". [F12] Record "[['ISA'], ['IEA']]" field "IEA01" has format "I" but contains decimal sign: "1.0".'''},
    #~ #fixed format: string too long
    {'infile':'ER01.fix','errortext':'''InMessageError: line 15 record "TOT" too long; is 324 pos, defined is 323 pos: "TOT0000000000000240.5000000000000000000.0000000000000000045.7000000000000000286.2000000000000000240.500S 0000019.00000000000000001111.1100000000000000011.110S 0000006.00000000000000002222.2200000000000000022.200S 0000000.00000000000000003333.3300000000000000033.300E 0000000.00000000000000004444.4400000000000000044.400 ".'''},
    #~ #fixed format: string too short
    {'infile':'ER02.fix','errortext':'''InMessageError: line 12 record "LIN" too short; is 180 pos, defined is 181 pos: "LIN0000038712345678906 000000000002.000000000000002.0000000000000000013.000000000000000006.5000000000000000.000 S 000019.0000".'''},
    #~ #fixed format: empty segment tag
    {'infile':'ER03.fix','errortext':'''InMessageError: Line:2 pos:0; record:"" not in grammar; looked in grammar until mandatory record: "[['HEA'], ['TOT']]".'''},
    #~ #fixed format: all possible S and F errors
    {'infile':'ER04.fix','errortext':'''MessageError: [F02] Record "[['HEA']]" field "SOORT" is mandatory. [F14] Record "[['HEA'], ['HAL']]" numeric field "BTWPERCENTAGE" has invalid nr of decimals: "00000019.000". [S04] Record "[['HEA'], ['HAL']]" occurs 3 times, max is 2. [S03] Record "[['HEA'], ['LIN'], ['LAL']]" occurs 1 times, min is 2. [F12] Record "[['HEA'], ['LIN'], ['TOE']]" field "TOTAALREGEL" has format "I" but contains decimal sign: "0000000000000240.500". [F15] Record "[['HEA'], ['LIN'], ['TOE']]" numeric field "TOTAALFACTUURKORTING" has non-numerical content: "000000000000000D.000". [F13] Record "[['HEA'], ['LIN'], ['TOE']]" numeric field "TOTAALBTW" has non-numerical content: "0000000000000045D700". [F16] Record "[['HEA'], ['LIN'], ['TOE']]" numeric field "TOTAALFACTUUR" has non-numerical content: "000000000000$286.200".'''},
    #~ #out: fixed->edifact: all possible S and F errors
    {'infile':'OK01-ERROUT.fix','errortext':'''MessageError: [F01] Record: "[['UNH'], ['BGM']]" field "XXXX" does not exist in grammar. [S01] Record "BGM" in message has children, but these are not in grammar "/home/hje/Bots/botsdev/bots/bots.usersys/grammars/edifact.INVOICD96AUNEAN008". Found record "DTM". [S02] Record "XXX" in message but not in grammar "/home/hje/Bots/botsdev/bots/bots.usersys/grammars/edifact.INVOICD96AUNEAN008". Content of record: "{'BOTSIDnr': u'1', 'BOTSID': u'XXX', '4343': u'HEA'}". [S04] Record "[['UNH'], ['BGM']]" occurs 2 times, max is 1. [S03] Record "[['UNH'], ['DTM']]" occurs 0 times, min is 1. [F03] Record "[['UNH'], ['PAI']]" composite "C534" is mandatory. [F02] Record "[['UNH'], ['FTX']]" field "4451" is mandatory. [F20] Record "[['UNH'], ['RFF']]" field "C506.1153" too big (max 3): "AAAA". [F21] Record "[['UNH'], ['RFF']]" field "C506.4000" too small (min 35): "A". [F04] Record "[['UNH'], ['NAD']]" subfield "C082.3039" is mandatory: "{'3035': u'XX', 'BOTSID': u'NAD', 'C082.3055': u'9', 'BOTSIDnr': u'1'}". [F24] Record "[['UNH'], ['PAT'], ['MOA']]" field "C516.5004" numerical format not valid: ".". [F25] Record "[['UNH'], ['PAT'], ['MOA']]" field "C516.5004" numerical format not valid: "0001D". [F28] Record "[['UNH'], ['PAT'], ['MOA']]" field "C516.5004" too big: "12345678901234567890".'''},
    #~ #out: edifact->fixed: all possible S and F errors
    {'infile':'OK01-ERROUT.edi','errortext':'''MessageError: [S01] Record "LIN" in message has children, but these are not in grammar "/home/hje/Bots/botsdev/bots/bots.usersys/grammars/fixed.ordersfixed". Found record "HEB". [S02] Record "HEB" in message but not in grammar "/home/hje/Bots/botsdev/bots/bots.usersys/grammars/fixed.ordersfixed". Content of record: "{'BOTSIDnr': u'1', 'BOTSID': u'HEB'}". [F20] Record "[['HEA']]" field "EANONTVANGER" too big (max 13): "12345678901234". [F22] Record "[['HEA']]" date field "ORDERDATUM" not a valid date: "20120230". [F23] Record "[['HEA']]" time field "ORDERTIME" not a valid time: "2500". [S03] Record "[['HEA'], ['DUM'], ['DUL']]" occurs 0 times, min is 1. [S04] Record "[['HEA'], ['DUM']]" occurs 2 times, max is 1. [F24] Record "[['HEA'], ['DUN']]" field "DUN1" numerical format not valid: ".". [F24] Record "[['HEA'], ['DUN']]" field "DUN2" numerical format not valid: ".". [F24] Record "[['HEA'], ['DUN']]" field "DUN3" numerical format not valid: ".". [F24] Record "[['HEA'], ['DUN']]" field "DUN4" numerical format not valid: ".". [F24] Record "[['HEA'], ['DUN']]" field "DUN5" numerical format not valid: ".". [F26] Record "[['HEA'], ['DUN']]" field "DUN1" numerical format not valid: "123%". [F26] Record "[['HEA'], ['DUN']]" field "DUN2" numerical format not valid: "12345E". [F27] Record "[['HEA'], ['DUN']]" field "DUN3" numerical format not valid: "123^". [F27] Record "[['HEA'], ['DUN']]" field "DUN4" numerical format not valid: "123^". [F25] Record "[['HEA'], ['DUN']]" field "DUN5" numerical format not valid: "0.1R". [F28] Record "[['HEA'], ['DUN']]" field "DUN1" too big: "1234567". [F28] Record "[['HEA'], ['DUN']]" field "DUN2" too big: "12345.00". [F28] Record "[['HEA'], ['DUN']]" field "DUN3" too big: "1234567". [F28] Record "[['HEA'], ['DUN']]" field "DUN4" too big: "1234500". [F28] Record "[['HEA'], ['DUN']]" field "DUN5" too big: "123456.11".'''},
    #~ #tradacoms: all E errors 
    {'infile':'ER01.tra','errortext':'''MessageError: [E22] Count in END is 2; should be equal to number of messages 3. [E24] Count in MTR is 5; should be equal to number of segments 6. [E24] Count in MTR is 6; should be equal to number of segments 7. [E24] Count in MTR is 2; should be equal to number of segments 3. [E23] Count of messages in END is invalid: "3.0". [E25] Count of segments in MTR is invalid: "6.0". [E25] Count of segments in MTR is invalid: "7.0". [E25] Count of segments in MTR is invalid: "3.0".'''},
    #~ #tradacoms->xml: all possible S and F errors
    {'infile':'ER02.tra','errortext':'''MessageError: [S02] Record "test" in message but not in grammar "/home/hje/Bots/botsdev/bots/bots.usersys/grammars/xml.orders". Content of record: "{'BOTSIDnr': u'1', 'BOTSID': u'test'}". [F01] Record: "[['envelope'], ['message']]" field "sender2" does not exist in grammar. [S01] Record "party" in message has children, but these are not in grammar "/home/hje/Bots/botsdev/bots/bots.usersys/grammars/xml.orders". Found record "test". [F02] Record "[['envelope'], ['message']]" field "sender" is mandatory. [F20] Record "[['envelope'], ['message']]" field "senderqua" too big (max 3): "1234". [F21] Record "[['envelope'], ['message']]" field "receiverqua" too small (min 3): "12". [F22] Record "[['envelope'], ['message']]" date field "envtestdtm" not a valid date: "20120230". [F23] Record "[['envelope'], ['message']]" time field "envtesttime" not a valid time: "2523". [S03] Record "[['envelope'], ['message'], ['partys'], ['party']]" occurs 0 times, min is 1. [S04] Record "[['envelope'], ['message'], ['partys']]" occurs 2 times, max is 1.'''},
    ]

def run_error_tests():
    for test in listoferrortests:
        #write correct testfile
        shutil.copyfile(botslib.join(botssys,'infile/unittesterrors/input',test['infile']),botslib.join(botssys,'infile/unittesterrors',test['infile']))
        subprocess.call(newcommand)     #run bots
        comparedicts({'status':1,'lastreceived':1,'lasterror':1,'lastdone':0,'lastok':0,'lastopen':0,'send':0,'processerrors':0},getreportlastrun()) #check report
        errortext = geterrorlastrun()
        if removeWS(test['errortext']) != removeWS(errortext):     #check error
            raise Exception('another errortekst; test "%s"'%(test['infile']))

listofoktests = [
    {'infile':'OK01.edi'},
    {'infile':'OK01.fix'},
    {'infile':'OK02.fix'},
    {'infile':'OK01.tra'},   #to xml
    {'infile':'OK02.tra'},  #to xmlnocheck
    {'infile':'OK01.xml'},  #xml to tradacoms
    {'infile':'OK01.xmlnocheck'},  #xml to tradacoms
    {'infile':'OK02.edi'},  #edifact 2 template
    {'infile':'OK01.csv'},  #csv 2 edifact
    {'infile':'OK03.edi'},  #edifact 2 csv
    ]

    
def run_ok_tests():
    for test in listofoktests:
        #delete result file (always one result file, fixed name)
        try:
            os.remove(botslib.join(botssys,'outfile/unittesterrors/result.txt'))
        except:
            pass
        #write correct testfile
        shutil.copyfile(botslib.join(botssys,'infile/unittesterrors/input',test['infile']),botslib.join(botssys,'infile/unittesterrors',test['infile']))
        subprocess.call(newcommand)     #run bots
        comparedicts({'status':0,'lastreceived':1,'lasterror':0,'lastdone':1,'lastok':0,'lastopen':0,'send':1,'processerrors':0},getreportlastrun()) #check report
        if not filecmp.cmp(botslib.join(botssys,'infile/unittesterrors/compare',test['infile']),botslib.join(botssys,'outfile/unittesterrors/result.txt')):
            raise Exception('output translation not as expected; test "%s"'%(test['infile']))


if __name__=='__main__':
    pythoninterpreter = 'python2.7'
    newcommand = [pythoninterpreter,'bots-engine.py',]
    botsinit.generalinit('config')
    dummylogger()
    botsinit.connect()
    #~ usersys = botsglobal.ini.get('directories','usersysabs')
    botssys = botsglobal.ini.get('directories','botssys')
    
    run_error_tests()
    run_ok_tests()

    logging.shutdown()
    botsglobal.db.close
    
    print 'Tests OK!!!' 
