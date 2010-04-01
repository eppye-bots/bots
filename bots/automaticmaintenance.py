#bots modules
import botslib
import botsglobal
from botsconfig import *
import communication
tavars = 'idta,statust,divtext,child,ts,filename,status,idroute,fromchannel,tochannel,frompartner,topartner,frommail,tomail,contenttype,nrmessages,editype,messagetype,errortext'



def findlasterror():
    for row in botslib.query('''SELECT idta
                            FROM  filereport
                            GROUP BY idta
                            HAVING MAX(statust) != %(statust)s''',
                            {'statust':DONE}):
        #found incoming file with error
        for row2 in botslib.query('''SELECT min(reportidta) as min
                                FROM  filereport
                                WHERE idta = %(idta)s ''',
                                {'idta':row['idta']}):
            print '>',row2
            botsglobal.rootoflasterror = row2['min']
            return True
    return False


def evaluaterun(type):
    ''' traces all recieved files.
        Write a filereport for each file,
        and writes a report for the run.
    '''
    rootidta = botslib.getlastrun()
    resultLast={OPEN:0,ERROR:0,OK:0,DONE:0}
    send=0
    processerrors=0
    #look at infiles from this run; trace them to determine their tracestatus.
    for tadict in botslib.query('''SELECT ''' + tavars + '''
                                FROM  ta
                                WHERE idta > %(rootidta)s
                                AND status=%(status)s ''',
                                {'status':EXTERNIN,'rootidta':rootidta}):
        #~ tadict = dict(zip(tavars,row))
        botsglobal.logger.debug(u'evaluate %s.',tadict['idta'])
        mytrace = Trace(tadict,rootidta)
        resultLast[mytrace.statusttree]+=1
        #write filereport:
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
        del mytrace.ta
        del mytrace
    #count nr files send
    for row in botslib.query('''SELECT COUNT(*) as count
                                FROM  ta
                                WHERE idta > %(rootidta)s
                                AND status=%(status)s
                                AND statust=%(statust)s ''',
                                {'status':EXTERNOUT,'rootidta':rootidta,'statust':DONE}):
        send=row['count']
    #count nr of process with errors
    for row in botslib.query('''SELECT COUNT(*) as count
                                FROM  ta
                                WHERE idta >= %(rootidta)s
                                AND status=%(status)s
                                AND statust=%(statust)s''',
                                {'status':PROCESS,'rootidta':rootidta,'statust':ERROR}):
        processerrors=row['count']
    #generate report (in database)
    rootta=botslib.OldTransaction(rootidta)
    rootta.syn('ts')    #get the timestamp of this run
    LastReceived=resultLast[DONE]+resultLast[OK]+resultLast[OPEN]+resultLast[ERROR]
    status = bool(resultLast[OK]+resultLast[OPEN]+resultLast[ERROR]+processerrors)
    botslib.change(u'''INSERT INTO report (idta,
                                            lastopen,lasterror,lastok,lastdone,
                                            send,processerrors,ts,lastreceived,status,type)
                            VALUES  (%(idta)s,
                                    %(lastopen)s,%(lasterror)s,%(lastok)s,%(lastdone)s,
                                    %(send)s,%(processerrors)s,%(ts)s,%(lastreceived)s,%(status)s,%(type)s)
                            ''',
                            {'idta':rootidta,
                            'lastopen':resultLast[OPEN],'lasterror':resultLast[ERROR],'lastok':resultLast[OK],'lastdone':resultLast[DONE],
                            'send':send,'processerrors':processerrors,'ts':rootta.ts,'lastreceived':LastReceived,'status':status,'type':type})
    return sendreport(rootidta)    #return report status: 0 (no error) or 1 (error)


def evaluateretryrun(type):
    rootidta = botslib.getlastrun()
    resultLast={OPEN:0,ERROR:0,OK:0,DONE:0}
    send=0
    processerrors=0
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
            raise botslib.PanicError(u'MaintenanceRetry: could not find transaction "$txt".',txt=row['idta'])
        #~ tadict = dict(zip(tavars,row2))
        mytrace = Trace(tadict,rootidta)
        resultLast[mytrace.statusttree]+=1
        if mytrace.statusttree == DONE:
            mytrace.errortext = ''
        #~ mytrace.ta.update(tracestatus=mytrace.statusttree)
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
    if not didretry:
        return 0    #no error

    #count nr files send
    for row in botslib.query('''SELECT COUNT(*) as count
                                FROM  ta
                                WHERE status=%(status)s
                                AND statust=%(statust)s
                                AND idta > %(rootidta)s''',
                                {'status':EXTERNOUT,'rootidta':rootidta,'statust':DONE}):
        send=row['count']
    #count nr of process with errors
    for row in botslib.query('''SELECT COUNT(*) as count
                                FROM  ta
                                WHERE status=%(status)s
                                AND idta >= %(rootidta)s
                                AND statust=%(statust)s''',
                                {'status':PROCESS,'rootidta':rootidta,'statust':ERROR}):
        processerrors=row['count']
    #generate report (in database)
    rootta=botslib.OldTransaction(rootidta)
    rootta.syn('ts')    #get the timestamp of this run
    LastReceived=resultLast[DONE]+resultLast[OK]+resultLast[OPEN]+resultLast[ERROR]
    status = bool(resultLast[OK]+resultLast[OPEN]+resultLast[ERROR]+processerrors)
    botslib.change(u'''INSERT INTO report (idta,lastopen,lasterror,lastok,lastdone,
                                            send,processerrors,ts,lastreceived,status,type)
                            VALUES  (%(idta)s,
                                    %(lastopen)s,%(lasterror)s,%(lastok)s,%(lastdone)s,
                                    %(send)s,%(processerrors)s,%(ts)s,%(lastreceived)s,%(status)s,%(type)s)
                            ''',
                            {'idta':rootidta,
                            'lastopen':resultLast[OPEN],'lasterror':resultLast[ERROR],'lastok':resultLast[OK],'lastdone':resultLast[DONE],
                            'send':send,'processerrors':processerrors,'ts':rootta.ts,'lastreceived':LastReceived,'status':status,'type':type})
    return sendreport(rootidta)    #return report status: 0 (no error) or 1 (error)

def sendreport(rootidta):
    for row in botslib.query('''SELECT idta,lastopen,lasterror,lastok,lastdone,
                                        send,processerrors,ts,lastreceived,type,status
                                FROM  report
                                WHERE idta=%(rootidta)s''',
                                {'rootidta':rootidta}):
        break
    else:
        raise botslib.PanicError(u'In sendreport: could not find report?')
    results = dict([(key, row[key]) for key in row.keys()])   #convert to real dict (for SQLite)
        
    reporttext = 'Bots Report; type: %(type)s, time: %(ts)s\n'%(results)
    reporttext += '    %(lastreceived)d files received/processed in run.\n'%(results)
    if results['lastdone']:
        reporttext += '    %(lastdone)d files without errors,\n'%(results)
    if results['lasterror']:
        reporttext += '    %(lasterror)d files with errors,\n'%(results)
    if results['lastok']:
        reporttext += '    %(lastok)d files got stuck,\n'%(results)
    if results['lastopen']:
        reporttext += '    %(lastopen)d system errors,\n'%(results)
    if results['processerrors']:
        reporttext += '    %(processerrors)d errors in processes.\n'%(results)
    reporttext += '    %(send)d files send in run.\n'%(results)
    botsglobal.logger.info(reporttext)
    if botsglobal.ini.getboolean('settings','sendreportiferror',False) and results['status']:
        botslib.setrouteid('botsreport')
        ta_session = botslib.NewProcess('botsreport')
        ta_report=botslib.NewTransaction(status=FILEOUT,idroute='botsreport')  #new transaction for report-file/mail
        filename = str(ta_report.idta)   #create report filename
        _outstream = botslib.opendata(filename,'wb','ascii')
        _outstream.write(reporttext)
        _outstream.close()
        ta_report.update(statust=OK,filename=filename,frompartner=u'botsreportsender',topartner=u'botsreportreceiver',tochannel=u'botsreport',charset=u'ascii')
        communication.run('botsreport',idroute='botsreport')
        ta_session.update(statust=DONE)
        #~ #check if sending of errorreport was OK
        for row in botslib.query('''SELECT errortext
                                    FROM  ta
                                    WHERE idroute=%(idroute)s
                                    AND   statust!=%(statust)s''',
                                    {'statust':DONE,'idroute':'botsreport'}):
            botsglobal.logger.error(u'Errors while trying to send error report.')
        #~ #delete all bd-ta for botsreport (clean up report residue)
        botslib.change('''DELETE FROM ta
                            WHERE idroute=%(idroute)s''',
                           {'idroute':'botsreport'})
        botslib.setrouteid('')
    return int(results['status'])    #return report status: 0 (no error) or 1 (error)


class Trace(object):
    ''' ediobject-ta's form a tree; the incoming ediobject-ta (status EXTERNIN) is root.
        (yes, this works for merging, strange but inherent).
        tree gets a (one) statust, by walking the tree and evaluating the statust of nodes.
        all nodes are put into a tree of ta-objects;
    '''
    def __init__(self,tadict,rootidta):
        self.ta=botslib.OldTransaction(**tadict)
        self.rootidta = rootidta
        self._build(self.ta)
        self._evaluatestatus()
        self._getfilereport()

    def _build(self,tacurrent):
        ''' recursive,for each db-ta:
            -   fill global talist with the children (and children of children, etc)
        '''
        if tacurrent.child:
            for row in botslib.query('''SELECT ''' + tavars + '''
                                         FROM  ta
                                         WHERE idta=%(child)s''',
                                        {'child':tacurrent.child}):
                tacurrent.talijst = [botslib.OldTransaction(**row)]
                break   #there is only one child
        else:   #find successor by using parent-relationship; mostly this relation except for merge operations
            for row in botslib.query('''SELECT ''' + tavars + '''
                                        FROM   ta
                                        WHERE idta > %(currentidta)s
                                        AND parent=%(currentidta)s ''',      #adding the idta > %(parent)s to selection speeds up a lot.
                                        {'currentidta':tacurrent.idta}):
                tacurrent.talijst.append(botslib.OldTransaction(**row))
        for child in tacurrent.talijst:
            self._build(child)

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
        statustcount = [0,0,0,0]  #count of statust
        for child in tacurrent.talijst:
            if child.idta > self.rootidta:
                self.done = True
            statustcount[self._evaluatetreestatus(child)]+=1
        else:   #evaluate & return statusttree of db-ta & children;
            if tacurrent.statust==DONE:
                if statustcount[DONE]:
                    return DONE #all is OK
                elif statustcount[OK]:
                    return OK   #at least one of the child-trees is not DONE
                elif statustcount[ERROR]:
                    raise botslib.TraceError(u'DONE but no child is DONE or OK (idta: $idta).',idta=tacurrent.idta)
                else:   #if no ERROR and has no children: end of trace
                    return DONE
            elif tacurrent.statust==OK:
                if statustcount[ERROR]:
                    return OK   #child(ren) ERROR, this is expected
                elif statustcount[DONE]:
                    raise botslib.TraceError(u'OK but child is DONE (idta: $idta). Changing setup while errors are pending?',idta=tacurrent.idta)
                elif statustcount[OK]:
                    raise botslib.TraceError(u'OK but child is OK (idta: $idta). Changing setup while errors are pending?',idta=tacurrent.idta)
                else:
                    raise botslib.TraceNotPickedUpError(u'OK but file is not processed further (idta: $idta).',idta=tacurrent.idta)
            elif tacurrent.statust==ERROR:
                if tacurrent.talijst:
                    raise botslib.TraceError(u'ERROR but has child(ren) (idta: $idta). Changing setup while errors are pending?',idta=tacurrent.idta)
                else:
                    #~ self.errorta += [tacurrent]
                    return ERROR
            else:   #tacurrent.statust==OPEN
                raise botslib.TraceError(u'Severe error: found statust (idta: $idta).',idta=tacurrent.idta)

    def _getfilereport(self):
        ''' Walk the ta-tree again in order to retrieve information belonging to incoming file.
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
        self.retransmit = False
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


