import sys
import os
import subprocess
import django
from django.utils.translation import ugettext as _
import forms
import models
import viewlib
import botslib
import pluglib
import botsglobal
import glob
from botsconfig import *

def server_error(request, template_name='500.html'):
    """
    500 error handler.

    Templates: `500.html`
    Context: None
    """
    import traceback
    exc_info = traceback.format_exc(None).decode('utf-8','ignore')

    t = django.template.loader.get_template(template_name) # You need to create a 500.html template.
    return django.http.HttpResponseServerError(t.render(django.template.Context({'exc_info':exc_info})))

def index(request,*kw,**kwargs):
    return django.shortcuts.render_to_response('admin/base.html', {},context_instance=django.template.RequestContext(request))

def about(request,*kw,**kwargs):
    return django.shortcuts.render_to_response('bots/about.html', {'botsinfo':botslib.botsinfo()},context_instance=django.template.RequestContext(request))

def help(request,*kw,**kwargs):
    return django.shortcuts.render_to_response('bots/help.html', {},context_instance=django.template.RequestContext(request))

def reports(request,*kw,**kwargs):
    #~ print 'reports received',kw,kwargs,request.POST,request.GET
    if request.method == 'GET':
        if 'select' in request.GET:             #via menu, go to select form
            formout = forms.SelectReports()
            return viewlib.render(request,formout)
        else:                              #via menu, go to view form
            cleaned_data = {'page':1,'sortedby':'ts','sortedasc':False}
    else:                                  # request.method == 'POST'
        if 'fromselect' in request.POST:        #coming from select criteria screen
            formin = forms.SelectReports(request.POST)
            if not formin.is_valid():
                return viewlib.render(request,formin)
        else:
            formin = forms.ViewReports(request.POST)
            if not formin.is_valid():
                return viewlib.render(request,formin)
            if '2select' in request.POST:         #coming from ViewIncoming, change the selection criteria, go to select form
                formout = forms.SelectReports(formin.cleaned_data)
                return viewlib.render(request,formout)
            elif 'report2incoming' in request.POST:         #coming from ViewIncoming, go to incoming
                request.POST = viewlib.preparereport2view(request.POST,int(request.POST['report2incoming']))
                return incoming(request)
            elif 'report2outgoing' in request.POST:         #coming from ViewIncoming, go to incoming
                request.POST = viewlib.preparereport2view(request.POST,int(request.POST['report2outgoing']))
                return outgoing(request)
            elif 'report2process' in request.POST:         #coming from ViewIncoming, go to incoming
                request.POST = viewlib.preparereport2view(request.POST,int(request.POST['report2process']))
                return process(request)
            elif 'report2errors' in request.POST:         #coming from ViewIncoming, go to incoming
                newpost = viewlib.preparereport2view(request.POST,int(request.POST['report2errors']))
                newpost['statust'] = ERROR
                request.POST = newpost
                return incoming(request)
            else:                                    #coming from ViewIncoming
                viewlib.handlepagination(request.POST,formin.cleaned_data)
        cleaned_data = formin.cleaned_data
                
    query = models.report.objects.all()
    pquery = viewlib.filterquery(query,cleaned_data)
    formout = forms.ViewReports(initial=cleaned_data)
    return viewlib.render(request,formout,pquery)
    
def incoming(request,*kw,**kwargs):
    if request.method == 'GET':
        if 'select' in request.GET:             #via menu, go to select form
            formout = forms.SelectIncoming()
            return viewlib.render(request,formout)
        elif 'all' in request.GET:             #via menu, go to all runs
            cleaned_data = {'page':1,'sortedby':'ts','sortedasc':False}
        else:                              #via menu, go to view form for last run
            cleaned_data = {'page':1,'lastrun':True,'sortedby':'ts','sortedasc':False}
    else:                                  # request.method == 'POST'
        if '2outgoing' in request.POST:        #coming from ViewIncoming, go to outgoing form using same criteria
            request.POST = viewlib.changepostparameters(request.POST,type='in2out')
            return outgoing(request)
        elif '2process' in request.POST:        #coming from ViewIncoming, go to outgoing form using same criteria
            request.POST = viewlib.changepostparameters(request.POST,type='2process')
            return process(request)
        elif '2confirm' in request.POST:        #coming from ViewIncoming, go to outgoing form using same criteria
            request.POST = viewlib.changepostparameters(request.POST,type='in2confirm')
            return process(request)
        elif 'fromselect' in request.POST:        #coming from select criteria screen
            formin = forms.SelectIncoming(request.POST)
            if not formin.is_valid():
                return viewlib.render(request,formin)
        else:                                   #coming from ViewIncoming
            formin = forms.ViewIncoming(request.POST)
            if not formin.is_valid():
                return viewlib.render(request,formin)
            elif '2select' in request.POST:         #go to select form using same criteria
                formout = forms.SelectIncoming(formin.cleaned_data)
                return viewlib.render(request,formout)
            elif 'retransmit' in request.POST:        #coming from ViewIncoming
                idta,reportidta = request.POST[u'retransmit'].split('-')
                filereport = models.filereport.objects.get(idta=int(idta),reportidta=int(reportidta))
                filereport.retransmit = not filereport.retransmit
                filereport.save()
            elif 'delete' in request.POST:        #coming from ViewIncoming
                idta = int(request.POST[u'delete'])
                #~ query = models.filereport.objects.filter(idta=int(idta)).all().delete()
                models.filereport.objects.filter(idta=idta).delete()
                ta = models.ta.objects.get(idta=idta)
                viewlib.gettrace(ta)
                viewlib.trace2delete(ta)
            else:                                    #coming from ViewIncoming
                viewlib.handlepagination(request.POST,formin.cleaned_data)
        cleaned_data = formin.cleaned_data
                
    query = models.filereport.objects.all()
    pquery = viewlib.filterquery(query,cleaned_data,incoming=True)
    formout = forms.ViewIncoming(initial=cleaned_data)
    return viewlib.render(request,formout,pquery)

def outgoing(request,*kw,**kwargs):
    if request.method == 'GET':
        if 'select' in request.GET:             #via menu, go to select form
            formout = forms.SelectOutgoing()
            return viewlib.render(request,formout)
        elif 'all' in request.GET:             #via menu, go to all runs
            cleaned_data = {'page':1,'sortedby':'ts','sortedasc':False}
        else:                              #via menu, go to view form for last run
            cleaned_data = {'page':1,'lastrun':True,'sortedby':'ts','sortedasc':False}
    else:                                  # request.method == 'POST'
        if '2incoming' in request.POST:        #coming from ViewIncoming, go to outgoing form using same criteria
            request.POST = viewlib.changepostparameters(request.POST,type='out2in')
            return incoming(request)
        elif '2process' in request.POST:        #coming from ViewIncoming, go to outgoing form using same criteria
            request.POST = viewlib.changepostparameters(request.POST,type='2process')
            return process(request)
        elif '2confirm' in request.POST:        #coming from ViewIncoming, go to outgoing form using same criteria
            request.POST = viewlib.changepostparameters(request.POST,type='out2confirm')
            return process(request)
        elif 'fromselect' in request.POST:        #coming from select criteria screen
            formin = forms.SelectOutgoing(request.POST)
            if not formin.is_valid():
                return viewlib.render(request,formin)
        else:
            formin = forms.ViewOutgoing(request.POST)
            if not formin.is_valid():
                return viewlib.render(request,formin)
            elif '2select' in request.POST:         #coming from ViewIncoming, change the selection criteria, go to select form
                formout = forms.SelectOutgoing(formin.cleaned_data)
                return viewlib.render(request,formout)
            elif 'retransmit' in request.POST:        #coming from ViewIncoming
                ta = models.ta.objects.get(idta=int(request.POST[u'retransmit']))
                ta.retransmit = not ta.retransmit
                ta.save()
            else:                                    #coming from ViewIncoming
                viewlib.handlepagination(request.POST,formin.cleaned_data)
        cleaned_data = formin.cleaned_data
                
    query = models.ta.objects.filter(status=EXTERNOUT,statust=DONE).all()
    pquery = viewlib.filterquery(query,cleaned_data)
    formout = forms.ViewOutgoing(initial=cleaned_data)
    return viewlib.render(request,formout,pquery)

def document(request,*kw,**kwargs):
    if request.method == 'GET':
        if 'select' in request.GET:             #via menu, go to select form
            formout = forms.SelectDocument()
            return viewlib.render(request,formout)
        elif 'all' in request.GET:             #via menu, go to all runs
            cleaned_data = {'page':1,'sortedby':'idta','sortedasc':False}
        else:                              #via menu, go to view form for last run
            cleaned_data = {'page':1,'lastrun':True,'sortedby':'idta','sortedasc':False}
    else:                                  # request.method == 'POST'
        if 'fromselect' in request.POST:        #coming from select criteria screen
            formin = forms.SelectDocument(request.POST)
            if not formin.is_valid():
                return viewlib.render(request,formin)
        else:
            formin = forms.ViewDocument(request.POST)
            if not formin.is_valid():
                return viewlib.render(request,formin)
            elif '2select' in request.POST:         #coming from ViewIncoming, change the selection criteria, go to select form
                formout = forms.SelectDocument(formin.cleaned_data)
                return viewlib.render(request,formout)
            elif 'retransmit' in request.POST:        #coming from Documents, no reportidta
                idta = request.POST[u'retransmit']
                filereport = models.filereport.objects.get(idta=int(idta),statust=DONE)
                filereport.retransmit = not filereport.retransmit
                filereport.save()
            else:                                    #coming from ViewIncoming
                viewlib.handlepagination(request.POST,formin.cleaned_data)
        cleaned_data = formin.cleaned_data
                
    query = models.ta.objects.filter(django.db.models.Q(status=SPLITUP)|django.db.models.Q(status=TRANSLATED)).all()
    pquery = viewlib.filterquery(query,cleaned_data)
    viewlib.trace_document(pquery)
    formout = forms.ViewDocument(initial=cleaned_data)
    return viewlib.render(request,formout,pquery)

def process(request,*kw,**kwargs):
    if request.method == 'GET':
        if 'select' in request.GET:             #via menu, go to select form
            formout = forms.SelectProcess()
            return viewlib.render(request,formout)
        elif 'all' in request.GET:             #via menu, go to all runs
            cleaned_data = {'page':1,'sortedby':'ts','sortedasc':False}
        else:                              #via menu, go to view form for last run
            cleaned_data = {'page':1,'lastrun':True,'sortedby':'ts','sortedasc':False}
    else:                                  # request.method == 'POST'
        if '2incoming' in request.POST:        #coming from ViewIncoming, go to outgoing form using same criteria
            request.POST = viewlib.changepostparameters(request.POST,type='fromprocess')
            return incoming(request)
        elif '2outgoing' in request.POST:        #coming from ViewIncoming, go to outgoing form using same criteria
            request.POST = viewlib.changepostparameters(request.POST,type='fromprocess')
            return outgoing(request)
        elif 'fromselect' in request.POST:        #coming from select criteria screen
            formin = forms.SelectProcess(request.POST)
            if not formin.is_valid():
                return viewlib.render(request,formin)
        else:
            if 'retry' in request.POST:
                idta = request.POST[u'retry']
                ta = models.ta.objects.get(idta=int(idta))
                ta.retransmit = not ta.retransmit
                ta.save()
            formin = forms.ViewProcess(request.POST)
            if not formin.is_valid():
                return viewlib.render(request,formin)
            elif '2select' in request.POST:         #coming from ViewIncoming, change the selection criteria, go to select form
                formout = forms.SelectProcess(formin.cleaned_data)
                return viewlib.render(request,formout)
            else:                                    #coming from ViewIncoming
                viewlib.handlepagination(request.POST,formin.cleaned_data)
        cleaned_data = formin.cleaned_data
                
    query = models.ta.objects.filter(status=PROCESS,statust=ERROR).all()
    pquery = viewlib.filterquery(query,cleaned_data)
    formout = forms.ViewProcess(initial=cleaned_data)
    return viewlib.render(request,formout,pquery)

def detail(request,*kw,**kwargs):
    ''' in: the idta, either as parameter in or out. 
        in: is idta of incoming file.
        out: idta of outgoing file, need to trace back for incoming file. 
        return list of ta's for display in detail template. 
        This list is formatted and ordered for display.
        first, get a tree (trace) starting with the incoming ta ;
        than make up the details for the trace
    '''
    if request.method == 'GET':
        if 'inidta' in request.GET:
            rootta = models.ta.objects.get(idta=int(request.GET['inidta']))
            viewlib.gettrace(rootta)
            detaillist = viewlib.trace2detail(rootta)
            return django.shortcuts.render_to_response('bots/detail.html', {'detaillist':detaillist,'rootta':rootta,},context_instance=django.template.RequestContext(request))
        else:
            #trace back to root:
            rootta = viewlib.django_trace_origin(int(request.GET['outidta']),{'status':EXTERNIN})[0]
            viewlib.gettrace(rootta)
            detaillist = viewlib.trace2detail(rootta)
            return django.shortcuts.render_to_response('bots/detail.html', {'detaillist':detaillist,'rootta':rootta,},context_instance=django.template.RequestContext(request))

def confirm(request,*kw,**kwargs):
    if request.method == 'GET':
        if 'select' in request.GET:             #via menu, go to select form
            formout = forms.SelectConfirm()
            return viewlib.render(request,formout)
        else:                              #via menu, go to view form for last run
            cleaned_data = {'page':1,'sortedby':'ts','sortedasc':False}
    else:                                  # request.method == 'POST'
        if '2incoming' in request.POST:        #coming from ViewIncoming, go to outgoing form using same criteria
            request.POST = viewlib.changepostparameters(request.POST,type='confirm2in')
            return incoming(request)
        elif '2outgoing' in request.POST:        #coming from ViewIncoming, go to outgoing form using same criteria
            request.POST = viewlib.changepostparameters(request.POST,type='confirm2out')
            return outgoing(request)
        elif 'fromselect' in request.POST:        #coming from select criteria screen
            formin = forms.SelectConfirm(request.POST)
            if not formin.is_valid():
                return viewlib.render(request,formin)
        else:
            formin = forms.ViewConfirm(request.POST)
            if not formin.is_valid():
                return viewlib.render(request,formin)
            elif '2select' in request.POST:         #coming from ViewIncoming, change the selection criteria, go to select form
                formout = forms.SelectConfirm(formin.cleaned_data)
                return viewlib.render(request,formout)
            else:                                    #coming from ViewIncoming
                viewlib.handlepagination(request.POST,formin.cleaned_data)
        cleaned_data = formin.cleaned_data
                
    query = models.ta.objects.filter(confirmasked=True).all()
    pquery = viewlib.filterquery(query,cleaned_data)
    formout = forms.ViewConfirm(initial=cleaned_data)
    return viewlib.render(request,formout,pquery)

def filer(request,*kw,**kwargs):
    ''' handles bots file viewer. Only files in data dir of Bots are displayed.'''
    nosuchfile = _(u'No such file.')
    if request.method == 'GET':
        try:
            idta = request.GET['idta']
        except:
            return  django.shortcuts.render_to_response('bots/filer.html', {'error_content': nosuchfile},context_instance=django.template.RequestContext(request))
        if idta == 0: #for the 'starred' file names (eg multiple output)
            return  django.shortcuts.render_to_response('bots/filer.html', {'error_content': nosuchfile},context_instance=django.template.RequestContext(request))
        try:
            currentta = list(models.ta.objects.filter(idta=idta))[0]
            if request.GET['action']=='downl':
                response = django.http.HttpResponse(mimetype=currentta.contenttype)
                response['Content-Disposition'] = 'attachment; filename=' + currentta.filename + '.txt'
                #~ absfilename = botslib.abspathdata(currentta.filename)
                #~ response['Content-Length'] = os.path.getsize(absfilename)
                response.write(botslib.readdata(currentta.filename,charset=currentta.charset,errors='ignore'))
                return response
            elif request.GET['action']=='previous':
                if currentta.parent:  #has a explicit parent
                    talijst = list(models.ta.objects.filter(idta=currentta.parent))
                else:   #get list of ta's referring to this idta as child
                    talijst = list(models.ta.objects.filter(child=currentta.idta))
            elif request.GET['action']=='this':
                if currentta.status == EXTERNIN:     #jump strait to next file, as EXTERNIN can not be displayed.
                    talijst = list(models.ta.objects.filter(parent=currentta.idta))
                elif currentta.status == EXTERNOUT:
                    talijst = list(models.ta.objects.filter(idta=currentta.parent))
                else:
                    talijst = [currentta]
            elif request.GET['action']=='next':
                if currentta.child: #has a explicit child
                    talijst = list(models.ta.objects.filter(idta=currentta.child))
                else:
                    talijst = list(models.ta.objects.filter(parent=currentta.idta))
            for ta in talijst:
                ta.has_next = True
                if ta.status == EXTERNIN:
                    ta.content = _(u'External file. Can not be displayed. Use "next".')
                elif ta.status == EXTERNOUT:
                    ta.content = _(u'External file. Can not be displayed. Use "previous".')
                    ta.has_next = False
                elif ta.statust in [OPEN,ERROR]:
                    ta.content = _(u'File has error status and does not exist. Use "previous".')
                    ta.has_next = False
                elif not ta.filename:
                    ta.content = _(u'File can not be displayed.')
                else:
                    if ta.charset:  #guess charset; uft-8 is reasonable
                        ta.content = botslib.readdata(ta.filename,charset=ta.charset,errors='ignore')
                    else:
                        ta.content = botslib.readdata(ta.filename,charset='utf-8',errors='ignore')
            return  django.shortcuts.render_to_response('bots/filer.html', {'idtas': talijst},context_instance=django.template.RequestContext(request))
        except:
            print botslib.txtexc()
            return  django.shortcuts.render_to_response('bots/filer.html', {'error_content': nosuchfile},context_instance=django.template.RequestContext(request))

def plugin(request,*kw,**kwargs):
    if request.method == 'GET':
        form = forms.UploadFileForm()
        return  django.shortcuts.render_to_response('bots/plugin.html', {'form': form},context_instance=django.template.RequestContext(request))
    else:
        if 'submit' in request.POST:        #coming from ViewIncoming, go to outgoing form using same criteria
            form = forms.UploadFileForm(request.POST, request.FILES)
            if form.is_valid():
                botsglobal.logger.info(_(u'Start reading plugin "%s".'),request.FILES['file'].name)
                try:
                    if pluglib.load(request.FILES['file'].temporary_file_path()):
                        request.user.message_set.create(message='Renamed existing files.')
                except botslib.PluginError,txt:
                    botsglobal.logger.info(u'%s',str(txt))
                    request.user.message_set.create(message='%s'%txt)
                else:
                    botsglobal.logger.info(_(u'Plugin "%s" read succesful.'),request.FILES['file'].name)
                    request.user.message_set.create(message='Plugin %s read succesful.'%request.FILES['file'].name)
                request.FILES['file'].close()
            else:
                 request.user.message_set.create(message=_(u'No plugin read.'))
        return django.shortcuts.redirect('/')
    
def plugout(request,*kw,**kwargs):
    if request.method == 'GET':
        filename = botslib.join(botsglobal.ini.get('directories','botssys'),request.GET['function'])
        #~ filename = os.path.abspath(request.GET['function'])
        botsglobal.logger.info(_(u'Start writing plugin "%s".'),filename)
        try:
            pluglib.dump(filename,request.GET['function'])
        except botslib.PluginError, txt:
            botsglobal.logger.info(u'%s',str(txt))
            request.user.message_set.create(message='%s'%txt)
        else:
            botsglobal.logger.info(_(u'Plugin "%s" created succesful.'),filename)
            request.user.message_set.create(message=_(u'Plugin %s created succesful.')%filename)
    return django.shortcuts.redirect('/')

def delete(request,*kw,**kwargs):
    if request.method == 'GET':
        if 'transactions' in request.GET:
            #while testing with very big loads, deleting transaction when wrong. Using raw SQL solved this.
            from django.db import connection, transaction
            cursor = connection.cursor()
            cursor.execute("DELETE FROM ta")
            cursor.execute("DELETE FROM filereport")
            cursor.execute("DELETE FROM report")
            #~ models.ta.objects.all().delete()
            #~ models.filereport.objects.all().delete()
            #~ models.report.objects.all().delete()
            transaction.commit_unless_managed()
            request.user.message_set.create(message=_(u'All transactions are deleted.'))
            try:
                frompath = botslib.join(botsglobal.ini.get('directories','data','botssys/data'),'*')
                for filename in glob.glob(frompath):
                    if os.path.isdir(filename):
                        frompath2 = botslib.join(filename,'*')
                        emptydir=True
                        for filename2 in glob.glob(frompath2): 
                            if os.path.isdir(filename2):
                                emptydir = False
                            else:
                                os.remove(filename2)
                        if emptydir:
                            os.rmdir(filename)
                    else:
                        os.remove(filename2)
            except:
                pass
        elif 'configuration' in request.GET:
            models.confirmrule.objects.all().delete()
            models.channel.objects.all().delete()
            models.chanpar.objects.all().delete()
            models.partner.objects.all().delete()
            models.translate.objects.all().delete()
            models.routes.objects.all().delete()
            request.user.message_set.create(message=_(u'All configuration is deleted.'))
        elif 'codelists' in request.GET:
            models.ccode.objects.all().delete()
            models.ccodetrigger.objects.all().delete()
            request.user.message_set.create(message=_(u'All user code lists are deleted.'))
    return django.shortcuts.redirect('/')


def runengine(request,*kw,**kwargs):
    if request.method == 'GET':
            #~ logger = logging.getLogger('bots')
        if os.name=='nt':
            lijst = [sys.executable, os.path.normpath(os.path.join(sys.prefix,'Scripts','bots-engine.py'))]
        elif os.path.exists(os.path.join(sys.prefix,'bin','bots-engine.py')):
            lijst = [os.path.normpath(os.path.join(sys.prefix,'bin','bots-engine.py'))]
        elif os.path.exists(os.path.join(sys.prefix,'local/bin','bots-engine.py')):
            lijst = [os.path.normpath(os.path.join(sys.prefix,'local/bin','bots-engine.py'))]
        else:
            request.user.message_set.create(message=_(u'Bots can not find executable for bots-engine.'))
            #~ logger.info('Bots can not find executable for bots-engine.')
            return django.shortcuts.redirect('/')
            
        try:
            if 'clparameter' in request.GET:
                lijst.append(request.GET['clparameter'])
            #~ logger.info('Run bots-engine with parameters: "%s"',str(lijst))
            terug = subprocess.Popen(lijst).pid
            request.user.message_set.create(message=_(u'Bots-engine is started.'))
            #~ logger.info('Bots-engine is started.')
        except:
            print botslib.txtexc()
            request.user.message_set.create(message=_(u'Errors while trying to run bots-engine.'))
            #~ logger.info('Errors while trying to run bots-engine.')
    return django.shortcuts.redirect('/')

def unlock(request,*kw,**kwargs):
    if request.method == 'GET':
        models.mutex.objects.get(mutexk=1).delete()
        request.user.message_set.create(message=_(u'Unlocked database.'))
    return django.shortcuts.redirect('/')

def sendtestmailmanagers(request,*kw,**kwargs):
    try:
        sendornot = botsglobal.ini.getboolean('settings','sendreportiferror',False)
    except botslib.BotsError:
        sendornot = False
    if not sendornot:
        request.user.message_set.create(message=_(u'In bots.ini, section [settings], "sendreportiferror" is not set (to "True").'))
        return django.shortcuts.redirect('/')
            
    from django.core.mail import mail_managers
    try:
        mail_managers(_(u'testsubject'), _(u'test content of report'))
    except:
        request.user.message_set.create(message=_(u'Sending test report failed: "%s".')%botslib.txtexc())
        return django.shortcuts.redirect('/')
    request.user.message_set.create(message=_(u'Sending test report succeeded.'))
    return django.shortcuts.redirect('/')

