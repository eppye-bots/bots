import sys
from django.utils.translation import ugettext as _
#bots-modules
import communication
import envelope
import transform
import botslib
import botsglobal
from botsconfig import *

@botslib.log_session
def prepareretransmit():
    ''' prepare the retransmittable files. Return: indication if files should be retransmitted.'''
    retransmit = False  #indicate retransmit
    #for rereceive
    for row in botslib.query('''SELECT idta,reportidta
                                FROM  filereport
                                WHERE retransmit=%(retransmit)s ''',
                                {'retransmit':True}):
        retransmit = True 
        botslib.change('''UPDATE filereport
                           SET retransmit=%(retransmit)s
                           WHERE idta=%(idta)s
                           AND   reportidta=%(reportidta)s ''',
                            {'idta':row['idta'],'reportidta':row['reportidta'],'retransmit':False})
        for row2 in botslib.query('''SELECT idta
                                    FROM  ta
                                    WHERE parent=%(parent)s
                                    AND   status=%(status)s''',
                                    {'parent':row['idta'],
                                    'status':RAWIN}):
            ta_rereceive = botslib.OldTransaction(row2['idta'])
            ta_externin = ta_rereceive.copyta(status=EXTERNIN,statust=DONE,parent=0) #inject; status is DONE so this ta is not used further
            ta_raw = ta_externin.copyta(status=RAWIN,statust=OK)  #reinjected file is ready as new input
    #for resend; this one is slow. Can be improved by having a seperate list of idta to resend
    for row in botslib.query('''SELECT idta,parent
                                FROM  ta
                                WHERE retransmit=%(retransmit)s
                                AND   status=%(status)s''',
                                {'retransmit':True,
                                'status':EXTERNOUT}):
        retransmit = True
        ta_outgoing = botslib.OldTransaction(row['idta'])
        ta_outgoing.update(retransmit=False)     #is reinjected; set retransmit back to False
        ta_resend = botslib.OldTransaction(row['parent'])  #parent ta with status RAWOUT; this is where the outgoing file is kept
        ta_externin = ta_resend.copyta(status=EXTERNIN,statust=DONE,parent=0) #inject; status is DONE so this ta is not used further
        ta_raw = ta_externin.copyta(status=RAWOUT,statust=OK)  #reinjected file is ready as new input
    return retransmit


@botslib.log_session
def preparerecommunication():
    #for each out-communication process that went wrong:
    retransmit = False  #indicate retransmit
    for row in botslib.query('''SELECT idta,tochannel
                                FROM  ta
                                WHERE statust!=%(statust)s
                                AND status=%(status)s
                                AND retransmit=%(retransmit)s ''',
                                {'status':PROCESS,'retransmit':True,'statust':DONE}):
        run_outgoing = botslib.OldTransaction(row['idta'])
        run_outgoing.update(retransmit=False)     #set retransmit back to False
        #get rootidta of run where communication failed
        for row2 in botslib.query('''SELECT max(idta) as rootidta
                                    FROM  ta
                                    WHERE script=%(script)s
                                    AND idta<%(thisidta)s ''',
                                    {'script':0,'thisidta':row['idta']}):
            rootidta = row2['rootidta']
        #get endidta of run where communication failed
        for row3 in botslib.query('''SELECT min(idta) as endidta
                            FROM  ta
                            WHERE script=%(script)s
                            AND idta>%(thisidta)s ''',
                            {'script':0,'thisidta':row['idta']}):
            endidta = row3['endidta']
        if not endidta:
            endidta = sys.maxint - 1
        #reinject
        for row4 in botslib.query('''SELECT idta
                                    FROM  ta
                                    WHERE idta<%(endidta)s
                                    AND idta>%(rootidta)s 
                                    AND   status=%(status)s 
                                    AND   statust=%(statust)s
                                    AND   tochannel=%(tochannel)s ''',
                                    {'statust':OK,'status':RAWOUT,'rootidta':rootidta,'endidta':endidta,'tochannel':row['tochannel']}):
            retransmit = True
            ta_outgoing = botslib.OldTransaction(row4['idta'])
            ta_outgoing_copy = ta_outgoing.copyta(status=RAWOUT,statust=OK)
            ta_outgoing.update(statust=DONE)
    return retransmit


@botslib.log_session
def routedispatcher(routestorun,type=None):
    ''' run all route(s). '''
    if type == '--retransmit':
        if not prepareretransmit():
            return 0
    elif type == '--retrycommunication':
        if not preparerecommunication():
            return 0
    stuff2evaluate = botslib.getlastrun()
    botslib.set_minta4query()
    for route in routestorun:
        foundroute=False
        for routedict in botslib.query('''SELECT idroute     ,
                                                 fromchannel_id as fromchannel,
                                                 tochannel_id as tochannel,
                                                 fromeditype,
                                                 frommessagetype,
                                                 alt,
                                                 frompartner_id as frompartner,
                                                 topartner_id as topartner,
                                                 toeditype,
                                                 tomessagetype,
                                                 seq,
                                                 frompartner_tochannel_id,
                                                 topartner_tochannel_id,
                                                 testindicator,
                                                 translateind,
                                                 defer
                                        FROM routes
                                        WHERE idroute=%(idroute)s
                                        AND   active=%(active)s
                                        ORDER BY seq''',
                                        {'idroute':route,'active':True}):
            botsglobal.logger.info(_(u'running route %(idroute)s %(seq)s'),{'idroute':routedict['idroute'],'seq':routedict['seq']})
            botslib.setrouteid(routedict['idroute'])
            foundroute=True
            router(routedict)
            botslib.setrouteid('')
            botsglobal.logger.debug(u'finished route %s %s',routedict['idroute'],routedict['seq'])
        if not foundroute:
            botsglobal.logger.warning(_(u'there is no (active) route "%s".'),route)
    return stuff2evaluate


@botslib.log_session
def router(routedict):
    ''' communication.run one route. variants:
        -   a route can be just script; 
        -   a route can do only incoming
        -   a route can do only outgoing
        -   a route can do both incoming and outgoing
        -   at several points functions from a route script are called - if function is in route script
    '''
    #is there a user route script?
    try:
        botsglobal.logger.debug(u'(try) to read user routescript route "%s".',routedict['idroute'])
        userscript,scriptname = botslib.botsimport('routescripts',routedict['idroute'])
    except ImportError: #other errors, eg syntax errors are just passed
        userscript = scriptname = None
        
    #if user route script has function 'main': communication.run 'main' (and do nothing else)
    if botslib.tryrunscript(userscript,scriptname,'main',routedict=routedict):
        return  #so: if function ' main' : communication.run only the routescript, nothing else.
    if not (userscript or routedict['fromchannel'] or routedict['tochannel'] or routedict['translateind']): 
        raise botslib.ScriptError(_(u'Route "$route" is empty: no script, not enough parameters.'),route=routedict['idroute'])

    
    botslib.tryrunscript(userscript,scriptname,'start',routedict=routedict)
    
    #communication.run incoming channel
    if routedict['fromchannel']:     #do incoming part of route: in-communication; set ready for translation; translate
        botslib.tryrunscript(userscript,scriptname,'preincommunication',routedict=routedict)
        communication.run(idchannel=routedict['fromchannel'],idroute=routedict['idroute'])  #communication.run incommunication
        #add attributes from route to the received files
        where={'status':FILEIN,'fromchannel':routedict['fromchannel'],'idroute':routedict['idroute']}
        change={'editype':routedict['fromeditype'],'messagetype':routedict['frommessagetype'],'frompartner':routedict['frompartner'],'topartner':routedict['topartner'],'alt':routedict['alt']}
        botslib.updateinfo(change=change,where=where)
            
        #all received files have status FILEIN
        botslib.tryrunscript(userscript,scriptname,'postincommunication',routedict=routedict)
    
    #communication.run translation
    if routedict['translateind']:
        #processes files with status FILEIN
        botslib.tryrunscript(userscript,scriptname,'pretranslation',routedict=routedict)
        if routedict['fromeditype'] == 'mailbag':
            toset = {'status':MAILBAG}
        else:
            toset = {'status':TRANSLATE}
        #~ botslib.addinfo(change=toset,where={'status':FILEIN,'fromchannel':routedict['fromchannel'],'idroute':routedict['idroute']})
        botslib.addinfo(change=toset,where={'status':FILEIN,'idroute':routedict['idroute']})
        transform.splitmailbag(idroute=routedict['idroute'])
        transform.translate(idroute=routedict['idroute'])
        botslib.tryrunscript(userscript,scriptname,'posttranslation',routedict=routedict)
    #~ import time
    #~ time.sleep(5)
        
    #merge messags & communication.run outgoing channel
    if routedict['tochannel']:   #do outgoing part of route
        botslib.tryrunscript(userscript,scriptname,'premerge',routedict=routedict)
        envelope.mergemessages(idroute=routedict['idroute'])
        botslib.tryrunscript(userscript,scriptname,'postmerge',routedict=routedict)
            
        #communication.run outgoing channel
        #build for query: towhere (dict) and wherestring  
        towhere=dict(status=MERGED,
                    idroute=routedict['idroute'],
                    editype=routedict['toeditype'],
                    messagetype=routedict['tomessagetype'],
                    testindicator=routedict['testindicator'])
        towhere=dict([(key, value) for (key, value) in towhere.iteritems() if value])   #remove nul-values from dict
        wherestring = ' AND '.join([key+'=%('+key+')s' for key in towhere])
        if routedict['frompartner_tochannel_id']:   #use frompartner_tochannel in where-clause of query (partner/group dependent outchannel
            towhere['frompartner_tochannel_id']=routedict['frompartner_tochannel_id']
            wherestring += ''' AND (frompartner=%(frompartner_tochannel_id)s 
                                    OR frompartner in (SELECT from_partner_id 
                                                        FROM partnergroup
                                                        WHERE to_partner_id =%(frompartner_tochannel_id)s ))'''
        if routedict['topartner_tochannel_id']:   #use topartner_tochannel in where-clause of query (partner/group dependent outchannel
            towhere['topartner_tochannel_id']=routedict['topartner_tochannel_id']
            wherestring += ''' AND (topartner=%(topartner_tochannel_id)s 
                                    OR topartner in (SELECT from_partner_id 
                                                        FROM partnergroup
                                                        WHERE to_partner_id=%(topartner_tochannel_id)s ))'''
        toset={'tochannel':routedict['tochannel'],'status':FILEOUT}
        botslib.addinfocore(change=toset,where=towhere,wherestring=wherestring)
        
        if not routedict['defer']:   #do outgoing part of route
            botslib.tryrunscript(userscript,scriptname,'preoutcommunication',routedict=routedict)
            communication.run(idchannel=routedict['tochannel'],idroute=routedict['idroute'])    #communication.run outcommunication
            botslib.tryrunscript(userscript,scriptname,'postoutcommunication',routedict=routedict)
    
    botslib.tryrunscript(userscript,scriptname,'end',routedict=routedict)
