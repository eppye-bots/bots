import sys
from django.utils.translation import ugettext as _
#bots-modules
import communication
import envelope
import transform
import botslib
import botsglobal
import preprocess
import automaticmaintenance
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
                                                     defer
                                            FROM routes
                                            WHERE idroute=%(idroute)s
                                            AND   active=%(active)s
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
            if routedict['fromeditype'] == 'mailbag':               #mailbag for the route.
                preprocess.preprocess(routedict,preprocess.mailbag)

        #communication.run translation
        if routedict['translateind']:
            botslib.tryrunscript(userscript,scriptname,'pretranslation',routedict=routedict)
            #~ botslib.addinfo(change={'status':TRANSLATE},where={'status':FILEIN,'idroute':routedict['idroute']})
            transform.translate(idroute=routedict['idroute'])
            botslib.tryrunscript(userscript,scriptname,'posttranslation',routedict=routedict)
        #~ import os
        #~ os._exit(1)

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
                communication.run(idchannel=routedict['tochannel'],command=self.command,idroute=routedict['idroute'])
                #in communication several things can go wrong.
                #but: ALL file ready for communication should have same status etc; this way all recomnnunication cna be handled same way.
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
        #select the idta from the last report; this is the run just before the crashed one.
        for row in botslib.query('''SELECT MAX(idta) as from_idta FROM report'''):
            from_idta = row['from_idta']
            if from_idta is None:
                from_idta = 0
        for row in botslib.query('''SELECT MAX(idta) as crashed_idta
                                    FROM  ta
                                    WHERE idta>%(from_idta)s
                                    AND idta<%(max_idta)s
                                    AND script= 0 ''',
                                    {'from_idta':from_idta,'max_idta':self.rootidta_of_current_run}):
            crashed_idta = row['crashed_idta']
            if crashed_idta:
                self.crashrecoverypossible = True
                botsglobal.minta4query = crashed_idta
            else:
                self.crashrecoverypossible = False
                botsglobal.minta4query = 0
        return

    def prepare(self):
        #check conditions from self.set_minta4query():
        if not self.crashrecoverypossible:
            return False
        #check if the crashed run was indeed terminated not OK
        rootofcrashedrun = botslib.OldTransaction(botslib.get_minta4query())
        rootofcrashedrun.syn('statust')
        if rootofcrashedrun.statust == DONE:
            return False
        rootofcrashedrun.update(statust=DONE)
        #clean up things from crah **********************************
        #delete run report
        botslib.change('''DELETE FROM report WHERE idta = %(rootofcrashedrun)s''',{'rootofcrashedrun':rootofcrashedrun.idta})
        #delete file reports
        botslib.change('''DELETE FROM filereport WHERE reportidta = %(rootofcrashedrun)s''',{'rootofcrashedrun':rootofcrashedrun.idta})
        #delete ta's after ERROR and OK for crashed merges
        mergedidtatodelete = set()
        for row in botslib.query('''SELECT child  FROM ta 
                                    WHERE  idta>%(rootofcrashedrun)s
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
                                    WHERE  idta>%(rootofcrashedrun)s
                                    AND ( statust=%(statust1)s OR statust=%(statust2)s )
                                    AND status!=%(status)s
                                    AND child == 0 ''',
                                    {'rootofcrashedrun':rootofcrashedrun.idta,'status':PROCESS,'statust1':OK,'statust2':ERROR}):
            ta_object = botslib.OldTransaction(row['idta'])
            ta_object.deletechildren()
        return True
        

class automaticretrycommunication(new):
    def keeptrackoflastretry(self):
        ''' keep track of last automaticretrycommunication/retry
            if domain not used before, initialize it . '1' is the first value expected.
        '''
        domein = 'bots__automaticretrycommunication'
        cursor = botsglobal.db.cursor()
        try:
            cursor.execute(u'''SELECT nummer FROM uniek WHERE domein=%(domein)s''',{'domein':domein})
            oldlastta = cursor.fetchone()['nummer']
        except:     #DatabaseError; domein does not exist so set it
            cursor.execute(u'''INSERT INTO uniek (domein) VALUES (%(domein)s)''',{'domein': domein})
            oldlastta = 1
        cursor.execute(u'''UPDATE uniek SET nummer=%(nummer)s WHERE domein=%(domein)s''',{'domein':domein,'nummer':self.rootidta_of_current_run})
        botsglobal.db.commit()
        cursor.close()
        return oldlastta

    @staticmethod
    def get_idta_last_error(idta_lastretry):
        for row in botslib.query('''SELECT MIN(idta) as min_idta
                                    FROM  filereport
                                    WHERE idta>%(idta_lastretry)s
                                    AND statust == %(statust)s''',
                                    {'statust':ERROR,'idta_lastretry':idta_lastretry}):
            return row['min_idta']

    @botslib.log_session
    def prepare(self):
        ''' reinjects all files for which communication failed.
        '''
        do_retransmit = False
        idta_lastretry = self.keeptrackoflastretry()    #bots keeps track of last time automaticretrycommunication was done; reason is mainly performance
        startidta = self.get_idta_last_error(idta_lastretry)
        if not startidta:
            return False
        for row in botslib.query('''SELECT idta,rsrv4
                                    FROM  ta
                                    WHERE idta>%(startidta)s
                                    AND   status=%(status)s
                                    AND   statust=%(statust)s ''',
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
                                    FROM  ta
                                    WHERE retransmit=%(retransmit)s
                                    AND   status=%(status)s''',
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
                                    FROM  filereport
                                    WHERE retransmit=%(retransmit)s ''',
                                    {'retransmit':True}):
            do_retransmit = True
            botslib.change('''UPDATE filereport
                              SET retransmit=%(retransmit)s
                              WHERE idta=%(idta)s ''',
                              {'idta':row['idta'],'retransmit':False})
            for row2 in botslib.query('''SELECT idta
                                        FROM  ta
                                        WHERE parent=%(parent)s ''',
                                        {'parent':row['idta']}):
                ta_rereceive = botslib.OldTransaction(row2['idta'])
                ta_externin = ta_rereceive.copyta(status=EXTERNIN,statust=DONE,parent=0) #inject; status is DONE so this ta is not used further
                ta_externin.copyta(status=FILEIN,statust=OK)  #reinjected file is ready as new input
        return do_retransmit
