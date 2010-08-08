#constants/definitions for Bots
#to be used as from bots.config import *

#for statust in ta:
OPEN    = 0 #Bots always closes transaction. OPEN is severe error
ERROR   = 1 #error in transaction.
OK      = 2 #succesfull, result is 'save'. But procesing has stopped: next step with error, or no next steps defined
DONE    = 3 #succesfull, and result is picked up by next step
#~ RETRANSMIT = 4   #reinjected archive edi-file

#for status in ta:
PROCESS    = 1
STATUSTMP= 2
DISCARD= 3

EXTERNIN  = 200      #transaction is OK; file is exported; out of reach
RAWIN    = 210    #the file as received, unprocessed; eg mail is in email-format (headers, body, attachments)
MIMEIN   = 215      #mime is checked and read; mime-info (sneder, receiver) is in db-ta
FILEIN   = 220    #received edifile; ready for further use
ZIP     = 270     #file is a zip file: split it upto be translated
ZIPPARSED = 275     #file is a mailbag: split it upto be translated
MAILBAG = 280     #file is a mailbag: split it upto be translated
MAILBAGPARSED = 290     #file is a mailbag: split it upto be translated
TRANSLATE = 300     #file to be translated
PARSED   = 310   #the edifile is lexed and parsed
SPLITUP    = 320        #the edimessages in the PARSED edifile have been split up
TRANSLATED = 330        #edimessage is result of translation
MERGED   =   400        #is enveloped
FILEOUT    = 500    #edifile ready to be 'send' (just the edi-file)
RAWOUT    = 510    #file in send fromat eg email format (including headers, body, attachemnts) 
EXTERNOUT  = 520      #transaction is complete; file is exported; out of reach

#grammar.structure: keys in grammarrecords
ID = 0 
MIN = 1
MAX = 2
COUNT = 3
LEVEL = 4
MPATH = 5
FIELDS = 6
QUERIES = 7
SUBTRANSLATION = 8

#grammar.recorddefs: dict keys for fields of record er: record[FIELDS][ID] == 'C124.0034'
#already definedID = 0
MANDATORY = 1
LENGTH = 2
SUBFIELDS = 2   #for composites
FORMAT = 3		#format in grammar file
ISFIELD = 4
DECIMALS = 5
MINLENGTH = 6
BFORMAT = 7		#internal bots format; formats in grammar are convertd to bformat

#modules inmessage, outmessage; record in self.records; ex: 
#already defined ID = 0
VALUE = 1
POS = 2
LIN = 3
SFIELD = 4  #boolean: True: is subfield, False: field or first element composite
#already defined MPATH = 5  #only for first field (=recordID)
FIXEDLINE = 6   #for fixed records; tmp storage of fixed record

