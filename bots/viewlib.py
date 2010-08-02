import sys
import copy
import datetime
import django
from django.core.paginator import Paginator,EmptyPage, InvalidPage
from django.utils.translation import ugettext as _
import models
import botsglobal
from botsconfig import *

def preparereport2view(post,runidta):
    terugpost = post.copy()
    thisrun = models.report.objects.get(idta=runidta)
    terugpost['datefrom'] = thisrun.ts
    try:
        nextrun = thisrun.get_next_by_ts()
        terugpost['dateuntil'] = nextrun.ts
    except:
        terugpost['dateuntil'] = datetimeuntil()
    return terugpost

def changepostparameters(post,type):
    terugpost = post.copy()
    if type == 'confirm2in':
        for key in ['confirmtype','confirmed','fromchannel','tochannel']:
            terugpost.pop(key)[0]
        terugpost['ineditype'] = terugpost.pop('editype')[0]
        terugpost['inmessagetype'] = terugpost.pop('messagetype')[0]
        #~ terugpost['outeditype'] = ''
        #~ terugpost['outmessagetype'] = ''
    elif type == 'confirm2out':
        for key in ['confirmtype','confirmed','fromchannel','tochannel']:
            terugpost.pop(key)[0]
    elif type == 'out2in':
        terugpost['outeditype'] = terugpost.pop('editype')[0]
        terugpost['outmessagetype'] = terugpost.pop('messagetype')[0]
        #~ terugpost['ineditype'] = ''
        #~ terugpost['inmessagetype'] = ''
    elif type == 'out2confirm':
        for key in ['lastrun']:
            terugpost.pop(key)[0]
    elif type == 'in2out':
        terugpost['editype'] = terugpost.pop('outeditype')[0]
        terugpost['messagetype'] = terugpost.pop('outmessagetype')[0]
        for key in ['ineditype','inmessagetype']:
            terugpost.pop(key)[0]
    elif type == 'in2confirm':
        terugpost['editype'] = terugpost.pop('outeditype')[0]
        terugpost['messagetype'] = terugpost.pop('outmessagetype')[0]
        for key in ['lastrun','statust','ineditype','inmessagetype']:
            terugpost.pop(key)[0]
    elif type == '2process':
        for key in terugpost.keys():
            if key not in ['datefrom','dateuntil','lastrun','idroute']:
                terugpost.pop(key)[0]
    elif type == 'fromprocess':
        pass    #is OK, all values are used
    terugpost['sortedby'] = 'ts'
    terugpost['sortedasc'] = False
    terugpost['page'] = 1
    return terugpost

def django_trace_origin(idta,where):
    ''' bots traces back all from the current step/ta. 
        where is a dict that is used to indicate a condition.
        eg:  {'status':EXTERNIN}
        If bots finds a ta for which this is true, the ta is added to a list.
        The list is returned when all tracing is done, and contains all ta's for which 'where' is True
    '''
    def trace_recurse(ta):
        ''' recursive
            walk over ta's backward (to origin).
            if condition is met, add the ta to a list
        '''
        for parent in get_parent(ta):
            donelijst.append(parent.idta)
            for key,value in where.items():
                if getattr(parent,key) != value:
                    break
            else:   #all where-criteria are true; check if we already have this ta
                teruglijst.append(parent)
            trace_recurse(parent)
    def get_parent(ta):
        ''' yields the parents of a ta '''
        if ta.parent: 
            if ta.parent not in donelijst:   #search via parent
                yield models.ta.objects.get(idta=ta.parent)
        else:
            for parent in models.ta.objects.filter(child=ta.idta).all():
                if parent.idta in donelijst:
                    continue
                yield parent
        
    donelijst = []
    teruglijst = []
    ta = models.ta.objects.get(idta=idta)
    trace_recurse(ta)
    return teruglijst


def trace_document(pquery):
    ''' trace forward & backwardfrom the current step/ta (status SPLITUP). 
        gathers confirm information
    '''
    def trace_forward(ta):
        ''' recursive. walk over ta's forward (to exit). '''
        if ta.child: 
            child = models.ta.objects.get(idta=ta.child)
        else:
            try:
                child = models.ta.objects.filter(parent=ta.idta).all()[0]
            except IndexError:
                return    #no result, return
        if child.confirmasked:
            taorg.confirmtext += _(u'Confirm send: %(confirmasked)s; confirmed: %(confirmed)s; confirmtype: %(confirmtype)s\n')%{'confirmasked':child.confirmasked,'confirmed':child.confirmed,'confirmtype':child.confirmtype}
        if child.status==EXTERNOUT:
            taorg.outgoing = child.idta
            taorg.channel = child.tochannel
        trace_forward(child)
    def trace_back(ta):
        ''' recursive. walk over ta's backward (to origin).  '''
        if ta.parent: 
            parent = models.ta.objects.get(idta=ta.parent)
        else:
            try:
                parent = models.ta.objects.filter(child=ta.idta).all()[0]   #just get one parent
            except IndexError:
                return    #no result, return
        if parent.confirmasked:
            taorg.confirmtext += u'Confirm asked: %(confirmasked)s; confirmed: %(confirmed)s; confirmtype: %(confirmtype)s\n'%{'confirmasked':parent.confirmasked,'confirmed':parent.confirmed,'confirmtype':parent.confirmtype}
        if parent.status==EXTERNIN:
            taorg.incoming = parent.idta
            taorg.channel = parent.fromchannel
        trace_back(parent)
    #main for trace_document*****************
    for taorg in pquery.object_list:
        taorg.confirmtext = u''
        if taorg.status == SPLITUP:
            trace_back(taorg)
        else:
            trace_forward(taorg)
        if not taorg.confirmtext:
            taorg.confirmtext = u'---'


def gettrace(ta):
    ''' recursive. Build trace (tree of ta's).'''
    if ta.child:  #has a explicit child
        ta.talijst = [models.ta.objects.get(idta=ta.child)]
    else:   #search in ta-table who is reffering to ta
        ta.talijst = list(models.ta.objects.filter(parent=ta.idta).all())
    for child in ta.talijst:
        gettrace(child)

def trace2delete(trace):
    def gathermember(ta):
        memberlist.append(ta)
        for child in ta.talijst:
            gathermember(child)
    def gatherdelete(ta):
        if ta.status==MERGED:
            for includedta in models.ta.objects.filter(child=ta.idta,status=TRANSLATED).all():    #select all db-ta's included in MERGED ta
                if includedta not in memberlist:
                    #~ print 'not found idta',includedta.idta, 'not to deletelist:',ta.idta
                    return
        deletelist.append(ta)
        for child in ta.talijst:
            gatherdelete(child)
    memberlist=[]
    gathermember(trace)   #zet alle idta in memberlist
    #~ printlijst(memberlist, 'memberlist')
    #~ printlijst(deletelist, 'deletelist')
    deletelist=[]
    gatherdelete(trace)     #zet alle te deleten idta in deletelijst
    #~ printlijst(deletelist, 'deletelist')
    for ta in deletelist:
        ta.delete()

def trace2detail(ta):
    def newbranche(ta,level=0):
        def dota(ta, isfirststep = False):
            if isfirststep:
                if not level:
                    ta.ind= _(u'in')
                else:
                    ta.ind = _(u'split>>>')
            elif ta.status==MERGED and ta.nrmessages>1:
                ta.ind = _(u'merge<<<')
            elif ta.status==EXTERNOUT:
                ta.ind = _(u'out')
            else:
                ta.ind =''
            #~ ta.action = models.ta.objects.only('filename').get(idta=ta.script)
            ta.channel=ta.fromchannel
            if ta.tochannel:
                ta.channel=ta.tochannel
            detaillist.append(ta)
            lengtetalijst = len(ta.talijst)
            if lengtetalijst > 1:
                for child in ta.talijst:
                    newbranche(child,level=level+1)
            elif lengtetalijst == 1:
                dota(ta.talijst[0])
        #start new level
        dota(ta,isfirststep = True)
    detaillist=[]
    newbranche(ta)
    return detaillist

def datetimefrom():
    terug = datetime.datetime.today()-datetime.timedelta(1860)
    return terug.strftime('%Y-%m-%d %H:%M:%S')

def datetimeuntil():
    terug = datetime.datetime.today()
    return terug.strftime('%Y-%m-%d %H:%M:%S')

def handlepagination(requestpost,cleaned_data):
    ''' use requestpost to set criteria for pagination in cleaned_data'''
    if "first" in requestpost:
        cleaned_data['page'] = 1
    elif "previous" in requestpost:
        cleaned_data['page'] = cleaned_data['page'] - 1
    elif "next" in requestpost:
        cleaned_data['page'] = cleaned_data['page'] + 1
    elif "last" in requestpost:
        cleaned_data['page']=sys.maxint
    elif "order" in requestpost:   #change the sorting order
        if requestpost['order'] == cleaned_data['sortedby']:  #sort same row, but desc->asc etc
            cleaned_data['sortedasc'] =  not cleaned_data['sortedasc']
        else:
            cleaned_data['sortedby'] = requestpost['order'].lower()
            if cleaned_data['sortedby'] == 'ts':
                cleaned_data['sortedasc'] = False
            else:
                cleaned_data['sortedasc'] = True

def render(request,form,query=None):
    return django.shortcuts.render_to_response(form.template, {'form': form,"queryset":query},context_instance=django.template.RequestContext(request))

def getidtalastrun():
    return models.filereport.objects.all().aggregate(django.db.models.Max('reportidta'))['reportidta__max']

def filterquery(query , org_cleaned_data, incoming=False):
    ''' use the data of the form (mostly in hidden fields) to do the query.'''
    #~ print 'filterquery',org_cleaned_data
    #~ sortedasc2str = 
    cleaned_data = copy.copy(org_cleaned_data)    #copy because it it destroyed in setting up query
    page = cleaned_data.pop('page')     #do not use this in query, use in paginator
    if 'dateuntil' in cleaned_data:
        query = query.filter(ts__lt=cleaned_data.pop('dateuntil'))
    if 'datefrom' in cleaned_data:
        query = query.filter(ts__gte=cleaned_data.pop('datefrom'))
    if 'botskey' in cleaned_data and cleaned_data['botskey']:
        query = query.filter(botskey__icontains=cleaned_data.pop('botskey'))
    if 'sortedby' in cleaned_data:
        query = query.order_by({True:'',False:'-'}[cleaned_data.pop('sortedasc')] + cleaned_data.pop('sortedby'))
    if 'lastrun' in cleaned_data:
        if cleaned_data.pop('lastrun'):
            idtalastrun = getidtalastrun()
            if idtalastrun:     #if no result (=None): there are no filereports.
                if incoming:    #detect if incoming; do other selection
                    query = query.filter(reportidta=idtalastrun)
                else:
                    query = query.filter(idta__gt=idtalastrun)
    for key,value in cleaned_data.items():
        if not value:
            del cleaned_data[key]
    query = query.filter(**cleaned_data)
    paginator = Paginator(query, botsglobal.ini.getint('settings','limit',30))
    try:
        return paginator.page(page)
    except EmptyPage, InvalidPage:  #page does not exist: use last page
        lastpage = paginator.num_pages
        org_cleaned_data['page']=lastpage  #change value in form as well!!
        return paginator.page(lastpage)

