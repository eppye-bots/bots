''' module contains functions to be called from user scripts. '''
import os
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
def translate(startstatus=FILEIN,endstatus=TRANSLATED,idroute=''):
    ''' main translation loop.
        get edifiles to be translated, than:
        -   read, lex, parse, make tree of nodes.
        -   split up files into messages (using 'nextmessage' of grammar)
        -   get mappingscript, start mappingscript.
        -   write the results of translation (no enveloping yet)
        status: FILEIN--PARSED-<SPLITUP--TRANSLATED
    '''
    try:    #see if there is a userscript that can determine the translation
        userscript,scriptname = botslib.botsimport('mappings','translation')
    except ImportError:       #userscript is not there; other errors like syntax errors are not catched
        userscript = scriptname = None
    #select edifiles to translate
    for row in botslib.query(u'''SELECT idta,frompartner,topartner,filename,messagetype,testindicator,editype,charset,alt,fromchannel,rsrv2
                                FROM ta
                                WHERE idta>%(rootidta)s
                                AND status=%(status)s
                                AND statust=%(statust)s
                                AND idroute=%(idroute)s ''',
                                {'status':startstatus,'statust':OK,'idroute':idroute,'rootidta':botslib.get_minta4query()}):
        try:
            if row['rsrv2'] > botsglobal.ini.getint('settings','maxfilesizeincoming',5000000):
                raise botslib.InMessageError(_(u'File size of "%s"; "maxfilesizeincoming" is set to "%s" (in bots.ini).'),row['rsrv2'],botsglobal.ini.getint('settings','maxfilesizeincoming',5000000))
            ta_fromfile = botslib.OldTransaction(row['idta'])
            ta_parsed = ta_fromfile.copyta(status=PARSED)       #make PARSED ta
            botsglobal.logger.debug(_(u'start translating file "%s" editype "%s" messagetype "%s".'),row['filename'],row['editype'],row['messagetype'])
            #read whole edi-file: read, parse and made into a inmessage-object. Message is represented as a tree (inmessage.root is the root of the tree).
            edifile = inmessage.parse_edi_file(frompartner=row['frompartner'],
                                                topartner=row['topartner'],
                                                filename=row['filename'],
                                                messagetype=row['messagetype'],
                                                testindicator=row['testindicator'],
                                                editype=row['editype'],
                                                charset=row['charset'],
                                                alt=row['alt'],
                                                fromchannel=row['fromchannel'],
                                                idroute=idroute)
            #if no exception: infile has been lexed and parsed OK.
            #edifile.ta_info contains info: QUERIES, charset etc
            for inn_splitup in edifile.nextmessage():   #splitup messages in parsed edifile
                try:
                    ta_splitup = ta_parsed.copyta(status=SPLITUP,**inn_splitup.ta_info)    #copy PARSED to SPLITUP ta
                    #inn_splitup.ta_info: parameters from inmessage.parse_edi_file(), syntax-information and parse-information
                    inn_splitup.ta_info['idta_fromfile'] = ta_fromfile.idta     #for confirmations in userscript; used to give idta of 'confirming message'
                    while 1:    #continue as long as there are (alt-)translations
                        #***lookup the translation: mappingscript, tomessagetype, toeditype**********************
                        for row2 in botslib.query(u'''SELECT tscript,tomessagetype,toeditype
                                                    FROM translate
                                                    WHERE frommessagetype = %(frommessagetype)s
                                                    AND fromeditype = %(fromeditype)s
                                                    AND active=%(booll)s
                                                    AND alt=%(alt)s
                                                    AND (frompartner_id IS NULL OR frompartner_id=%(frompartner)s OR frompartner_id in (SELECT to_partner_id
                                                                                                                                            FROM partnergroup
                                                                                                                                            WHERE from_partner_id=%(frompartner)s ))
                                                    AND (topartner_id IS NULL OR topartner_id=%(topartner)s OR topartner_id in (SELECT to_partner_id
                                                                                                                                    FROM partnergroup
                                                                                                                                    WHERE from_partner_id=%(topartner)s ))
                                                    ORDER BY alt DESC,
                                                             CASE WHEN frompartner_id IS NULL THEN 1 ELSE 0 END, frompartner_id ,
                                                             CASE WHEN topartner_id IS NULL THEN 1 ELSE 0 END, topartner_id ''',
                                                    {'frommessagetype':inn_splitup.ta_info['messagetype'],
                                                     'fromeditype':inn_splitup.ta_info['editype'],
                                                     'alt':inn_splitup.ta_info['alt'],
                                                     'frompartner':inn_splitup.ta_info['frompartner'],
                                                     'topartner':inn_splitup.ta_info['topartner'],
                                                    'booll':True}):
                            tscript = row2['tscript']
                            toeditype = row2['toeditype']
                            tomessagetype = row2['tomessagetype']
                            break   #translation is found; break because only the first one is used - this is what the ORDER BY in the query takes care of
                        else:       #no translation found in translate table; check if can find translation via user script
                            raiseTranslationNotFoundError = True
                            #check if user scripting can determine translation
                            if userscript and hasattr(userscript,'gettranslation'):      
                                tscript,toeditype,tomessagetype = botslib.runscript(userscript,scriptname,'gettranslation',idroute=idroute,message=inn_splitup)
                                if tscript is not None:
                                    raiseTranslationNotFoundError = False
                            if raiseTranslationNotFoundError:
                                raise botslib.TranslationNotFoundError(_(u'Editype "$editype", messagetype "$messagetype", frompartner "$frompartner", topartner "$topartner", alt "$alt"'),
                                                                            editype=inn_splitup.ta_info['editype'],
                                                                            messagetype=inn_splitup.ta_info['messagetype'],
                                                                            frompartner=inn_splitup.ta_info['frompartner'],
                                                                            topartner=inn_splitup.ta_info['topartner'],
                                                                            alt=inn_splitup.ta_info['alt'])
                        ta_translated = ta_splitup.copyta(status=endstatus)     #make ta for translated message
                        filename_translated = str(ta_translated.idta)
                        out_translated = outmessage.outmessage_init(messagetype=tomessagetype,editype=toeditype,filename=filename_translated,reference=unique('messagecounter'),statust=OK,divtext=tscript)    #make outmessage object
                        botsglobal.logger.debug(_(u'Mappingscript "%s" translates messagetype "%s" to messagetype "%s".'),tscript,inn_splitup.ta_info['messagetype'],out_translated.ta_info['messagetype'])
                        translationscript,scriptfilename = botslib.botsimport('mappings',inn_splitup.ta_info['editype'] + '.' + tscript) #get the mappingscript
                        doalttranslation = botslib.runscript(translationscript,scriptfilename,'main',inn=inn_splitup,out=out_translated)
                        botsglobal.logger.debug(_(u'Mappingscript "%s" finished.'),tscript)
                        if 'topartner' not in out_translated.ta_info:    #out_translated does not contain values from ta......
                            out_translated.ta_info['topartner'] = inn_splitup.ta_info['topartner']
                        if out_translated.ta_info['statust'] == DONE:    #if indicated in mappingscript the message should be discarded
                            botsglobal.logger.debug(_(u'No output file because mappingscript explicitly indicated this.'))
                            out_translated.ta_info['filename'] = ''
                            out_translated.ta_info['status'] = DISCARD
                        else:
                            botsglobal.logger.debug(_(u'Start writing output file editype "%s" messagetype "%s".'),out_translated.ta_info['editype'],out_translated.ta_info['messagetype'])
                            out_translated.writeall()   #write result of translation.
                            out_translated.ta_info['rsrv2'] = os.path.getsize(botslib.abspathdata(out_translated.ta_info['filename']))  #get filesize
                        #problem is that not all values ta_translated are know to to_message....
                        #~ print 'out_translated.ta_info',out_translated.ta_info
                        ta_translated.update(**out_translated.ta_info)  #update outmessage transaction with ta_info; statust = OK
                        #check the value received from the mappingscript to see if another translation needs to be done (chained translation)
                        if doalttranslation is None:
                            del out_translated
                            break   #break out of while loop; do no other translation
                        elif isinstance(doalttranslation,dict):
                            #some extended cases; a dict is returned that contains 'instructions'
                            if 'type' not in doalttranslation:
                                raise botslib.BotsError(_(u"Mappingscript returned dict. This dict does not have a 'type', like in eg: {'type:'out_as_inn', 'alt':'alt-value'}."))
                            if doalttranslation['type'] == u'out_as_inn':
                                if 'alt' not in doalttranslation:
                                    raise botslib.BotsError(_("Mappingscript returned dict, type 'out_as_inn'. This dict does not have a 'alt'-value, like in eg: {'type:'out_as_inn', 'alt':'alt-value'}."))
                                inn_splitup = out_translated
                                if isinstance(inn_splitup,outmessage.fixed):
                                    inn_splitup.root.stripnode()
                                inn_splitup.ta_info['alt'] = doalttranslation['alt']   #get the alt-value for the next chained translation
                                inn_splitup.ta_info.pop('statust')
                        else:
                            del out_translated
                            inn_splitup.ta_info['alt'] = doalttranslation   #get the alt-value for the next chained translation
                    #end of while-loop (trans**********************************************************************************
                #exceptions file_out-level: exception in mappingscript or writing of out-file
                except:
                    #2 modes: either every error leads to skipping of  whole infile (old  mode) or errors in mappingscript/outfile only affect that branche 
                    if botsglobal.ini.getboolean('settings','oldmessageerrors',False):
                        raise
                    txt = botslib.txtexc()
                    ta_splitup.update(statust=ERROR,errortext=txt,**inn_splitup.ta_info)   #update db. inn_splitup.ta_info could be changed by mappingscript. Is this useful?
                    ta_splitup.deletechildren()
                else:
                    ta_splitup.update(statust=DONE, **inn_splitup.ta_info)   #update db. inn_splitup.ta_info could be changed by mappingscript. Is this useful?
                    

        #exceptions file_in-level (file not OK according to grammar)
        except:
            txt = botslib.txtexc()
            ta_parsed.update(statust=ERROR,errortext=txt)
            ta_parsed.deletechildren()
            botsglobal.logger.debug(u'error in translating input file "%s":\n%s',row['filename'],txt)
        else:
            edifile.handleconfirm(ta_fromfile,error=False)
            ta_parsed.update(statust=DONE,rsrv2=row['rsrv2'],**edifile.ta_info)
            botsglobal.logger.debug(_(u'translated input file "%s".'),row['filename'])
        finally:
            ta_fromfile.update(statust=DONE)

#*********************************************************************
#*** utily functions for persist: store things in the bots database.
#*** this is intended as a memory stretching across messages.
#*********************************************************************
def persist_add(domein,botskey,value):
    ''' store persistent values in db.
    '''
    content = pickle.dumps(value)
    try:
        botslib.changeq(u''' INSERT INTO persist (domein,botskey,content)
                            VALUES   (%(domein)s,%(botskey)s,%(content)s)''',
                            {'domein':domein,'botskey':botskey,'content':content})
    except:
        raise botslib.PersistError(_(u'Failed to add for domein "$domein", botskey "$botskey", value "$value".'),domein=domein,botskey=botskey,value=value)

def persist_update(domein,botskey,value):
    ''' store persistent values in db.
    '''
    content = pickle.dumps(value)
    botslib.changeq(u''' UPDATE persist
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
    botslib.changeq(u''' DELETE FROM persist
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
                                FROM ccode
                                WHERE ccodeid_id = %(ccodeid)s
                                AND leftcode = %(leftcode)s''',
                                {'ccodeid':ccodeid,'leftcode':leftcode}):
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
                                FROM ccode
                                WHERE ccodeid_id = %(ccodeid)s
                                AND rightcode = %(rightcode)s''',
                                {'ccodeid':ccodeid,'rightcode':rightcode}):
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
    ''' Returns a list of all 'field' values in ccode with right ccodeid and leftcode.
    '''
    terug = []
    for row in botslib.query(u'''SELECT ''' +field+ '''
                                FROM ccode
                                WHERE ccodeid_id = %(ccodeid)s
                                AND leftcode = %(leftcode)s''',
                                {'ccodeid':ccodeid,'leftcode':leftcode}):
        terug.append(row[field])
    return  terug

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

def unique_runcounter(domain):
    ''' generate unique counter within range domain during one run of bots.
        if domain not used before, initialize as 1; for each subsequent call this is incremented with 1
        usage example:
        unh_reference = unique_runcounter(<messagetype>_<topartner>)
    '''
    if hasattr(botsglobal,domain):
        botsglobal.domain += 1
    else:
        botsglobal.domain = 1
    return botsglobal.domain
