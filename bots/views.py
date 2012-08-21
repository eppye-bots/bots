import sys
import os
import time
import shutil
import subprocess
import traceback
import django
from django.utils.translation import ugettext as _
import forms
import models
import viewlib
import botslib
import pluglib
import botsglobal
from botsconfig import *

def server_error(request, template_name='500.html'):
    """ the 500 error handler.
        Templates: `500.html`
        Context: None
    """
    exc_info = traceback.format_exc(None).decode('utf-8','ignore')
    botsglobal.logger.info(_(u'Ran into server error: "%s"'),str(exc_info))
    temp = django.template.loader.get_template(template_name)  #You need to create a 500.html template.
    return django.http.HttpResponseServerError(temp.render(django.template.Context({'exc_info':exc_info})))

def index(request,*kw,**kwargs):
    return django.shortcuts.render_to_response('admin/base.html', {},context_instance=django.template.RequestContext(request))

def home(request,*kw,**kwargs):
    return django.shortcuts.render_to_response('bots/about.html', {'botsinfo':botslib.botsinfo()},context_instance=django.template.RequestContext(request))

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
            request.POST = viewlib.changepostparameters(request.POST,soort='in2out')
            return outgoing(request)
        elif '2process' in request.POST:        #coming from ViewIncoming, go to outgoing form using same criteria
            request.POST = viewlib.changepostparameters(request.POST,soort='2process')
            return process(request)
        elif '2confirm' in request.POST:        #coming from ViewIncoming, go to outgoing form using same criteria
            request.POST = viewlib.changepostparameters(request.POST,soort='in2confirm')
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
                idta = request.POST[u'retransmit']
                filereport = models.filereport.objects.get(idta=int(idta))
                filereport.retransmit = not filereport.retransmit
                filereport.save()
            elif 'delete' in request.POST:        #coming from ViewIncoming
                idta = int(request.POST[u'delete'])
                #~ query = models.filereport.objects.filter(idta=int(idta)).all().delete()
                models.filereport.objects.filter(idta=idta).delete()
                ta_object = models.ta.objects.get(idta=idta)
                viewlib.gettrace(ta_object)
                viewlib.trace2delete(ta_object)
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
            request.POST = viewlib.changepostparameters(request.POST,soort='out2in')
            return incoming(request)
        elif '2process' in request.POST:        #coming from ViewIncoming, go to outgoing form using same criteria
            request.POST = viewlib.changepostparameters(request.POST,soort='2process')
            return process(request)
        elif '2confirm' in request.POST:        #coming from ViewIncoming, go to outgoing form using same criteria
            request.POST = viewlib.changepostparameters(request.POST,soort='out2confirm')
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
                ta_object = models.ta.objects.get(idta=int(request.POST[u'retransmit']))
                ta_object.retransmit = not ta_object.retransmit
                ta_object.save()
            elif 'resendall' in request.POST:
                #select all objects with parameters and set retransmit
                query = models.ta.objects.filter(status=EXTERNOUT).all()
                outgoingfiles = viewlib.filterquery2(query,formin.cleaned_data)
                for outgoingfile in outgoingfiles:
                    outgoingfile.retransmit = not outgoingfile.retransmit
                    outgoingfile.save()
            else:                                    #coming from ViewIncoming
                viewlib.handlepagination(request.POST,formin.cleaned_data)
        cleaned_data = formin.cleaned_data

    #~ query = models.ta.objects.filter(status=EXTERNOUT,statust=DONE).all()
    query = models.ta.objects.filter(status=EXTERNOUT).all()
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
    #~ from django.db import connections
    #~ print django.db.connection.queries
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
            request.POST = viewlib.changepostparameters(request.POST,soort='fromprocess')
            return incoming(request)
        elif '2outgoing' in request.POST:        #coming from ViewIncoming, go to outgoing form using same criteria
            request.POST = viewlib.changepostparameters(request.POST,soort='fromprocess')
            return outgoing(request)
        elif 'fromselect' in request.POST:        #coming from select criteria screen
            formin = forms.SelectProcess(request.POST)
            if not formin.is_valid():
                return viewlib.render(request,formin)
        else:
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
        if 'inidta' in request.GET: #detail for incoming screen
            rootta = models.ta.objects.get(idta=int(request.GET['inidta']))
        else:                       #detail for outgoing: trace back to EXTERNIN first
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
            request.POST = viewlib.changepostparameters(request.POST,soort='confirm2in')
            return incoming(request)
        elif '2outgoing' in request.POST:        #coming from ViewIncoming, go to outgoing form using same criteria
            request.POST = viewlib.changepostparameters(request.POST,soort='confirm2out')
            return outgoing(request)
        elif 'fromselect' in request.POST:        #coming from select criteria screen
            formin = forms.SelectConfirm(request.POST)
            if not formin.is_valid():
                return viewlib.render(request,formin)
        elif 'confirm' in request.POST:        #coming from 'star' menu 'Manual confirm'
            ta_object = models.ta.objects.get(idta=int(request.POST[u'confirm']))
            if ta_object.confirmed == False and ta_object.confirmtype.startswith('ask'):
                ta_object.confirmed = True
                ta_object.confirmidta = '-1'   # to indicate a manual confirmation
                ta_object.save()
                request.user.message_set.create(message='Manual confirmed.')
            else:
                request.user.message_set.create(message='Manual confirm not possible.')
            # then just refresh the current view
            formin = forms.ViewConfirm(request.POST)
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
    if request.method == 'GET':
        try:
            idta = request.GET['idta']
            if idta == 0: #for the 'starred' file names (eg multiple output)
                raise Exception('to be caught')
                
            currentta = list(models.ta.objects.filter(idta=idta))[0]
            if request.GET['action'] == 'downl':
                response = django.http.HttpResponse(mimetype=currentta.contenttype)
                if  currentta.contenttype == 'text/html':
                    dispositiontype = 'inline'
                else:
                    dispositiontype = 'attachment'
                response['Content-Disposition'] = dispositiontype + '; filename=' + currentta.filename + '.txt'
                #~ response['Content-Length'] = os.path.getsize(absfilename)
                response.write(botslib.readdata(currentta.filename,charset=currentta.charset,errors='ignore'))
                return response
            elif request.GET['action'] == 'previous':
                if currentta.parent:    #has a explicit parent
                    talijst = list(models.ta.objects.filter(idta=currentta.parent))
                else:                   #get list of ta's referring to this idta as child
                    talijst = list(models.ta.objects.filter(child=currentta.idta))
            elif request.GET['action'] == 'this':
                if currentta.status == EXTERNIN:        #EXTERNIN can not be displayed, so go to first FILEIN
                    talijst = list(models.ta.objects.filter(parent=currentta.idta))
                elif currentta.status == EXTERNOUT:     #EXTERNOUT can not be displayed, so go to last FILEOUT
                    talijst = list(models.ta.objects.filter(idta=currentta.parent))
                else:
                    talijst = [currentta]
            elif request.GET['action'] == 'next':
                if currentta.child:     #has a explicit child
                    talijst = list(models.ta.objects.filter(idta=currentta.child))
                else:
                    talijst = list(models.ta.objects.filter(parent=currentta.idta))
            for ta_object in talijst:
                #determine if can display file
                ta_object.has_file = False
                if ta_object.filename and ta_object.filename.isdigit():
                    try:
                        if ta_object.charset:  #guess charset if not available; uft-8 is reasonable
                            ta_object.content = botslib.readdata(ta_object.filename,charset=ta_object.charset,errors='ignore')
                        else:
                            ta_object.content = botslib.readdata(ta_object.filename,charset='utf-8',errors='ignore')
                        ta_object.has_file = True
                    except:
                        pass
                if not ta_object.has_file:
                    ta_object.content = _(u'No file available for display.')
                #determine has previous:
                if ta_object.parent or ta_object.status == MERGED:
                    ta_object.has_previous = True
                else:
                    ta_object.has_previous = False
                #determine: has next:
                if ta_object.status == EXTERNOUT or ta_object.statust in [OPEN,ERROR]:
                    ta_object.has_next = False
                else:
                    ta_object.has_next = True
            return  django.shortcuts.render_to_response('bots/filer.html', {'idtas': talijst},context_instance=django.template.RequestContext(request))
        except:
            #~ print botslib.txtexc()
            return  django.shortcuts.render_to_response('bots/filer.html', {'error_content': _(u'No such file.')},context_instance=django.template.RequestContext(request))

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
                except botslib.PluginError,msg:
                    botsglobal.logger.info(u'%s',str(msg))
                    request.user.message_set.create(message='%s'%msg)
                else:
                    botsglobal.logger.info(_(u'Finished reading plugin "%s" successful.'),request.FILES['file'].name)
                    request.user.message_set.create(message='Plugin "%s" is read successful.'%request.FILES['file'].name)
                request.FILES['file'].close()
            else:
                request.user.message_set.create(message=_(u'No plugin read.'))
        return django.shortcuts.redirect('/home')

def plugout(request,*kw,**kwargs):
    if request.method == 'GET':
        form = forms.PlugoutForm()
        return  django.shortcuts.render_to_response('bots/plugout.html', {'form': form},context_instance=django.template.RequestContext(request))
    else:
        if 'submit' in request.POST:
            form = forms.PlugoutForm(request.POST)
            if form.is_valid():
                filename = botslib.join(botsglobal.ini.get('directories','botssys'),'plugin_temp.zip')
                botsglobal.logger.info(_(u'Start writing plugin "%s".'),filename)
                try:
                    pluglib.plugoutcore(form.cleaned_data,filename)
                except botslib.PluginError, msg:
                    botsglobal.logger.info(u'%s',str(msg))
                    request.user.message_set.create(message='%s'%msg)
                else:
                    botsglobal.logger.info(_(u'Plugin "%s" created successful.'),filename)
                    response = django.http.HttpResponse(open(filename, 'rb').read(), content_type='application/zip')
                    # response['Content-Length'] = os.path.getsize(filename)
                    response['Content-Disposition'] = 'attachment; filename=' + 'plugin' + time.strftime('_%Y%m%d') + '.zip'
                    return response
    return django.shortcuts.redirect('/home')

def delete(request,*kw,**kwargs):
    if request.method == 'GET':
        form = forms.DeleteForm()
        return  django.shortcuts.render_to_response('bots/delete.html', {'form': form},context_instance=django.template.RequestContext(request))
    else:
        if 'submit' in request.POST:
            form = forms.DeleteForm(request.POST)
            if form.is_valid():
                botsglobal.logger.info(_(u'Start deleting in configuration.'))
                if form.cleaned_data['deltransactions']:
                    #while testing with very big loads, deleting transaction when wrong. Using raw SQL solved this.
                    from django.db import connection, transaction
                    cursor = connection.cursor()
                    cursor.execute("DELETE FROM ta")
                    cursor.execute("DELETE FROM filereport")
                    cursor.execute("DELETE FROM report")
                    transaction.commit_unless_managed()
                    request.user.message_set.create(message=_(u'Transactions are deleted.'))
                    botsglobal.logger.info(_(u'    Transactions are deleted.'))
                    #clean data files
                    deletefrompath = botsglobal.ini.get('directories','data','botssys/data')
                    shutil.rmtree(deletefrompath,ignore_errors=True)
                    botslib.dirshouldbethere(deletefrompath)
                    request.user.message_set.create(message=_(u'Data files are deleted.'))
                    botsglobal.logger.info(_(u'    Data files are deleted.'))
                if form.cleaned_data['delconfiguration']:
                    models.confirmrule.objects.all().delete()
                    models.channel.objects.all().delete()
                    models.chanpar.objects.all().delete()
                    models.partner.objects.all().delete()
                    models.translate.objects.all().delete()
                    models.routes.objects.all().delete()
                    request.user.message_set.create(message=_(u'Database configuration is deleted.'))
                    botsglobal.logger.info(_(u'    Database configuration is deleted.'))
                if form.cleaned_data['delcodelists']:
                    models.ccode.objects.all().delete()
                    models.ccodetrigger.objects.all().delete()
                    request.user.message_set.create(message=_(u'User code lists are deleted.'))
                    botsglobal.logger.info(_(u'    User code lists are deleted.'))
                if form.cleaned_data['delinfile']:
                    deletefrompath = botslib.join(botsglobal.ini.get('directories','botssys','botssys'),'infile')
                    shutil.rmtree('bots/botssys/infile',ignore_errors=True)
                    request.user.message_set.create(message=_(u'Files in botssys/infile are deleted.'))
                    botsglobal.logger.info(_(u'    Files in botssys/infile are deleted.'))
                if form.cleaned_data['deloutfile']:
                    deletefrompath = botslib.join(botsglobal.ini.get('directories','botssys','botssys'),'outfile')
                    shutil.rmtree('bots/botssys/outfile',ignore_errors=True)
                    request.user.message_set.create(message=_(u'Files in botssys/outfile are deleted.'))
                    botsglobal.logger.info(_(u'    Files in botssys/outfile are deleted.'))
                if form.cleaned_data['deluserscripts']:
                    deletefrompath = botsglobal.ini.get('directories','usersysabs')
                    for root, dirs, files in os.walk(deletefrompath):
                        head, tail = os.path.split(root)
                        if tail == 'charsets':
                            del dirs[:]
                            continue
                        for bestand in files:
                            if bestand != '__init__.py':
                                os.remove(os.path.join(root,bestand))
                    request.user.message_set.create(message=_(u'User scripts are deleted (in usersys).'))
                    botsglobal.logger.info(_(u'    User scripts are deleted (in usersys).'))
                elif form.cleaned_data['delbackup']:
                    deletefrompath = botsglobal.ini.get('directories','usersysabs')
                    for root, dirs, files in os.walk(deletefrompath):
                        head, tail = os.path.split(root)
                        if tail == 'charsets':
                            del dirs[:]
                            continue
                        for bestand in files:
                            name,ext = os.path.splitext(bestand)
                            if ext and len(ext) == 15 and ext[1:].isdigit() :
                                os.remove(os.path.join(root,bestand))
                    request.user.message_set.create(message=_(u'Backupped user scripts are deleted/purged (in usersys).'))
                    botsglobal.logger.info(_(u'    Backupped user scripts are deleted/purged (in usersys).'))
                botsglobal.logger.info(_(u'Finished deleting in configuration.'))
    return django.shortcuts.redirect('/home')


def runengine(request,*kw,**kwargs):
    if request.method == 'GET':
        #check if bots-engine is not already running (unless attempting crashrecovery)
        if list(models.mutex.objects.filter(mutexk=1).all()) and request.GET['clparameter'] != '--crashrecovery':
            request.user.message_set.create(message=_(u'Trying to run "bots-engine", but database is locked by another run in progress. Please try again later.'))
            botsglobal.logger.info(_(u'Trying to run "bots-engine", but database is locked by another run in progress.'))
            return django.shortcuts.redirect('/home')
        #find out the right arguments to use
        botsenginepath = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])),'bots-engine.py')        #find the bots-engine
        lijst = [sys.executable,botsenginepath] + sys.argv[1:]
        if 'clparameter' in request.GET:
            lijst.append(request.GET['clparameter'])

        try:
            botsglobal.logger.info(_(u'Run bots-engine with parameters: "%s"'),str(lijst))
            terug = subprocess.Popen(lijst).pid
            request.user.message_set.create(message=_(u'Bots-engine is started.'))
        except:
            txt =  botslib.txtexc()
            request.user.message_set.create(message=_(u'Errors while trying to run bots-engine.'))
            botsglobal.logger.info(_(u'Errors while trying to run bots-engine:\n%s.'),txt)
    return django.shortcuts.redirect('/home')

def unlock(request,*kw,**kwargs):
    if request.method == 'GET':
        lijst = list(models.mutex.objects.filter(mutexk=1).all())
        if lijst:
            lijst[0].delete()
            request.user.message_set.create(message=_(u'Unlocked database.'))
            botsglobal.logger.info(_(u'Unlocked database.'))
        else:
            request.user.message_set.create(message=_(u'Request to unlock database, but database was not locked.'))
            botsglobal.logger.info(_(u'Request to unlock database, but database was not locked.'))
    return django.shortcuts.redirect('/home')

def sendtestmailmanagers(request,*kw,**kwargs):
    try:
        sendornot = botsglobal.ini.getboolean('settings','sendreportiferror',False)
    except botslib.BotsError:
        sendornot = False
    if not sendornot:
        botsglobal.logger.info(_(u'Trying to send test mail, but in bots.ini, section [settings], "sendreportiferror" is not "True".'))
        request.user.message_set.create(message=_(u'Trying to send test mail, but in bots.ini, section [settings], "sendreportiferror" is not "True".'))
        return django.shortcuts.redirect('/home')

    from django.core.mail import mail_managers
    try:
        mail_managers(_(u'testsubject'), _(u'test content of report'))
    except:
        txt = botslib.txtexc()
        request.user.message_set.create(message=_(u'Sending test mail failed.'))
        botsglobal.logger.info(_(u'Sending test mail failed, error:\n%s'), txt)
        return django.shortcuts.redirect('/home')
    request.user.message_set.create(message=_(u'Sending test mail succeeded.'))
    botsglobal.logger.info(_(u'Sending test mail succeeded.'))
    return django.shortcuts.redirect('/home')

