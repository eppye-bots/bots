'''module contains the functions to be called from user scripts'''
import pickle
import re
import copy
#bots-modules
import botslib
import botsglobal
import inmessage
import outmessage
from botsconfig import *

#*******************************************************************************************************************
#****** functions imported from other modules. reason: user scripting uses primary transform functions *************
#*******************************************************************************************************************
from botslib import addinfo,updateinfo,changestatustinfo,checkunique
from envelope import mergemessages
from communication import run 


@botslib.log_session    
def splitmailbag(startstatus=MAILBAG,endstatus=TRANSLATE,idroute=''):
    ''' splits 'mailbag'files to seperate files each containging one interchange (ISA-IEA or UNA/UNB-UNZ).
        handles x12 and edifact; these can be mixed.
    '''
    for row in botslib.query(u'''SELECT idta,filename,charset
                                FROM  ta
                                WHERE   idta>%(rootidta)s
                                AND     status=%(status)s
                                AND     statust=%(statust)s
                                AND     idroute=%(idroute)s
                                ''',
                                {'status':startstatus,'statust':OK,'idroute':idroute,'rootidta':botslib.get_minta4query()}):
        try:
            ta_org=botslib.OldTransaction(row['idta'])
            ta_intermediate = ta_org.copyta(status=MAILBAGPARSED)
            edifile = botslib.readdata(filename=row['filename'],charset=row['charset'])
            botsglobal.logmap.debug(u'Start parsing mailbag file "%s".',row['filename'])
            header = re.compile('(\s*(ISA))|(\s*(UNA.{6})?\s*(UNB).{1}(.{4}).{1}(.{1}))',re.DOTALL)
            #           group:    1   2       3  4            5        6         7
            startpos=0
            while (1):
                found = header.search(edifile[startpos:])
                if found==None:
                    if not startpos:
                        raise botslib.InMessageError(u'Found no content in mailbag.')
                    break
                if found.group(1):
                    editype='x12'
                    headpos=startpos+ found.start(2)
                    count=0
                    for c in edifile[headpos:headpos+120]:  #search first 120 characters to find seperators
                        if c in '\r\n' and count!=105:
                            continue
                        count +=1
                        if count==4:
                            field_sep = c
                        elif count==106:
                            record_sep = c
                            break
                    foundtrailer = re.search(re.escape(record_sep)+'\s*IEA'+re.escape(field_sep)+'.+?'+re.escape(record_sep),edifile[headpos:],re.DOTALL)
                elif found.group(3):
                    editype='edifact'
                    if found.group(4):
                        field_sep = edifile[startpos + found.start(4) + 4]
                        record_sep = edifile[startpos + found.start(4) + 8]
                        headpos=startpos+ found.start(4)
                    else:
                        field_sep = '+'
                        record_sep = "'"
                        headpos=startpos+ found.start(5)
                    foundtrailer = re.search(re.escape(record_sep)+'\s*UNZ'+re.escape(field_sep)+'.+?'+re.escape(record_sep),edifile[headpos:],re.DOTALL)
                if not foundtrailer:
                    raise botslib.InMessageError(u'Found no valid envelope trailer in mailbag.')
                endpos = headpos+foundtrailer.end()
                #so: interchange is from headerpos untill endpos
                #~ if header.search(edifile[headpos+25:endpos]):   #check if there is another header in the interchange
                    #~ raise botslib.InMessageError(u'Error in mailbag format: found no valid envelope trailer.')
                ta_tomes=ta_intermediate.copyta(status=endstatus)  #make transaction for translated message; gets ta_info of ta_frommes
                tofilename = str(ta_tomes.idta)
                tofile = botslib.opendata(tofilename,'wb',charset=row['charset'])
                tofile.write(edifile[headpos:endpos])
                tofile.close()
                ta_tomes.update(status=STATUSTMP,statust=OK,filename=tofilename,editype=editype,messagetype=editype) #update outmessage transaction with ta_info; 
                startpos=endpos
        except:
            txt=botslib.txtexc()
            ta_intermediate.failure()
            ta_intermediate.update(statust=ERROR,errortext=txt)
        else:
            botsglobal.logmap.debug(u'OK Parsing mailbag file "%s".',row['filename'])
            ta_org.update(statust=DONE)
            ta_intermediate.succes(endstatus)
            ta_intermediate.update(statust=DONE)


@botslib.log_session    
def translate(startstatus=TRANSLATE,endstatus=TRANSLATED,idroute=''):
    ''' translates edifiles in one or more edimessages.
        reads and parses edifiles that have to be translated.
        tries to split files into messages (using 'nextmessage' of grammar); if no splitting: edifile is one message.
        seaches the right translation in translate-table;
        runs the mapping-script for the translation;
        Function takes db-ta with status=TRANSLATE->PARSED->SPLITUP->TRANSLATED
    '''
    #select edifiles to translate; fill ta-object
    #~ import gc
    #~ gc.disable()
    for row in botslib.query(u'''SELECT idta,frompartner,topartner,filename,messagetype,testindicator,editype,charset,alt,fromchannel
                                FROM  ta
                                WHERE   idta>%(rootidta)s
                                AND     status=%(status)s
                                AND     statust=%(statust)s
                                AND     idroute=%(idroute)s
                                ''',
                                {'status':startstatus,'statust':OK,'idroute':idroute,'rootidta':botslib.get_minta4query()}):
        try:
            ta_fromfile=botslib.OldTransaction(row['idta'])  #TRANSLATE ta
            ta_parsedfile = ta_fromfile.copyta(status=PARSED)  #copy TRANSLATE to PARSED ta
            #whole edi-file is read, parsed and made into a inmessage-object:
            edifile = inmessage.edifromfile(frompartner=row['frompartner'],
                                            topartner=row['topartner'],
                                            filename=row['filename'],
                                            messagetype=row['messagetype'],
                                            testindicator=row['testindicator'],
                                            editype=row['editype'],
                                            charset=row['charset'],
                                            alt=row['alt'],
                                            fromchannel=row['fromchannel'],
                                            idroute=idroute)
            
            botsglobal.logger.debug(u'Start read and parse input file editype "%s" messagetype "%s".',row['editype'],row['messagetype'])
            for inn in edifile.nextmessage():   #for each message in the edifile:
                #inn.ta_info: parameters from inmessage.edifromfile(), syntax-information and parse-information
                ta_frommes=ta_parsedfile.copyta(status=SPLITUP)    #copy PARSED to SPLITUP ta
                inn.ta_info['idta_fromfile'] = ta_fromfile.idta     #for confirmations in user script; used to give idta of 'confirming message'
                ta_frommes.update(**inn.ta_info)    #update ta-record SLIPTUP with info from message content and/or grammar
                #~ print 'alt',inn.ta_info['alt']
                #~ print 'frompartner', inn.ta_info['frompartner']
                #~ print 'topartner',inn.ta_info['topartner']
                while 1:    #whileloop continues as long as there are alt-translations
                    #************select parameters for translation(script):
                    for row2 in botslib.query(u'''SELECT tscript,tomessagetype,toeditype
                                                FROM    translate
                                                WHERE   frommessagetype = %(frommessagetype)s
                                                AND     fromeditype = %(fromeditype)s
                                                AND     active=%(booll)s
                                                AND     (alt='' OR alt=%(alt)s)
                                                AND     (frompartner_id IS NULL OR frompartner_id=%(frompartner)s OR frompartner_id in (SELECT to_partner_id 
                                                                                                                            FROM partnergroup
                                                                                                                            WHERE from_partner_id=%(frompartner)s ))
                                                AND     (topartner_id IS NULL OR topartner_id=%(topartner)s OR topartner_id in (SELECT to_partner_id
                                                                                                                            FROM partnergroup
                                                                                                                            WHERE from_partner_id=%(topartner)s ))
                                                ORDER BY alt DESC,frompartner_id DESC, topartner_id DESC''',
                                                {'frommessagetype':inn.ta_info['messagetype'],
                                                 'fromeditype':inn.ta_info['editype'],
                                                 'alt':inn.ta_info['alt'],
                                                 'frompartner':inn.ta_info['frompartner'],
                                                 'topartner':inn.ta_info['topartner'],
                                                'booll':True}):
                        break  #escape if found; we need only the first - ORDER BY in the query 
                    else:   #no translation record is found
                        raise botslib.TranslationNotFoundError(u'Editype "$editype", messagetype "$messagetype", frompartner "$frompartner", topartner "$topartner", alt "$alt"',
                                                                                                            editype=inn.ta_info['editype'],
                                                                                                            messagetype=inn.ta_info['messagetype'],
                                                                                                            frompartner=inn.ta_info['frompartner'],
                                                                                                            topartner=inn.ta_info['topartner'],
                                                                                                            alt=inn.ta_info['alt'])
                    ta_tomes=ta_frommes.copyta(status=endstatus)  #copy SPLITUP to TRANSLATED ta
                    tofilename = str(ta_tomes.idta)
                    tscript=row2['tscript']
                    tomessage = outmessage.outmessage_init(messagetype=row2['tomessagetype'],editype=row2['toeditype'],filename=tofilename,reference=unique('messagecounter'),statust=OK,divtext=tscript)    #make outmessage object
                    #copy ta_info
                    botsglobal.logger.debug(u'Script "%s" translates messagetype "%s" to messagetype "%s".',tscript,inn.ta_info['messagetype'],tomessage.ta_info['messagetype'])
                    translationscript,scriptfilename = botslib.botsimport('mappings',inn.ta_info['editype'] + '.' + tscript) #get the mapping-script
                    doalttranslation = botslib.runscript(translationscript,scriptfilename,'main',inn=inn,out=tomessage)
                    botsglobal.logger.debug(u'Script "%s" finished.',tscript)
                    if 'topartner' not in tomessage.ta_info:    #tomessage does not contain values from ta...... 
                        tomessage.ta_info['topartner']=inn.ta_info['topartner']
                    botsglobal.logger.debug(u'Start writing output file editype "%s" messagetype "%s".',tomessage.ta_info['editype'],tomessage.ta_info['messagetype'])
                    tomessage.writeall()   #write tomessage (result of translation).
                    #problem is that not all values ta_tomes are know to to_message....
                    #~ print 'tomessage.ta_info',tomessage.ta_info
                    ta_tomes.update(**tomessage.ta_info) #update outmessage transaction with ta_info; 
                    del tomessage
                    #~ gc.collect()
                    if not doalttranslation:
                        break   #out of while loop
                    else:
                        inn.ta_info['alt'] = doalttranslation


                #end of while-loop
                #~ print inn.ta_info
                ta_frommes.update(statust=DONE,**inn.ta_info)   #update db. inn.ta_info could be changed by script. Is this useful?
                del inn
                #~ gc.collect()
                    
        #exceptions file_in-level
        except:
            #~ edifile.close(ta_fromfile,error=True)    #only useful if errors are reported in acknowledgement (eg x12 997). Not used now.
            txt=botslib.txtexc()
            print txt
            ta_parsedfile.failure()
            ta_parsedfile.update(statust=ERROR,errortext=txt)
            botsglobal.logger.debug(u'Error reading and parsing input file')
        else:
            edifile.close(ta_fromfile,error=False)
            ta_fromfile.update(statust=DONE)
            ta_parsedfile.update(statust=DONE,**edifile.confirminfo)
            botsglobal.logger.debug(u'Succesfull read and parse of input file')
            del edifile
        #~ gc.collect()
    #~ gc.enable()

        
def persist_add(domein,botskey,value):
    ''' store persistent values in db.
    '''
    content = pickle.dumps(value,0)
    if botsglobal.dbinfo.drivername != 'sqlite' and len(content)>1024:
        raise botslib.PersistError(u'Data too long for domein "$domein", botskey "$botskey", value "$value".',domein=domein,botskey=botskey,value=value)
    try:
        botslib.change(u'''INSERT INTO persist (domein,botskey,content)
                                VALUES   (%(domein)s,%(botskey)s,%(content)s)''',
                                {'domein':domein,'botskey':botskey,'content':content})
    except:
        raise botslib.PersistError(u'Failed to add for domein "$domein", botskey "$botskey", value "$value".',domein=domein,botskey=botskey,value=value)

def persist_update(domein,botskey,value):
    ''' store persistent values in db.
    '''
    content = pickle.dumps(value,0)
    if botsglobal.dbinfo.drivername != 'sqlite' and len(content)>1024:
        raise botslib.PersistError(u'Data too long for domein "$domein", botskey "$botskey", value "$value".',domein=domein,botskey=botskey,value=value)
    botslib.change(u'''UPDATE persist 
                          SET content=%(content)s
                        WHERE domein=%(domein)s
                          AND botskey=%(botskey)s''',
                            {'domein':domein,'botskey':botskey,'content':content})

def persist_delete(domein,botskey):
    ''' store persistent values in db.
    '''
    botslib.change(u'''DELETE FROM persist
                            WHERE domein=%(domein)s
                              AND botskey=%(botskey)s''',
                            {'domein':domein,'botskey':botskey})

def persist_lookup(domein,botskey):
    ''' lookup persistent values in db.
    '''
    for row in botslib.query(u'''SELECT content
                                FROM persist
                               WHERE domein=%(domein)s
                                 AND botskey=%(botskey)s''',
                            {'domein':domein,'botskey':botskey}):
        return pickle.loads(str(row['content']))
    return None

def safecodetconversion(ccodeid,leftcode,field='rightcode'):
    ''' converts code using a db-table.
        converted value is returned. 
    '''
    for row in botslib.query(u'''SELECT ''' +field+ '''
                                FROM    ccode
                                WHERE   ccodeid = %(ccodeid)s
                                AND     leftcode = %(leftcode)s''',
                                {'ccodeid':ccodeid,
                                 'leftcode':leftcode,
                                }):
        return row[field]
    return leftcode

def codetconversion(ccodeid,leftcode,field='rightcode'):
    ''' converts code using a db-table.
        converted value is returned. 
    '''
    for row in botslib.query(u'''SELECT ''' +field+ '''
                                FROM    ccode
                                WHERE   ccodeid = %(ccodeid)s
                                AND     leftcode = %(leftcode)s''',
                                {'ccodeid':ccodeid,
                                 'leftcode':leftcode,
                                }):
        return row[field]
    raise botslib.CodeConversionError(u'Value "$value" not in codetconversions, user table "$table".',value=rightcode,tabel=ccodeid)

def safercodetconversion(ccodeid,rightcode,field='leftcode'):
    ''' as codetconversion but reverses the dictionary first'''
    for row in botslib.query(u'''SELECT ''' +field+ '''
                                FROM    ccode
                                WHERE   ccodeid = %(ccodeid)s
                                AND     rightcode = %(rightcode)s''',
                                {'ccodeid':ccodeid,
                                 'rightcode':rightcode,
                                }):
        return row[field]
    return rightcode

def rcodetconversion(ccodeid,rightcode,field='leftcode'):
    ''' as codetconversion but reverses the dictionary first'''
    for row in botslib.query(u'''SELECT ''' +field+ '''
                                FROM    ccode
                                WHERE   ccodeid = %(ccodeid)s
                                AND     rightcode = %(rightcode)s''',
                                {'ccodeid':ccodeid,
                                 'rightcode':rightcode,
                                }):
        return row[field]
    raise botslib.CodeConversionError(u'Value "$value" not in codetconversions, user table "$table".',value=rightcode,tabel=ccodeid)

def safecodeconversion(modulename,value):
    ''' converts code using a codelist.
        converted value is returned. 
        codelist is first imported from file in codeconversions (lookup right place/mudule in bots.ini)
    '''
    module,filename = botslib.botsimport('codeconversions',modulename)
    try:
        return module.codeconversions[value]
    except KeyError:
        return value

def codeconversion(modulename,value):
    ''' converts code using a codelist.
        converted value is returned. 
        codelist is first imported from file in codeconversions (lookup right place/mudule in bots.ini)
    '''
    module,filename = botslib.botsimport('codeconversions',modulename)
    try:
        return module.codeconversions[value]
    except KeyError:
        raise botslib.CodeConversionError(u'Value "$value" not in file for codeconversion "$filename".',value=value,filename=filename)

def safercodeconversion(modulename,value):
    ''' as codeconversion but reverses the dictionary first'''
    module,filename = botslib.botsimport('codeconversions',modulename)
    if not hasattr(module,'botsreversed'+'codeconversions'):
        reversedict = dict((value,key) for key,value in module.codeconversions.items())
        setattr(module,'botsreversed'+'codeconversions',reversedict)
    try:
        return module.botsreversedcodeconversions[value]
    except KeyError:
        return value

def rcodeconversion(modulename,value):
    ''' as codeconversion but reverses the dictionary first'''
    module,filename = botslib.botsimport('codeconversions',modulename)
    if not hasattr(module,'botsreversed'+'codeconversions'):
        reversedict = dict((value,key) for key,value in module.codeconversions.items())
        setattr(module,'botsreversed'+'codeconversions',reversedict)
    try:
        return module.botsreversedcodeconversions[value]
    except KeyError:
        raise botslib.CodeConversionError(u'Value "$value" not in file for reversed codeconversion "$filename".',value=value,filename=filename)

def calceancheckdigit(ean):
    ''' input: EAN without checkdigit; returns the checkdigit'''
    try:
        if not ean.isdigit():
            raise botslib.EanError(u'EAN "$ean" should be string with only numericals',ean=ean)
    except AttributeError:
        raise botslib.EanError(u'EAN "$ean" should be string, but is a "$type"',ean=ean,type=type(ean))
    sum1=sum([int(x)*3 for x in ean[-1::-2]]) + sum([int(x) for x in ean[-2::-2]])
    return str((1000-sum1)%10)

def checkean(ean):
    ''' input: EAN; returns: True (valid EAN) of False (EAN not valid)'''
    return (ean[-1] == calceancheckdigit(ean[:-1]))

def addeancheckdigit(ean):
    ''' input: EAN without checkdigit; returns EAN with checkdigit'''
    return ean+calceancheckdigit(ean)


def unique(domein):
    ''' generate unique number within range domein.
        uses db to keep track of last generated number.
        if domein not used before, initialized with 1.
    '''
    return str(botslib.unique(domein))

def inn2out(inn,out):
    ''' copies inn-message to outmessage
    '''
    out.root = copy.deepcopy(inn.root)
    
def useoneof(*args):
    for arg in args:
        if arg:
            return arg
    else:
        return None
    
def dateformat(date):
    if not date:
        return None
    if len(date)==8:
        return '102'
    if len(date)==12:
        return '203'
    if len(date)==16:
        return '718'
    return None


