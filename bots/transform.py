'''module contains the functions to be called from user scripts'''
try:
    import cPickle as pickle
except ImportError:
    import pickle
import copy
import collections
from django.utils.translation import ugettext as _
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
def translate(startstatus=TRANSLATE,endstatus=TRANSLATED,idroute=''):
    ''' translates edifiles in one or more edimessages.
        reads and parses edifiles that have to be translated.
        tries to split files into messages (using 'nextmessage' of grammar); if no splitting: edifile is one message.
        searches the right translation in translate-table;
        runs the mapping-script for the translation;
        Function takes db-ta with status=TRANSLATE->PARSED->SPLITUP->TRANSLATED
    '''
    try:
        userscript,scriptname = botslib.botsimport('mappings','translation')
    except ImportError:       #script is not there; other errors like syntax errors are not catched
        userscript = scriptname = None
    #select edifiles to translate; fill ta-object
    for row in botslib.query(u'''SELECT idta,frompartner,topartner,filename,messagetype,testindicator,editype,charset,alt,fromchannel
                                FROM  ta
                                WHERE   idta>%(rootidta)s
                                AND     status=%(status)s
                                AND     statust=%(statust)s
                                AND     idroute=%(idroute)s
                                ''',
                                {'status':startstatus,'statust':OK,'idroute':idroute,'rootidta':botslib.get_minta4query()}):
        try:
            ta_fromfile = botslib.OldTransaction(row['idta'])  #TRANSLATE ta
            ta_parsedfile = ta_fromfile.copyta(status=PARSED)  #copy TRANSLATE to PARSED ta
            #read whole edi-file: read, parse and made into a inmessage-object. Message is represented as a tree (inmessage.root is the root of the tree).
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

            botsglobal.logger.debug(u'start read and parse input file "%s" editype "%s" messagetype "%s".',row['filename'],row['editype'],row['messagetype'])
            for inn in edifile.nextmessage():   #for each message in the edifile:
                #inn.ta_info: parameters from inmessage.edifromfile(), syntax-information and parse-information
                ta_frommes = ta_parsedfile.copyta(status=SPLITUP)    #copy PARSED to SPLITUP ta
                inn.ta_info['idta_fromfile'] = ta_fromfile.idta     #for confirmations in user script; used to give idta of 'confirming message'
                ta_frommes.update(**inn.ta_info)    #update ta-record SLIPTUP with info from message content and/or grammar
                while 1:    #whileloop continues as long as there are alt-translations
                    #************select parameters for translation(script):
                    for tscript,tomessagetype,toeditype in botslib.query(u'''SELECT tscript,tomessagetype,toeditype
                                                FROM    translate
                                                WHERE   frommessagetype = %(frommessagetype)s
                                                AND     fromeditype = %(fromeditype)s
                                                AND     active=%(booll)s
                                                AND     alt=%(alt)s
                                                AND     (frompartner_id IS NULL OR frompartner_id=%(frompartner)s OR frompartner_id in (SELECT to_partner_id
                                                                                                                            FROM partnergroup
                                                                                                                            WHERE from_partner_id=%(frompartner)s ))
                                                AND     (topartner_id IS NULL OR topartner_id=%(topartner)s OR topartner_id in (SELECT to_partner_id
                                                                                                                            FROM partnergroup
                                                                                                                            WHERE from_partner_id=%(topartner)s ))
                                                ORDER BY alt DESC,
                                                         CASE WHEN frompartner_id IS NULL THEN 1 ELSE 0 END, frompartner_id ,
                                                         CASE WHEN topartner_id IS NULL THEN 1 ELSE 0 END, topartner_id ''',
                                                {'frommessagetype':inn.ta_info['messagetype'],
                                                 'fromeditype':inn.ta_info['editype'],
                                                 'alt':inn.ta_info['alt'],
                                                 'frompartner':inn.ta_info['frompartner'],
                                                 'topartner':inn.ta_info['topartner'],
                                                'booll':True}):
                        break   #translation is found; break because only the first one is used - this is what the ORDER BY in the query takes care of
                    else:       #no translation is found in translate table
                        raiseTranslationNotFoundError = True
                        if userscript and hasattr(userscript,'gettranslation'):      #check if user scripting to determine translation
                            tscript,tomessagetype,toeditype = botslib.runscript(userscript,scriptname,'gettranslation',idroute=idroute,message=inn)
                            if tscript is not None:
                                raiseTranslationNotFoundError = False
                        if raiseTranslationNotFoundError:
                            raise botslib.TranslationNotFoundError(_(u'Editype "$editype", messagetype "$messagetype", frompartner "$frompartner", topartner "$topartner", alt "$alt"'),
                                                                        editype=inn.ta_info['editype'],
                                                                        messagetype=inn.ta_info['messagetype'],
                                                                        frompartner=inn.ta_info['frompartner'],
                                                                        topartner=inn.ta_info['topartner'],
                                                                        alt=inn.ta_info['alt'])
                    ta_tomes = ta_frommes.copyta(status=endstatus)  #copy SPLITUP to TRANSLATED ta
                    tofilename = str(ta_tomes.idta)
                    tomessage = outmessage.outmessage_init(messagetype=tomessagetype,editype=toeditype,filename=tofilename,reference=unique('messagecounter'),statust=OK,divtext=tscript)    #make outmessage object
                    #copy ta_info
                    botsglobal.logger.debug(u'script "%s" translates messagetype "%s" to messagetype "%s".',tscript,inn.ta_info['messagetype'],tomessage.ta_info['messagetype'])
                    translationscript,scriptfilename = botslib.botsimport('mappings',inn.ta_info['editype'] + '.' + tscript) #get the mapping-script
                    doalttranslation = botslib.runscript(translationscript,scriptfilename,'main',inn=inn,out=tomessage)
                    botsglobal.logger.debug(u'script "%s" finished.',tscript)
                    if 'topartner' not in tomessage.ta_info:    #tomessage does not contain values from ta......
                        tomessage.ta_info['topartner'] = inn.ta_info['topartner']
                    if tomessage.ta_info['statust'] == DONE:    #if indicated in user script the message should be discarded
                        botsglobal.logger.debug(u'No output file because mapping script explicitly indicated this.')
                        tomessage.ta_info['filename'] = ''
                        tomessage.ta_info['status'] = DISCARD
                    else:
                        botsglobal.logger.debug(u'Start writing output file editype "%s" messagetype "%s".',tomessage.ta_info['editype'],tomessage.ta_info['messagetype'])
                        tomessage.writeall()   #write tomessage (result of translation).
                    #problem is that not all values ta_tomes are know to to_message....
                    #~ print 'tomessage.ta_info',tomessage.ta_info
                    ta_tomes.update(**tomessage.ta_info) #update outmessage transaction with ta_info;
                    #check the value received from the mappingscript to see if another traanslation needs to be done (chained translation)
                    if doalttranslation is None:
                        del tomessage
                        break   #break out of while loop; do no other translation
                    elif isinstance(doalttranslation,dict):
                        #some extended cases; a dict is returned that contains 'instructions'
                        if 'type' not in doalttranslation:
                            raise botslib.BotsError("Mapping script returned dict. This dict does not have a 'type', like in eg: {'type:'out_as_inn', 'alt':'alt-value'}.")
                        if doalttranslation['type'] == u'out_as_inn':
                            if 'alt' not in doalttranslation:
                                raise botslib.BotsError("Mapping script returned dict, type 'out_as_inn'. This dict does not have a 'alt'-value, like in eg: {'type:'out_as_inn', 'alt':'alt-value'}.")
                            inn = tomessage
                            if isinstance(inn,outmessage.fixed):
                                inn.root.stripnode()
                            inn.ta_info['alt'] = doalttranslation['alt']   #get the alt-value for the next chainded translation
                            inn.ta_info.pop('statust')
                    else:
                        del tomessage
                        inn.ta_info['alt'] = doalttranslation   #get the alt-value for the next chainded translation
                #end of while-loop

                #
                #~ print inn.ta_info
                ta_frommes.update(statust=DONE,**inn.ta_info)   #update db. inn.ta_info could be changed by script. Is this useful?
                del inn

        #exceptions file_in-level
        except:
            #~ edifile.handleconfirm(ta_fromfile,error=True)    #only useful if errors are reported in acknowledgement (eg x12 997). Not used now.
            txt = botslib.txtexc()
            ta_parsedfile.failure()
            ta_parsedfile.update(statust=ERROR,errortext=txt)
            botsglobal.logger.debug(u'error in translating input file "%s":\n%s',row['filename'],txt)
        else:
            edifile.handleconfirm(ta_fromfile,error=False)
            ta_fromfile.update(statust=DONE)
            ta_parsedfile.update(statust=DONE,**edifile.confirminfo)
            botsglobal.logger.debug(u'translated input file "%s".',row['filename'])
            del edifile

#*********************************************************************
#*** utily functions for persist: store things in the bots database.
#*** this is intended as a memory stretching across messages.
#*********************************************************************
def persist_add(domein,botskey,value):
    ''' store persistent values in db.
    '''
    content = pickle.dumps(value,0)
    if botsglobal.settings.DATABASE_ENGINE != 'sqlite3' and len(content)>1024:
        raise botslib.PersistError(_(u'Data too long for domein "$domein", botskey "$botskey", value "$value".'),domein=domein,botskey=botskey,value=value)
    try:
        botslib.change(u'''INSERT INTO persist (domein,botskey,content)
                                VALUES   (%(domein)s,%(botskey)s,%(content)s)''',
                                {'domein':domein,'botskey':botskey,'content':content})
    except:
        raise botslib.PersistError(_(u'Failed to add for domein "$domein", botskey "$botskey", value "$value".'),domein=domein,botskey=botskey,value=value)

def persist_update(domein,botskey,value):
    ''' store persistent values in db.
    '''
    content = pickle.dumps(value,0)
    if botsglobal.settings.DATABASE_ENGINE != 'sqlite3' and len(content)>1024:
        raise botslib.PersistError(_(u'Data too long for domein "$domein", botskey "$botskey", value "$value".'),domein=domein,botskey=botskey,value=value)
    botslib.change(u'''UPDATE persist
                          SET content=%(content)s
                        WHERE domein=%(domein)s
                          AND botskey=%(botskey)s''',
                            {'domein':domein,'botskey':botskey,'content':content})

def persist_add_update(domein,botskey,value):
    # add the record, or update it if already there.
    try:
        persist_add(domein,botskey,value)
    except:
        persist_update(domein,botskey,value)

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

#*********************************************************************
#*** utily functions for codeconversion
#***   2 types: codeconversion via database tabel ccode, and via file.
#*** 20111116: codeconversion via file is depreciated, will disappear.
#*********************************************************************
#***code conversion via database tabel ccode
def ccode(ccodeid,leftcode,field='rightcode'):
    ''' converts code using a db-table.
        converted value is returned, exception if not there.
    '''
    for row in botslib.query(u'''SELECT ''' +field+ '''
                                FROM    ccode
                                WHERE   ccodeid_id = %(ccodeid)s
                                AND     leftcode = %(leftcode)s''',
                                {'ccodeid':ccodeid,
                                 'leftcode':leftcode,
                                }):
        return row[field]
    raise botslib.CodeConversionError(_(u'Value "$value" not in code-conversion, user table "$table".'),value=leftcode,table=ccodeid)
codetconversion = ccode

def safe_ccode(ccodeid,leftcode,field='rightcode'):
    ''' converts code using a db-table.
        converted value is returned, if not there return orginal code
    '''
    try:
        return ccode(ccodeid,leftcode,field)
    except botslib.CodeConversionError:
        return leftcode
safecodetconversion = safe_ccode

def reverse_ccode(ccodeid,rightcode,field='leftcode'):
    ''' as ccode but reversed lookup.'''
    for row in botslib.query(u'''SELECT ''' +field+ '''
                                FROM    ccode
                                WHERE   ccodeid_id = %(ccodeid)s
                                AND     rightcode = %(rightcode)s''',
                                {'ccodeid':ccodeid,
                                 'rightcode':rightcode,
                                }):
        return row[field]
    raise botslib.CodeConversionError(_(u'Value "$value" not in code-conversion, user table "$table".'),value=rightcode,table=ccodeid)
rcodetconversion = reverse_ccode

def safe_reverse_ccode(ccodeid,rightcode,field='leftcode'):
    ''' as safe_ccode but reversed lookup.'''
    try:
        return reverse_ccode(ccodeid,rightcode,field)
    except botslib.CodeConversionError:
        return rightcode
safercodetconversion = safe_reverse_ccode

def getcodeset(ccodeid,leftcode,field='rightcode'):
    ''' Get a code set
    '''
    return list(botslib.query(u'''SELECT ''' +field+ '''
                                FROM    ccode
                                WHERE   ccodeid_id = %(ccodeid)s
                                AND     leftcode = %(leftcode)s''',
                                {'ccodeid':ccodeid,
                                 'leftcode':leftcode,
                                }))

#***code conversion via file. 20111116: depreciated
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
        raise botslib.CodeConversionError(_(u'Value "$value" not in file for codeconversion "$filename".'),value=value,filename=filename)

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
        raise botslib.CodeConversionError(_(u'Value "$value" not in file for reversed codeconversion "$filename".'),value=value,filename=filename)

#*********************************************************************
#*** utily functions for calculating/generating/checking EAN/GTIN/GLN
#*********************************************************************
def calceancheckdigit(ean):
    ''' input: EAN without checkdigit; returns the checkdigit'''
    try:
        if not ean.isdigit():
            raise botslib.EanError(_(u'GTIN "$ean" should be string with only numericals'),ean=ean)
    except AttributeError:
        raise botslib.EanError(_(u'GTIN "$ean" should be string, but is a "$type"'),ean=ean,type=type(ean))
    sum1 = sum([int(x)*3 for x in ean[-1::-2]]) + sum([int(x) for x in ean[-2::-2]])
    return str((1000-sum1)%10)

def calceancheckdigit2(ean):
    ''' just for fun: slightly different algoritm for calculating the ean checkdigit. same results; is 10% faster.
    '''
    sum1 = 0
    factor = 3
    for i in ean[-1::-1]:
        sum1 += int(i) * factor
        factor = 4 - factor         #factor flip-flops between 3 and 1...
    return str(((1000 - sum1) % 10))

def checkean(ean):
    ''' input: EAN; returns: True (valid EAN) of False (EAN not valid)'''
    return (ean[-1] == calceancheckdigit(ean[:-1]))

def addeancheckdigit(ean):
    ''' input: EAN without checkdigit; returns EAN with checkdigit'''
    return ean+calceancheckdigit(ean)

#*********************************************************************
#*** div utily functions for mappings
#*********************************************************************
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
    ''' for edifact: return right format code for the date. '''
    if not date:
        return None
    if len(date) == 8:
        return '102'
    if len(date) == 12:
        return '203'
    if len(date) == 16:
        return '718'
    return None

def datemask(value,frommask,tomask):
    ''' value is formatted according as in frommask;
        returned is the value formatted according to tomask.
        example: datemask('12/31/2012','MM/DD/YYYY','YYYYMMDD') returns '20121231'
    '''
    if not value:
        return value
    convdict = collections.defaultdict(list)
    for key,val in zip(frommask,value):
        convdict[key].append(val)
    #convdict contains for example:  {'Y': [u'2', u'0', u'1', u'2'], 'M': [u'1', u'2'], 'D': [u'3', u'1'], '/': [u'/', u'/']}
    terug = ''
    try:
        # alternative implementation: return ''.join([convdict.get(c,[c]).pop(0) for c in tomask])     #very short, but not faster....
        for char in tomask:
            terug += convdict.get(char,[char]).pop(0)     #for this character, lookup value in convdict (a list). pop(0) this list: get first member of list, and drop it. If char not in convdict as key, use char itself.
    except:
        raise botslib.BotsError(_(u'Error in function datamask("$value", "$frommask", "$tomask").'),value=value,frommask=frommask,tomask=tomask)
    return terug

def truncate(maxpos,value):
    if value:
        return value[:maxpos]
    else:
        return value
