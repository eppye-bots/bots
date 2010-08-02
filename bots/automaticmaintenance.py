#bots modules
import botslib
import botsglobal
from botsconfig import *
from django.utils.translation import ugettext as _
tavars = 'idta,statust,divtext,child,ts,filename,status,idroute,fromchannel,tochannel,frompartner,topartner,frommail,tomail,contenttype,nrmessages,editype,messagetype,errortext,script'


def evaluate(type,stuff2evaluate):
    # try: catch errors in retry....this should of course not happen...
    try:
        if type in ['--retry','--retrycommunication','--automaticretrycommunication']:
            return evaluateretryrun(type,stuff2evaluate)
        else:
            return evaluaterun(type,stuff2evaluate)
    except:
        botsglobal.logger.exception(_(u'Error in automatic maintenance.'))
        return 1    #there has been an error!

def evaluaterun(type,stuff2evaluate):
    ''' traces all recieved files.
        Write a filereport for each file,
        and writes a report for the run.
    '''
    resultlast={OPEN:0,ERROR:0,OK:0,DONE:0}     #gather results of all filereports for runreport
    #look at infiles from this run; trace them to determine their tracestatus.
    for tadict in botslib.query('''SELECT ''' + tavars + '''
                                FROM  ta
                                WHERE idta > %(rootidta)s
                                AND status=%(status)s ''',
                                {'status':EXTERNIN,'rootidta':stuff2evaluate}):
        botsglobal.logger.debug(u'evaluate %s.',tadict['idta'])
        mytrace = Trace(tadict,stuff2evaluate)
        resultlast[mytrace.statusttree]+=1
        insert_filereport(mytrace)
        del mytrace.ta
        del mytrace
    return finish_evaluation(stuff2evaluate,resultlast,type)

def evaluateretryrun(type,stuff2evaluate):
    resultlast={OPEN:0,ERROR:0,OK:0,DONE:0}
    didretry = False
    for row in botslib.query('''SELECT idta
                            FROM  filereport
                            GROUP BY idta
                            HAVING MAX(statust) != %(statust)s''',
                            {'statust':DONE}):
        didretry = True
        for tadict in botslib.query('''SELECT ''' + tavars + '''
                                    FROM  ta
                                    WHERE idta= %(idta)s ''',
                                    {'idta':row['idta']}):
            break
        else:   #there really should be a corresponding ta
            raise botslib.PanicError(_(u'MaintenanceRetry: could not find transaction "$txt".'),txt=row['idta'])
        mytrace = Trace(tadict,stuff2evaluate)
        resultlast[mytrace.statusttree]+=1
        if mytrace.statusttree == DONE:
            mytrace.errortext = ''
        #~ mytrace.ta.update(tracestatus=mytrace.statusttree)
        #ts for retried filereports is tricky: is this the time the file was originally received? best would be to use ts of prepare...
        #that is quite difficult, so use time of this run
        rootta=botslib.OldTransaction(stuff2evaluate)
        rootta.syn('ts')    #get the timestamp of this run
        mytrace.ts = rootta.ts
        insert_filereport(mytrace)
        del mytrace.ta
        del mytrace
    if not didretry:
        return 0    #no error
    return finish_evaluation(stuff2evaluate,resultlast,type)

def insert_filereport(mytrace):
    botslib.change(u'''INSERT INTO filereport (idta,statust,reportidta,retransmit,idroute,fromchannel,ts,
                                                infilename,tochannel,frompartner,topartner,frommail,
                                                tomail,ineditype,inmessagetype,outeditype,outmessagetype,
                                                incontenttype,outcontenttype,nrmessages,outfilename,errortext,
                                                divtext,outidta)
                            VALUES  (%(idta)s,%(statust)s,%(reportidta)s,%(retransmit)s,%(idroute)s,%(fromchannel)s,%(ts)s,
                                    %(infilename)s,%(tochannel)s,%(frompartner)s,%(topartner)s,%(frommail)s,
                                    %(tomail)s,%(ineditype)s,%(inmessagetype)s,%(outeditype)s,%(outmessagetype)s,
                                    %(incontenttype)s,%(outcontenttype)s,%(nrmessages)s,%(outfilename)s,%(errortext)s,
                                    %(divtext)s,%(outidta)s )
                            ''',
                            {'idta':mytrace.idta,'statust':mytrace.statusttree,'reportidta':mytrace.reportidta,
                            'retransmit':mytrace.retransmit,'idroute':mytrace.idroute,'fromchannel':mytrace.fromchannel,
                            'ts':mytrace.ts,'infilename':mytrace.infilename,'tochannel':mytrace.tochannel,
                            'frompartner':mytrace.frompartner,'topartner':mytrace.topartner,'frommail':mytrace.frommail,
                            'tomail':mytrace.tomail,'ineditype':mytrace.ineditype,'inmessagetype':mytrace.inmessagetype,
                            'outeditype':mytrace.outeditype,'outmessagetype':mytrace.outmessagetype,
                            'incontenttype':mytrace.incontenttype,'outcontenttype':mytrace.outcontenttype,
                            'nrmessages':mytrace.nrmessages,'outfilename':mytrace.outfilename,'errortext':mytrace.errortext,
                            'divtext':mytrace.divtext,'outidta':mytrace.outidta})

def finish_evaluation(stuff2evaluate,resultlast,type):
    #count nr files send
    for row in botslib.query('''SELECT COUNT(*) as count
                                FROM  ta
                                WHERE idta > %(rootidta)s
                                AND status=%(status)s
                                AND statust=%(statust)s ''',
                                {'status':EXTERNOUT,'rootidta':stuff2evaluate,'statust':DONE}):
        send = row['count']
    #count process errors
    for row in botslib.query('''SELECT COUNT(*) as count
                                FROM  ta
                                WHERE idta >= %(rootidta)s
                                AND status=%(status)s
                                AND statust=%(statust)s''',
                                {'status':PROCESS,'rootidta':stuff2evaluate,'statust':ERROR}):
        processerrors = row['count']
    #generate report (in database)
    rootta=botslib.OldTransaction(stuff2evaluate)
    rootta.syn('ts')    #get the timestamp of this run
    LastReceived=resultlast[DONE]+resultlast[OK]+resultlast[OPEN]+resultlast[ERROR]
    status = bool(resultlast[OK]+resultlast[OPEN]+resultlast[ERROR]+processerrors)
    botslib.change(u'''INSERT INTO report (idta,lastopen,lasterror,lastok,lastdone,
                                            send,processerrors,ts,lastreceived,status,type)
                            VALUES  (%(idta)s,
                                    %(lastopen)s,%(lasterror)s,%(lastok)s,%(lastdone)s,
                                    %(send)s,%(processerrors)s,%(ts)s,%(lastreceived)s,%(status)s,%(type)s)
                            ''',
                            {'idta':stuff2evaluate,
                            'lastopen':resultlast[OPEN],'lasterror':resultlast[ERROR],'lastok':resultlast[OK],'lastdone':resultlast[DONE],
                            'send':send,'processerrors':processerrors,'ts':rootta.ts,'lastreceived':LastReceived,'status':status,'type':type[2:]})
    return generate_report(stuff2evaluate)    #return report status: 0 (no error) or 1 (error)


def generate_report(stuff2evaluate):
    for results in botslib.query('''SELECT idta,lastopen,lasterror,lastok,lastdone,
                                            send,processerrors,ts,lastreceived,type,status
                                    FROM report
                                    WHERE idta=%(rootidta)s''',
                                    {'rootidta':stuff2evaluate}):
        break
    else:
        raise botslib.PanicError(_(u'In generate report: could not find report?'))
    subject = _(u'[Bots Error Report] %(time)s')%{'time':str(results['ts'])[:16]}
    reporttext = _(u'Bots Report; type: %(type)s, time: %(time)s\n')%{'type':results['type'],'time':str(results['ts'])[:19]}
    reporttext += _(u'    %d files received/processed in run.\n')%(results['lastreceived'])
    if results['lastdone']:
        reporttext += _(u'    %d files without errors,\n')%(results['lastdone'])
    if results['lasterror']:
        subject += _(u'; %d file errors')%(results['lasterror'])
        reporttext += _(u'    %d files with errors,\n')%(results['lasterror'])
    if results['lastok']:
        subject += _(u'; %d files stuck')%(results['lastok'])
        reporttext += _(u'    %d files got stuck,\n')%(results['lastok'])
    if results['lastopen']:
        subject += _(u'; %d system errors')%(results['lastopen'])
        reporttext += _(u'    %d system errors,\n')%(results['lastopen'])
    if results['processerrors']:
        subject += _(u'; %d process errors')%(results['processerrors'])
        reporttext += _(u'    %d errors in processes.\n')%(results['processerrors'])
    reporttext += _(u'    %d files send in run.\n')%(results['send'])
    
    botsglobal.logger.info(reporttext)
    if results['status']:
        botslib.sendbotserrorreport(subject,reporttext)
    return int(results['status'])    #return report status: 0 (no error) or 1 (error)


class Trace(object):
    ''' ediobject-ta's form a tree; the incoming ediobject-ta (status EXTERNIN) is root.
        (yes, this works for merging, strange but inherent).
        tree gets a (one) statust, by walking the tree and evaluating the statust of nodes.
        all nodes are put into a tree of ta-objects;
    '''
    def __init__(self,tadict,stuff2evaluate):
        realdict = dict([(key,tadict[key]) for key in tadict.keys()])
        self.ta=botslib.OldTransaction(**realdict)
        self.rootidta = stuff2evaluate
        self._buildevaluationstructure(self.ta)
        #~ self.display(self.ta)
        self._evaluatestatus()
        self._gatherfilereportdata()

    def display(self,currentta,level=0):
        print level*'    ',currentta.idta,currentta.statust,currentta.talijst
        for ta in currentta.talijst:
            self.display(ta,level+1)
        
    def _buildevaluationstructure(self,tacurrent):
        ''' recursive,for each db-ta:
            -   fill global talist with the children (and children of children, etc)
        '''
        #gather next steps/ta's for tacurrent; 
        if tacurrent.child: #find successor by using child relation ship
            for row in botslib.query('''SELECT ''' + tavars + '''
                                         FROM  ta
                                         WHERE idta=%(child)s''',
                                        {'child':tacurrent.child}):
                realdict = dict([(key,row[key]) for key in row.keys()])
                tacurrent.talijst = [botslib.OldTransaction(**realdict)]
        else:   #find successor by using parent-relationship; mostly this relation except for merge operations
            talijst = []
            for row in botslib.query('''SELECT ''' + tavars + '''
                                        FROM  ta
                                        WHERE idta > %(currentidta)s
                                        AND parent=%(currentidta)s ''',      #adding the idta > %(parent)s to selection speeds up a lot.
                                        {'currentidta':tacurrent.idta}):
                realdict = dict([(key,row[key]) for key in row.keys()])
                talijst.append(botslib.OldTransaction(**realdict))
            #filter: 
            #one ta might have multiple children; 2 possible reasons for that:
            #1. split up 
            #2. error is processing the file; and retried
            #Here case 2 (error/retry) is filtered; it is not interesting to evaluate the older errors!
            #So: if the same filename and different script: use newest idta
            #shortcut: when an error occurs in a split all is turned back.
            #so: split up is OK as a whole or because of retries.
            #so: if split, and different scripts: split is becaue of retires: use newest idta.
            #~ print tacurrent.talijst
            if len(talijst) > 1 and talijst[0].script != talijst[1].script:
                #find higest idta
                highest_ta = talijst[0]
                for ta in talijst[1:]:
                    if ta.idta > highest_ta.idta:
                        highest_ta = ta
                tacurrent.talijst = [highest_ta]
            else:
                tacurrent.talijst = talijst
        #recursive build:
        for child in tacurrent.talijst:
            self._buildevaluationstructure(child)

    def _evaluatestatus(self):
        self.done = False
        try:
            self.statusttree = self._evaluatetreestatus(self.ta)
            if self.statusttree == OK:
                self.statusttree = ERROR    #this is ugly!!
        except botslib.TraceNotPickedUpError:
            self.statusttree = OK
        except:     #botslib.TraceError:
            self.statusttree = OPEN

    def _evaluatetreestatus(self,tacurrent):
        ''' recursive, walks tree of ediobject-ta, depth-first
            for each db-ta:
            -   get statust of all child-db-ta (recursive); count these statust's
            -   evaluate this
            rules for evaluating:
            -   typical error-situation: DONE->OK->ERROR
            -   Db-ta with statust OK will be picked up next botsrun.
            -   if succes on next botsrun: DONE->   DONE->  ERROR
                                                        ->  DONE
            -   one db-ta can have more children; each of these children has to evaluated
            -   not possible is:       DONE->   ERROR (because there should always be statust OK)
        '''
        statustcount = [0,0,0,0]  #count of statust: number of OPEN, ERROR, OK, DONE
        for child in tacurrent.talijst:
            if child.idta > self.rootidta:
                self.done = True
            statustcount[self._evaluatetreestatus(child)]+=1
        else:   #evaluate & return statust of current ta & children;
            if tacurrent.statust==DONE:
                if statustcount[OK]:
                    return OK   #at least one of the child-trees is not DONE
                elif statustcount[DONE]:
                    return DONE #all is OK
                elif statustcount[ERROR]:
                    raise botslib.TraceError(-(u'DONE but no child is DONE or OK (idta: $idta).'),idta=tacurrent.idta)
                else:   #if no ERROR and has no children: end of trace
                    return DONE
            elif tacurrent.statust==OK:
                if statustcount[ERROR]:
                    return OK   #child(ren) ERROR, this is expected
                elif statustcount[DONE]:
                    raise botslib.TraceError(_(u'OK but child is DONE (idta: $idta). Changing setup while errors are pending?'),idta=tacurrent.idta)
                elif statustcount[OK]:
                    raise botslib.TraceError(_(u'OK but child is OK (idta: $idta). Changing setup while errors are pending?'),idta=tacurrent.idta)
                else:
                    raise botslib.TraceNotPickedUpError(_(u'OK but file is not processed further (idta: $idta).'),idta=tacurrent.idta)
            elif tacurrent.statust==ERROR:
                if tacurrent.talijst:
                    raise botslib.TraceError(_(u'ERROR but has child(ren) (idta: $idta). Changing setup while errors are pending?'),idta=tacurrent.idta)
                else:
                    #~ self.errorta += [tacurrent]
                    return ERROR
            else:   #tacurrent.statust==OPEN
                raise botslib.TraceError(_(u'Severe error: found statust (idta: $idta).'),idta=tacurrent.idta)

    def _gatherfilereportdata(self):
        ''' Walk the ta-tree again in order to retrieve information/data belonging to incoming file; statust (OK, DONE, ERROR etc) is NOT done here.
            If information is different in different ta's: place '*'
            Start 'root'-ta; a file coming in; status=EXTERNIN. Retrieve as much information from ta's as possible for the filereport.
        '''
        def core(ta):
            if ta.status==MIMEIN:
                self.frommail=ta.frommail
                self.tomail=ta.tomail
                self.incontenttype=ta.contenttype
            elif ta.status==RAWOUT:
                if ta.frommail:
                    if self.frommail:
                        if self.frommail != ta.frommail and asterisk:
                            self.frommail='*'
                    else:
                        self.frommail=ta.frommail
                if ta.tomail:
                    if self.tomail:
                        if self.tomail != ta.tomail and asterisk:
                            self.tomail='*'
                    else:
                        self.tomail=ta.tomail
                if ta.contenttype:
                    if self.outcontenttype:
                        if self.outcontenttype != ta.contenttype and asterisk:
                            self.outcontenttype='*'
                    else:
                        self.outcontenttype=ta.contenttype
                if ta.idta:
                    if self.outidta:
                        if self.outidta != ta.idta and asterisk:
                            self.outidta=0
                    else:
                        self.outidta=ta.idta
            elif ta.status==TRANSLATE:
                #self.ineditype=ta.editype
                if self.ineditype:
                    if self.ineditype!=ta.editype and asterisk:
                        self.ineditype='*'
                else:
                    self.ineditype=ta.editype
            elif ta.status==SPLITUP:
                self.nrmessages+=1
                if self.inmessagetype:
                    if self.inmessagetype!=ta.messagetype and asterisk:
                        self.inmessagetype='*'
                else:
                    self.inmessagetype=ta.messagetype
            elif ta.status==TRANSLATED:
                #self.outeditype=ta.editype
                if self.outeditype:
                    if self.outeditype!=ta.editype and asterisk:
                        self.outeditype='*'
                else:
                    self.outeditype=ta.editype
                if self.outmessagetype:
                    if self.outmessagetype!=ta.messagetype and asterisk:
                        self.outmessagetype='*'
                else:
                    self.outmessagetype=ta.messagetype
                if self.divtext:
                    if self.divtext!=ta.divtext and asterisk:
                        self.divtext='*'
                else:
                    self.divtext=ta.divtext
            elif ta.status==EXTERNOUT:
                if self.outfilename:
                    if self.outfilename != ta.filename and asterisk:
                        self.outfilename='*'
                else:
                    self.outfilename=ta.filename
                if self.tochannel:
                    if self.tochannel != ta.tochannel and asterisk:
                        self.tochannel='*'
                else:
                    self.tochannel=ta.tochannel
            if ta.frompartner:
                if not self.frompartner:
                    self.frompartner=ta.frompartner
                elif self.frompartner!=ta.frompartner and asterisk:
                    self.frompartner='*'
            if ta.topartner:
                if not self.topartner:
                    self.topartner=ta.topartner
                elif self.topartner!=ta.topartner and asterisk:
                    self.topartner='*'
            if ta.errortext:
                self.errortext = ta.errortext
            for child in ta.talijst:
                core(child)
            #end of core function

        asterisk = botsglobal.ini.getboolean('settings','multiplevaluesasterisk',True)
        self.idta = self.ta.idta
        self.reportidta = self.rootidta
        self.retransmit = 0
        self.idroute = self.ta.idroute
        self.fromchannel = self.ta.fromchannel
        self.ts = self.ta.ts
        self.infilename = self.ta.filename
        self.tochannel = ''
        self.frompartner = ''
        self.topartner = ''
        self.frommail = ''
        self.tomail = ''
        self.ineditype = ''
        self.inmessagetype = ''
        self.outeditype = ''
        self.outmessagetype = ''
        self.incontenttype = ''
        self.outcontenttype = ''
        self.nrmessages = 0
        self.outfilename = ''
        self.outidta = 0
        self.errortext = ''
        self.divtext = ''
        core(self.ta)


