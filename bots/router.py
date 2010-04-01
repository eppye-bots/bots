#bots-modules
import communication
import envelope
import transform
import botslib
import botsglobal
from botsconfig import *


@botslib.log_session
def prepareretransmit():
    ''' check if user indicated a retrans/resend.
        If so, prepare the retransmittable files and return retransmit=True '''
    retransmit = False
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
    #for resend
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
def routedispatcher(routestorun,type):
    ''' communication.run all route(s) for this type (retry, retransmit, new)'''
    #for retransmit: check if there is something to retransmit; this limits the nr of reports/runs
    if type == 'retransmit' and not prepareretransmit():
        return False
    botslib.setlastrun()
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
                                                 frompartner_tochannel_id as frompartner_tochannel,
                                                 topartner_tochannel_id as topartner_tochannel,
                                                 testindicator,
                                                 translateind
                                        FROM routes
                                        WHERE idroute=%(idroute)s
                                        AND   active=%(active)s
                                        ORDER BY seq''',
                                        {'idroute':route,'active':True}):
            botslib.setrouteid(routedict['idroute'])
            botsglobal.logger.info(u'running route %s %s',routedict['idroute'],routedict['seq'])
            foundroute=True
            router(routedict)
            botslib.setrouteid('')
            botsglobal.logger.debug(u'finished route %s %s',routedict['idroute'],routedict['seq'])
        if not foundroute:
            botsglobal.logger.warning(u'there is no (active) route "%s".',route)
    return True


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
        raise botslib.ScriptError(u'Route "$route" is empty: no script, not enough parameters.',route=routedict['idroute'])

    
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
        botslib.addinfo(change=toset,where={'status':FILEIN,'fromchannel':routedict['fromchannel'],'idroute':routedict['idroute']})
        transform.splitmailbag(idroute=routedict['idroute'])
        transform.translate(idroute=routedict['idroute'])
        botslib.tryrunscript(userscript,scriptname,'posttranslation',routedict=routedict)
        
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
        if routedict['frompartner_tochannel']:   #use frompartner_tochannel in where-clause of query (partner/group dependent outchannel
            towhere['frompartner_tochannel']=routedict['frompartner_tochannel']
            wherestring += ''' AND (frompartner=%(frompartner_tochannel)s 
                                    OR frompartner in (SELECT idpartner_id 
                                                        FROM partnergroup
                                                        WHERE idpartnergroup_id=%(frompartner_tochannel_id)s ))'''
        if routedict['topartner_tochannel']:   #use topartner_tochannel in where-clause of query (partner/group dependent outchannel
            towhere['topartner_tochannel']=routedict['topartner_tochannel']
            wherestring += ''' AND (topartner_id=%(topartner_tochannel)s 
                                    OR topartner_id in (SELECT idpartner 
                                                        FROM partnergroup
                                                        WHERE idpartnergroup=%(topartner_tochannel)s ))'''
        toset={'tochannel':routedict['tochannel'],'status':FILEOUT}
        botslib.addinfocore(change=toset,where=towhere,wherestring=wherestring)
        
        botslib.tryrunscript(userscript,scriptname,'preoutcommunication',routedict=routedict)
        communication.run(idchannel=routedict['tochannel'],idroute=routedict['idroute'])    #communication.run outcommunication
        botslib.tryrunscript(userscript,scriptname,'postoutcommunication',routedict=routedict)
    
    botslib.tryrunscript(userscript,scriptname,'end',routedict=routedict)
        
