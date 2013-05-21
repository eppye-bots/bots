from django.utils.translation import ugettext as _
#bots-modules
import automaticmaintenance
import botslib
import botsglobal
import communication
import envelope
import preprocess
import transform
from botsconfig import *

@botslib.log_session
def rundispatcher(command,routestorun):
    classtocall = globals()[command]           #get the route class from this module
    myrun = classtocall(command,routestorun)
    return myrun.run()

class new(object):
    #important variables in run:
    #-  root_idta of this run
    #-  minta4query: minimum ta for queries: all database queries use this to limit the number of ta's to query.
    #                for most Run-classes this is equal to root_idta_of_run, except for crashrecovery
    def __init__(self,command,routestorun):
        self.routestorun = routestorun
        self.command = command
        self.rootidta_of_current_run = botslib._Transaction.processlist[-1]     #the idta of rundispatcher
        self.keep_track_if_outchannel_deferred = {}
        
    def run(self):
        if not self.set_minta4query() or not self.prepare():
            botsglobal.logger.info(_(u'Nothing to do in run.'))
            return 0
        for route in self.routestorun:
            botslib.setrouteid(route)
            self.router(route)
            botslib.setrouteid('')
        try:
            return automaticmaintenance.evaluate(self.command,botslib.get_minta4query())
        except:
            botsglobal.logger.exception(_(u'Error in automatic maintenance.'))
            return 1
        
    @botslib.log_session
    def router(self,route):
        botsglobal.minta4query_route = botslib._Transaction.processlist[-1]     #the idta of route
        foundroute = False
        for row in botslib.query('''SELECT idroute     ,
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
                                                 zip_incoming,
                                                 zip_outgoing
                                        FROM routes
                                        WHERE idroute=%(idroute)s
                                        AND active=%(active)s
                                        ORDER BY seq''',
                                        {'idroute':route,'active':True}):
            routedict = dict(row)   #convert to real dictionary (as self.command is added to routedict)
            routedict['command'] = self.command
            foundroute = True
            botsglobal.logger.info(_(u'Running route %(idroute)s %(seq)s'),routedict)
            self.routepart(routedict)
            #handle deferred-logic: mark if channel is deffered, umark if run
            self.keep_track_if_outchannel_deferred[routedict['tochannel']] = routedict['defer']
            botsglobal.logger.debug(u'Finished route %(idroute)s %(seq)s',routedict)
        if not foundroute:
            botsglobal.logger.warning(_(u'There is no (active) route "%(route)s".'),{'route':route})
        
    @botslib.log_session
    def routepart(self,routedict):
        ''' communication.run one route. variants:
            -   a route can be a userscript;
            -   a route can do only incoming
            -   a route can do only outgoing
            -   a route can do both incoming and outgoing
            -   at several points functions from a routescript are called - if function is in routescript
        '''
        botsglobal.minta4query_routepart = botslib._Transaction.processlist[-1]     #the idta of routepart
        #is there a user routescript?
        try:
            userscript,scriptname = botslib.botsimport('routescripts',routedict['idroute'])
        except ImportError:      #routescript is not there; other errors like syntax errors are not catched
            userscript = scriptname = None

        #if routescript has function 'main': communication.run 'main' (and do nothing else)
        if botslib.tryrunscript(userscript,scriptname,'main',routedict=routedict):
            return  #so: if function ' main' : communication.run only the routescript, nothing else.
        if not (userscript or routedict['fromchannel'] or routedict['tochannel'] or routedict['translateind']):
            raise botslib.ScriptError(_(u'Route "%(route)s" is empty: no routescript, not enough parameters.'),routedict)

        botslib.tryrunscript(userscript,scriptname,'start',routedict=routedict)

        #incoming part of route: incommunication, assign attribute from route, some preprocessing
        if routedict['fromchannel']:
            #only done for edi files from this route-part, this inchannel
            botslib.tryrunscript(userscript,scriptname,'preincommunication',routedict=routedict)
            communication.run(idchannel=routedict['fromchannel'],command=routedict['command'],idroute=routedict['idroute'],rootidta=botslib.get_minta4query_routepart())  #communication.run incommunication
            #add attributes from route to the received files;
            where = {'statust':OK,'status':FILEIN,'fromchannel':routedict['fromchannel'],'idroute':routedict['idroute'],'rootidta':botslib.get_minta4query_routepart()}
            change = {'editype':routedict['fromeditype'],'messagetype':routedict['frommessagetype'],'frompartner':routedict['frompartner'],'topartner':routedict['topartner'],'alt':routedict['alt']}
            nr_of_incoming_files_for_channel = botslib.updateinfocore(change=change,where=where)
            botslib.tryrunscript(userscript,scriptname,'postincommunication',routedict=routedict)
            if nr_of_incoming_files_for_channel:
                #unzip incoming files (if indicated)
                if routedict['zip_incoming'] == 1:               #unzip incoming (non-zipped gives error).
                    preprocess.preprocess(routedict=routedict,function=preprocess.botsunzip,pass_non_zip=False)
                elif routedict['zip_incoming'] == 2:               #unzip incoming if zipped.
                    preprocess.preprocess(routedict=routedict,function=preprocess.botsunzip,pass_non_zip=True)
                #run mailbag-module.
                if botsglobal.ini.getboolean('settings','compatibility_mailbag',False):
                    editypes_via_mailbag = ['mailbag']
                else:
                    editypes_via_mailbag = ['mailbag','edifact','x12','tradacoms']
                if routedict['fromeditype'] in editypes_via_mailbag:               #mailbag for the route.
                    preprocess.preprocess(routedict=routedict,function=preprocess.mailbag)

        #translate & merge, pass through: INFILE->MERGED
        if int(routedict['translateind']) == 1:
            #translate: for files in route
            botslib.tryrunscript(userscript,scriptname,'pretranslation',routedict=routedict)
            transform.translate(startstatus=FILEIN,endstatus=TRANSLATED,idroute=routedict['idroute'],rootidta=botslib.get_minta4query_route())
            botslib.tryrunscript(userscript,scriptname,'posttranslation',routedict=routedict)
            #**merge: for files in this route-part (the translated files)
            botslib.tryrunscript(userscript,scriptname,'premerge',routedict=routedict)
            envelope.mergemessages(startstatus=TRANSLATED,endstatus=MERGED,idroute=routedict['idroute'],rootidta=botslib.get_minta4query_routepart())
            botslib.tryrunscript(userscript,scriptname,'postmerge',routedict=routedict)
        elif routedict['translateind'] == 2:        #pass-through: pickup the incoming files and mark these as TRANSLATED (==translation is finished)
            botslib.addinfocore(change={'status':MERGED,'statust':OK},where={'status':FILEIN,'statust':OK,'idroute':routedict['idroute'],'rootidta':botslib.get_minta4query_route()})
        #NOTE: routedict['translateind'] == 0 than nothing will happen with the files in this route. 

        #ommunication outgoing channel: MERGED->RAWOUT
        if routedict['tochannel']:
            #**build query to add outchannel as attribute to outgoing files***
            #filter files in route for outchannel
            towhere = { 'status':MERGED,
                        'statust':OK,
                        'rootidta':botslib.get_minta4query_route(),
                        'idroute':routedict['idroute'],
                        'editype':routedict['toeditype'],
                        'messagetype':routedict['tomessagetype'],
                        'testindicator':routedict['testindicator'],
                        }
            towhere = dict([(key, value) for key,value in towhere.iteritems() if value])   #remove nul-values from dict
            wherestring = ''
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
            toset = {'status':FILEOUT,'statust':OK,'tochannel':routedict['tochannel']}
            nr_of_outgoing_files_for_channel = botslib.addinfocore(change=toset,where=towhere,wherestring=wherestring)
            
            if nr_of_outgoing_files_for_channel:
                #**zip outgoing
                #for files in this route-part for this out-channel
                if routedict['zip_outgoing'] == 1:               
                    preprocess.postprocess(routedict=routedict,function=preprocess.botszip)
                    
            #actual communication: run outgoing channel (if not deferred)
            #for all files in run that are for this channel (including the deferred ones from other routes)
            if not routedict['defer']:
                #determine range of idta to query: if channel was not deferred earlier in run: query only for route part else query for whole run
                rootidta = botslib.get_minta4query_routepart() if not self.keep_track_if_outchannel_deferred.get(routedict['tochannel'],False) else botslib.get_minta4query()
                if botslib.countoutfiles(idchannel=routedict['tochannel'],rootidta=rootidta):
                    botslib.tryrunscript(userscript,scriptname,'preoutcommunication',routedict=routedict)
                    communication.run(idchannel=routedict['tochannel'],command=routedict['command'],idroute=routedict['idroute'],rootidta=rootidta)
                    #in communication several things can go wrong.
                    #all outgoing files should have same status; that way all recomnnunication can be handled the same:
                    #- status EXTERNOUT statust DONE (if communication goes OK)
                    #- status EXTERNOUT status ERROR (if file is not communicatied)
                    #to have the same status for all outgoing files some manipulation is needed, eg in case no connection could be made.
                    botslib.addinfocore(change={'status':EXTERNOUT,'statust':ERROR},where={'status':FILEOUT,'statust':OK,'tochannel':routedict['tochannel'],'rootidta':rootidta})
                    botslib.tryrunscript(userscript,scriptname,'postoutcommunication',routedict=routedict)
                
        botslib.tryrunscript(userscript,scriptname,'end',routedict=routedict)

    def set_minta4query(self):
        botsglobal.minta4query_crash = 0
        botsglobal.minta4query = self.rootidta_of_current_run
        return True
        
    def prepare(self):
        return True
        

class crashrecovery(new):
    ''' Basicaly the crashed run is rerun.
    '''
    def set_minta4query(self):
        for row in botslib.query('''SELECT MAX(idta) as crashed_idta
                                    FROM ta
                                    WHERE idta < %(rootidta_of_current_run)s
                                    AND script = 0 ''',
                                    {'rootidta_of_current_run':self.rootidta_of_current_run}):
            if row['crashed_idta']:
                botsglobal.minta4query_crash = row['crashed_idta']
                botsglobal.minta4query = self.rootidta_of_current_run
                return True
            else:
                return False

    def prepare(self):
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
                                    WHERE idta > %(rootofcrashedrun)s
                                    AND statust = %(statust)s
                                    AND status != %(status)s
                                    AND child != 0 ''',
                                    {'rootofcrashedrun':rootofcrashedrun.idta,'status':PROCESS,'statust':OK}):
            mergedidtatodelete.add(row['child'])
        for idta in mergedidtatodelete:
            ta_object = botslib.OldTransaction(idta)
            ta_object.delete()
        #delete ta's after ERROR and OK for other
        for row in botslib.query('''SELECT idta  FROM ta 
                                    WHERE idta > %(rootofcrashedrun)s
                                    AND ( statust = %(statust1)s OR statust = %(statust2)s )
                                    AND status != %(status)s
                                    AND child = 0 ''',
                                    {'rootofcrashedrun':rootofcrashedrun.idta,'status':PROCESS,'statust1':OK,'statust2':ERROR}):
            ta_object = botslib.OldTransaction(row['idta'])
            ta_object.deletechildren()
        return True
        

class automaticretrycommunication(new):
    @staticmethod
    def get_idta_last_error(idta_lastretry):
        for row in botslib.query('''SELECT MIN(idta) AS min_idta
                                    FROM filereport
                                    WHERE idta > %(idta_lastretry)s
                                    AND statust = %(statust)s ''',
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
        for row in botslib.query('''SELECT idta,numberofresends
                                    FROM ta
                                    WHERE idta > %(startidta)s
                                    AND status = %(status)s
                                    AND statust = %(statust)s ''',
                                    {'statust':ERROR,'status':EXTERNOUT,'startidta':startidta}):
            do_retransmit = True
            ta_resend = botslib.OldTransaction(row['idta'])
            ta_resend.update(statust=RESEND)
            ta_externin = ta_resend.copyta(status=EXTERNIN,statust=DONE) #inject; status is DONE so this ta is not used further
            ta_externin.copyta(status=FILEOUT,statust=OK,numberofresends=row['numberofresends'])  #reinjected file is ready as new input
        return do_retransmit

        
class resend(new):
    @botslib.log_session
    def prepare(self):
        ''' prepare the files indicated by user to be resend. Return: indication if files should be resend.'''
        do_retransmit = False
        #for resend; this one is slow. Can be improved by having a separate list of idta to resend
        for row in botslib.query('''SELECT idta,parent,numberofresends
                                    FROM ta
                                    WHERE retransmit = %(retransmit)s
                                    AND status = %(status)s''',
                                    {'retransmit':True,'status':EXTERNOUT}):
            do_retransmit = True
            ta_outgoing = botslib.OldTransaction(row['idta'])
            ta_outgoing.update(retransmit=False,statust=RESEND)     #set retransmit back to False
            ta_resend = botslib.OldTransaction(row['parent'])  #parent ta with status RAWOUT; this is where the outgoing file is kept
            ta_externin = ta_resend.copyta(status=EXTERNIN,statust=DONE) #inject; status is DONE so this ta is not used further
            ta_externin.copyta(status=FILEOUT,statust=OK,numberofresends=row['numberofresends'])  #reinjected file is ready as new input
        return do_retransmit


class rereceive(new):
    @botslib.log_session
    def prepare(self):
        ''' prepare the files indicated by user to be rereceived. Return: indication if files should be rereceived.'''
        do_retransmit = False
        for row in botslib.query('''SELECT idta
                                    FROM filereport
                                    WHERE retransmit = %(retransmit)s ''',
                                    {'retransmit':1}):
            do_retransmit = True
            botslib.changeq('''UPDATE filereport
                              SET retransmit = %(retransmit)s
                              WHERE idta = %(idta)s ''',
                              {'idta':row['idta'],'retransmit':0})
            for row2 in botslib.query('''SELECT idta
                                        FROM ta
                                        WHERE parent = %(parent)s ''',
                                        {'parent':row['idta']}):
                ta_rereceive = botslib.OldTransaction(row2['idta'])
                ta_externin = ta_rereceive.copyta(status=EXTERNIN,statust=DONE,parent=0) #inject; status is DONE so this ta is not used further
                ta_externin.copyta(status=FILEIN,statust=OK)  #reinjected file is ready as new input
        return do_retransmit
