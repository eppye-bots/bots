from django.utils.translation import ugettext as _
#bots-modules
from botsconfig import *
import automaticmaintenance
import botslib
import botsglobal
import communication
import envelope
import preprocess
import transform

@botslib.log_session
def rundispatcher(command,routestorun):
    classtocall = globals()[command]           #get the route class from this module
    myrun = classtocall(command,routestorun)
    return myrun.run()

class new(object):
    #important variables in run:
    #-  root_idta of this run
    #-  minta4query: minimum ta for queries: all database queries use this to limit the number of ta's to query.
    #                for most Run-classes this is equal to root_idta_of_run, excpet for crashrecovery
    def __init__(self,command,routestorun):
        self.routestorun = routestorun
        self.command = command
        self.rootidta_of_current_run = botslib._Transaction.processlist[1]
        
    def run(self):
        self.set_minta4query()
        if not self.prepare():
            botsglobal.logger.info(_(u'Nothing to do in run.'))
            return 0
        for route in self.routestorun:
            foundroute = False
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
                                                     defer,
                                                     rsrv1,
                                                     rsrv2
                                            FROM routes
                                            WHERE idroute=%(idroute)s
                                            AND active=%(active)s
                                            ORDER BY seq''',
                                            {'idroute':route,'active':True}):
                botsglobal.logger.info(_(u'running route %(idroute)s %(seq)s'),{'idroute':routedict['idroute'],'seq':routedict['seq']})
                botslib.setrouteid(routedict['idroute'])
                foundroute = True
                self.router(routedict)
                botslib.setrouteid('')
                botsglobal.logger.debug(u'finished route %s %s',routedict['idroute'],routedict['seq'])
            if not foundroute:
                botsglobal.logger.warning(_(u'there is no (active) route "%s".'),route)
        try:
            return automaticmaintenance.evaluate(self.command,botslib.get_minta4query())
        except:
            botsglobal.logger.exception(_(u'Error in automatic maintenance.'))
            return 1
        
    def prepare(self):
        return True
        
    @botslib.log_session
    def router(self,routedict):
        ''' communication.run one route. variants:
            -   a route can be a userscript;
            -   a route can do only incoming
            -   a route can do only outgoing
            -   a route can do both incoming and outgoing
            -   at several points functions from a routescript are called - if function is in routescript
        '''
        #is there a user routescript?
        try:
            userscript,scriptname = botslib.botsimport('routescripts',routedict['idroute'])
        except ImportError:      #routescript is not there; other errors like syntax errors are not catched
            userscript = scriptname = None

        #if routescript has function 'main': communication.run 'main' (and do nothing else)
        if botslib.tryrunscript(userscript,scriptname,'main',routedict=routedict):
            return  #so: if function ' main' : communication.run only the routescript, nothing else.
        if not (userscript or routedict['fromchannel'] or routedict['tochannel'] or routedict['translateind']):
            raise botslib.ScriptError(_(u'Route "$route" is empty: no routescript, not enough parameters.'),route=routedict['idroute'])

        botslib.tryrunscript(userscript,scriptname,'start',routedict=routedict)

        #communication.run incoming channel
        if routedict['fromchannel']:     #do incoming part of route: in-communication;
            botslib.tryrunscript(userscript,scriptname,'preincommunication',routedict=routedict)
            communication.run(idchannel=routedict['fromchannel'],command=self.command,idroute=routedict['idroute'])  #communication.run incommunication
            #add attributes from route to the received files
            where = {'status':FILEIN,'fromchannel':routedict['fromchannel'],'idroute':routedict['idroute']}
            change = {'editype':routedict['fromeditype'],'messagetype':routedict['frommessagetype'],'frompartner':routedict['frompartner'],'topartner':routedict['topartner'],'alt':routedict['alt']}
            botslib.updateinfo(change=change,where=where)
            #all received files have status FILEIN
            botslib.tryrunscript(userscript,scriptname,'postincommunication',routedict=routedict)
            #some preprocessing if needed
            if routedict['rsrv1'] == 'in_always':               #unzip incoming (non-zipped gives error).
                preprocess.preprocess(routedict=routedict,function=preprocess.botsunzip,pass_non_zip=False)
            elif routedict['rsrv1'] == 'in_test':               #unzip incoming if zipped.
                preprocess.preprocess(routedict=routedict,function=preprocess.botsunzip,pass_non_zip=True)
            if routedict['fromeditype'] in ['mailbag','edifact','x12','tradacoms']:               #mailbag for the route.
                preprocess.preprocess(routedict=routedict,function=preprocess.mailbag)

        #communication.run translation
        if int(routedict['translateind']) == 1:
            botslib.tryrunscript(userscript,scriptname,'pretranslation',routedict=routedict)
            transform.translate(idroute=routedict['idroute'])
            botslib.tryrunscript(userscript,scriptname,'posttranslation',routedict=routedict)
        elif routedict['translateind'] == 2:        #pass-through: pickup the incoming files and mark these as MERGED (==translation is finished)
            botslib.addinfo(change={'status':MERGED},where={'status':FILEIN,'idroute':routedict['idroute']})
        #NOTE: routedict['translateind'] == 0 than nothing will happen with the files in this route. 

        #merge messages & communication.run outgoing channel
        if routedict['tochannel']:   #do outgoing part of route
            botslib.tryrunscript(userscript,scriptname,'premerge',routedict=routedict)
            envelope.mergemessages(idroute=routedict['idroute'])
            botslib.tryrunscript(userscript,scriptname,'postmerge',routedict=routedict)

            #communication.run outgoing channel
            #build for query: towhere (dict) and wherestring
            towhere = dict(status=MERGED,
                        idroute=routedict['idroute'],
                        editype=routedict['toeditype'],
                        messagetype=routedict['tomessagetype'],
                        testindicator=routedict['testindicator'])
            towhere = dict([(key, value) for (key, value) in towhere.iteritems() if value])   #remove nul-values from dict
            wherestring = ' AND '.join([key+'=%('+key+')s' for key in towhere])
            if routedict['frompartner_tochannel_id']:   #use frompartner_tochannel in where-clause of query (partner/group dependent outchannel
                towhere['frompartner_tochannel_id'] = routedict['frompartner_tochannel_id']
                wherestring += ''' AND (frompartner=%(frompartner_tochannel_id)s
                                        OR frompartner in (SELECT from_partner_id
                                                            FROM partnergroup
                                                            WHERE to_partner_id =%(frompartner_tochannel_id)s ))'''
            if routedict['topartner_tochannel_id']:   #use topartner_tochannel in where-clause of query (partner/group dependent outchannel
                towhere['topartner_tochannel_id'] = routedict['topartner_tochannel_id']
                wherestring += ''' AND (topartner=%(topartner_tochannel_id)s
                                        OR topartner in (SELECT from_partner_id
                                                            FROM partnergroup
                                                            WHERE to_partner_id=%(topartner_tochannel_id)s ))'''
            toset = {'tochannel':routedict['tochannel'],'status':FILEOUT}
            botslib.addinfocore(change=toset,where=towhere,wherestring=wherestring)

            if not routedict['defer']:   #do outgoing part of route
                botslib.tryrunscript(userscript,scriptname,'preoutcommunication',routedict=routedict)
                if routedict['rsrv2'] == 1:               #zip outgoing.
                    preprocess.postprocess(routedict=routedict,function=preprocess.botszip)
                communication.run(idchannel=routedict['tochannel'],command=self.command,idroute=routedict['idroute'])
                #in communication several things can go wrong.
                #but: ALL file ready for communication should have same status etc; this way all recomnnunication can be handled same way:
                # status EXTERNOUT statust DONE (if communication goes OK)
                # status EXTERNOUT status ERROR (if file is not communicatied)
                #in order to do that some manipulation is needed
                #only needed if errors, how to check if error has occured here?
                where = {'status':FILEOUT,'statust':OK,'tochannel':routedict['tochannel']}
                change = {'status':EXTERNOUT,'statust':ERROR}
                botslib.addinfo(change=change,where=where)
                #
                botslib.tryrunscript(userscript,scriptname,'postoutcommunication',routedict=routedict)
                
        botslib.tryrunscript(userscript,scriptname,'end',routedict=routedict)

    def set_minta4query(self):
        botsglobal.minta4query = self.rootidta_of_current_run

class crashrecovery(new):
    ''' Basicaly the crashed run is rerun.
    '''
    def set_minta4query(self):
        ''' for crashrecovery: minta4query is the rootidta of the crashed run
        '''
        for row in botslib.query('''SELECT MAX(idta) as crashed_idta
                                    FROM ta
                                    WHERE idta<%(rootidta_of_current_run)s
                                    AND script= 0 ''',
                                    {'rootidta_of_current_run':self.rootidta_of_current_run}):
            if row['crashed_idta']:
                self.crashrecoverypossible = True
                botsglobal.minta4query = row['crashed_idta']
            else:
                self.crashrecoverypossible = False
                botsglobal.minta4query = 0
        return

    def prepare(self):
        #check conditions from self.set_minta4query():
        if not self.crashrecoverypossible:
            return False
        rootofcrashedrun = botslib.OldTransaction(botslib.get_minta4query())
        rootofcrashedrun.update(statust=DONE)
        #clean up things from crash **********************************
        #delete run report
        botslib.changeq('''DELETE FROM report WHERE idta = %(rootofcrashedrun)s''',{'rootofcrashedrun':rootofcrashedrun.idta})
        #delete file reports
        botslib.changeq('''DELETE FROM filereport WHERE idta>%(rootofcrashedrun)s''',{'rootofcrashedrun':rootofcrashedrun.idta})
        #delete ta's after ERROR and OK for crashed merges
        mergedidtatodelete = set()
        for row in botslib.query('''SELECT child  FROM ta 
                                    WHERE idta>%(rootofcrashedrun)s
                                    AND statust=%(statust)s
                                    AND status!=%(status)s
                                    AND child != 0 ''',
                                    {'rootofcrashedrun':rootofcrashedrun.idta,'status':PROCESS,'statust':OK}):
            mergedidtatodelete.add(row['child'])
        for idta in mergedidtatodelete:
            ta_object = botslib.OldTransaction(idta)
            ta_object.delete()
        #delete ta's after ERROR and OK for other
        for row in botslib.query('''SELECT idta  FROM ta 
                                    WHERE idta>%(rootofcrashedrun)s
                                    AND ( statust=%(statust1)s OR statust=%(statust2)s )
                                    AND status!=%(status)s
                                    AND child == 0 ''',
                                    {'rootofcrashedrun':rootofcrashedrun.idta,'status':PROCESS,'statust1':OK,'statust2':ERROR}):
            ta_object = botslib.OldTransaction(row['idta'])
            ta_object.deletechildren()
        return True
        

class automaticretrycommunication(new):
    @staticmethod
    def get_idta_last_error(idta_lastretry):
        for row in botslib.query('''SELECT MIN(idta) as min_idta
                                    FROM filereport
                                    WHERE idta>%(idta_lastretry)s
                                    AND statust == %(statust)s''',
                                    {'statust':ERROR,'idta_lastretry':idta_lastretry}):
            return row['min_idta']

    @botslib.log_session
    def prepare(self):
        ''' reinjects all files for which communication failed.
        '''
        do_retransmit = False
        #bots keeps track of last time automaticretrycommunication was done; reason is mainly performance
        idta_lastretry = botslib.uniquecore('bots__automaticretrycommunication',updatewith=self.rootidta_of_current_run)
        startidta = self.get_idta_last_error(idta_lastretry)
        if not startidta:
            return False
        for row in botslib.query('''SELECT idta,rsrv4
                                    FROM ta
                                    WHERE idta>%(startidta)s
                                    AND status=%(status)s
                                    AND statust=%(statust)s ''',
                                    {'statust':ERROR,'status':EXTERNOUT,'startidta':startidta}):
            do_retransmit = True
            ta_resend = botslib.OldTransaction(row['idta'])
            ta_resend.update(statust=RESEND)
            ta_externin = ta_resend.copyta(status=EXTERNIN,statust=DONE) #inject; status is DONE so this ta is not used further
            ta_externin.copyta(status=FILEOUT,statust=OK,rsrv4=row['rsrv4'])  #reinjected file is ready as new input
        return do_retransmit

        
class resend(new):
    @botslib.log_session
    def prepare(self):
        ''' prepare the files indicated by user to be resend. Return: indication if files should be resend.'''
        do_retransmit = False
        #for resend; this one is slow. Can be improved by having a separate list of idta to resend
        for row in botslib.query('''SELECT idta,parent,rsrv4
                                    FROM ta
                                    WHERE retransmit=%(retransmit)s
                                    AND status=%(status)s''',
                                    {'retransmit':True,'status':EXTERNOUT}):
            do_retransmit = True
            ta_outgoing = botslib.OldTransaction(row['idta'])
            ta_outgoing.update(retransmit=False,statust=RESEND)     #set retransmit back to False
            ta_resend = botslib.OldTransaction(row['parent'])  #parent ta with status RAWOUT; this is where the outgoing file is kept
            ta_externin = ta_resend.copyta(status=EXTERNIN,statust=DONE) #inject; status is DONE so this ta is not used further
            ta_externin.copyta(status=FILEOUT,statust=OK,rsrv4=row['rsrv4'])  #reinjected file is ready as new input
        return do_retransmit


class rereceive(new):
    @botslib.log_session
    def prepare(self):
        ''' prepare the files indicated by user to be rereceived. Return: indication if files should be rereceived.'''
        do_retransmit = False
        for row in botslib.query('''SELECT idta
                                    FROM filereport
                                    WHERE retransmit=%(retransmit)s ''',
                                    {'retransmit':True}):
            do_retransmit = True
            botslib.changeq('''UPDATE filereport
                              SET retransmit=%(retransmit)s
                              WHERE idta=%(idta)s ''',
                              {'idta':row['idta'],'retransmit':False})
            for row2 in botslib.query('''SELECT idta
                                        FROM ta
                                        WHERE parent=%(parent)s ''',
                                        {'parent':row['idta']}):
                ta_rereceive = botslib.OldTransaction(row2['idta'])
                ta_externin = ta_rereceive.copyta(status=EXTERNIN,statust=DONE,parent=0) #inject; status is DONE so this ta is not used further
                ta_externin.copyta(status=FILEIN,statust=OK)  #reinjected file is ready as new input
        return do_retransmit
