import os
import sys
import time
import zipfile
import zipimport
import operator
import django
from django.core import serializers
from django.utils.translation import ugettext as _
import models
import botslib
import botsglobal
'''
some tabel have 'id' as primary key. This is always an artificial key.
this is not usable for plugins: 'id' is never written to a plugin.
often a tabel with 'id' has an 'unique together' attribute.
than this is used to check if the enty already exists (this is reported).
existing enties are always overwritten.
exeptions:
- confirmrule; there is no clear unique key. AFAICS this will never be a problem.
- translate: may be confusing. But anyway, no existing translate will be overwritten....
'''

#lijst is used for filtering and sorting the plugins. 
lijst = ['uniek','persist','mutex','ta','filereport','report','ccodetrigger','ccode', 'channel','partner','chanpar','translate','routes','confirmrule']


def pluglistcmp(key1,key2):
    return lijst.index(key1) - lijst.index(key2)

def pluglistcmpisgroup(plug1,plug2):
    if plug1['plugintype'] == 'partner' and plug2['plugintype'] == 'partner':
        return  int(plug2['isgroup']) - int(plug1['isgroup'])
    else:
        return 0

def writetodatabase(orgpluglist):
    #sanity checks on pluglist
    if not orgpluglist:  #list of plugins is empty: is OK. DO nothing
        return
    if not isinstance(orgpluglist,list):   #has to be a list!!
        raise Exception(_(u'plugins should be list of dicts. Nothing is written.'))
    for plug in orgpluglist:
        if not isinstance(plug,dict):
            raise botslib.PluginError(_(u'plugins should be list of dicts. Nothing is written.'))
        for key in plug.keys():
            if not isinstance(key,basestring):
                raise botslib.PluginError(_('key of dict is not a string: "%s". Nothing is written.')%(plug))
        if 'plugintype' not in plug:
            raise botslib.PluginError(_(u'"plugintype" missing in: "%s". Nothing is written.')%(plug))
            
    #in bots 1.*, partnrgroup was in seperate tabel; in bots 2.* partnergroup is in partner
    for plug in orgpluglist[:]:
        if plug['plugintype'] == 'partnergroup':
            for plugpartner in orgpluglist:
                if plugpartner['plugintype'] == 'partner' and plugpartner['idpartner'] == plug['idpartner']:
                    if 'group' in plugpartner:
                        plugpartner['group'].append(plug['idpartnergroup'])
                    else:
                        plugpartner['group'] = [plug['idpartnergroup']]
                    break
        
    #copy & filter orgpluglist; do plugtype specific adaptions
    pluglist = []
    for plug in orgpluglist:
        if plug['plugintype'] == 'ccode':   #add ccodetrigger.
            for seachccodetriggerplug in pluglist:
                if seachccodetriggerplug['plugintype']=='ccodetrigger' and seachccodetriggerplug['ccodeid']==plug['ccodeid']:
                    break
            else:
                pluglist.append({'plugintype':'ccodetrigger','ccodeid':plug['ccodeid']})
        elif plug['plugintype'] == 'translate': #make some fields None instead of '' (translate formpartner, topartner)
            if not plug['frompartner']:
                plug['frompartner'] = None
            if not plug['topartner']:
                plug['topartner'] = None
        elif plug['plugintype'] in ['ta','filereport']: #sqlite can have errortexts that are to long. Chop these
            plug['errortext'] = plug['errortext'][:2047]
        elif plug['plugintype'] == 'routes':
            plug['active'] = False
            if not 'defer' in plug:
                plug['defer'] = False
            else:
                if plug['defer'] is None:
                    plug['defer'] = False
        elif plug['plugintype'] == 'confirmrule':
            plug.pop('id', None)       #id is an artificial key, delete,
        elif plug['plugintype'] not in lijst: #filter
            continue
        pluglist.append(plug)
    #sort pluglist: this is needed for relationships
    pluglist.sort(cmp=pluglistcmp,key=operator.itemgetter('plugintype'))
    #2nd sort: 
    pluglist.sort(cmp=pluglistcmpisgroup)
    #~ for plug in pluglist:
        #~ print 'list:',plug
    
    for plug in pluglist:
        botsglobal.logger.info(u'    Start write to database for: "%s".'%plug)
        #~ print '\nstart plug', plug
        table = django.db.models.get_model('bots',plug['plugintype'])
        #~ print table
        
        #delete fields not in model (create compatibility plugin-version)
        loopdictionary = plug.keys()
        for key in loopdictionary:
            try:
                table._meta.get_field(key)
            except django.db.models.fields.FieldDoesNotExist:
                del plug[key]
        #make right key(s)fields (in dict 'sleutel')
        pk = table._meta.pk.name
        if pk == 'id':
            sleutel = {}
            if table._meta.unique_together:
                for key in table._meta.unique_together[0]:
                    sleutel[key]=plug.pop(key)
        else:
            sleutel = {pk:plug.pop(pk)}
        #now we have:
        #- sleutel: unique key fields. mind: translate and confirmrule have empty 'sleutel' now
        #- plug: rest of database fields
        
        #get real column names for fields: for relational fields 
        loopdictionary = plug.keys()
        for fieldname in loopdictionary:
            fieldobject = table._meta.get_field_by_name(fieldname)[0]
            try:
                if fieldobject.column != fieldname:
                    plug[fieldobject.column] = plug[fieldname]
                    del plug[fieldname]
                    #~ print 'replace _id for:',fieldname
            except:
                print 'no field column for:',fieldname
        #get real column names for fields in sleutel
        sleutelorg = sleutel.copy()
        loopdictionary = sleutel.keys()
        for fieldname in loopdictionary:
            fieldobject = table._meta.get_field_by_name(fieldname)[0]
            try:
                if fieldobject.column != fieldname:
                    sleutel[fieldobject.column] = sleutel[fieldname]
                    del sleutel[fieldname]
            except:
                print 'no field column for',fieldname
                
        #~ print 'plug attr',plug
        #~ print '**sleutel',sleutelorg
        
        if sleutelorg:  #translate and confirmrule have empty 'sleutel'
            checkifexistsindb = table.objects.filter(**sleutelorg).all()
            if len(checkifexistsindb)>1:
                raise Exception('not unique?')
            elif len(checkifexistsindb)==1:
                checkifexistsindb[0].delete()
                #~ print 'deleted old enty'
            botsglobal.logger.info(_(u'        Existing entry in database is deleted.'))
            
        dbobject = table(**sleutel)   #create db-object
        if 'idpartner'in sleutel:   #for partners, first the partner needs to be saved before groups can be made
            dbobject.save()
        for key,value in plug.items():
            setattr(dbobject,key,value)
        dbobject.save()
        botsglobal.logger.info(_(u'        Write to database is OK.'))


@django.db.transaction.commit_on_success  #if no exception raised: commit, else rollback.
def load(pathzipfile):
    ''' process uploaded plugin. '''
    #test is valid zipfile
    if not zipfile.is_zipfile(pathzipfile):
        raise botslib.PluginError(_(u'Plugin is not a valid file.'))

    #read index file
    try:
        Zipimporter = zipimport.zipimporter(pathzipfile)
        importedbotsindex = Zipimporter.load_module('botsindex')
        pluglist = importedbotsindex.plugins[:]
        if 'botsindex' in sys.modules:
            del sys.modules['botsindex']
    except:
        txt = botslib.txtexc()
        raise botslib.PluginError(_(u'Error in plugin. Nothing is written. Error: "%s"')%(txt))
    else:
        botsglobal.logger.info(_(u'Plugin is OK.\nStart writing to database.'))
    
    #write content of index file to the bots database
    try:
        writetodatabase(pluglist)
    except:
        txt = botslib.txtexc()
        raise botslib.PluginError('Error writing plugin to database. Nothing is written. Error: "%s"'%(txt))
    else:
        botsglobal.logger.info(u'Writing to database is OK.\nStart writing to files')
    
    #write files to the file system.
    try:
        warnrenamed = False     #to report in GUI files have been overwritten.
        z = zipfile.ZipFile(pathzipfile, mode="r")
        orgtargetpath = botsglobal.ini.get('directories','botspath')
        if (orgtargetpath[-1:] in (os.path.sep, os.path.altsep) and len(os.path.splitdrive(orgtargetpath)[1]) > 1):
            orgtargetpath = orgtargetpath[:-1]
        for f in z.infolist():
            if f.filename not in ['botsindex.py','README','botssys/sqlitedb/botsdb','config/bots.ini'] and os.path.splitext(f.filename)[1] not in ['.pyo','.pyc']:
                #~ botsglobal.logger.info(u'filename in zip "%s".',f.filename)                
                if f.filename[0] == '/':
                    targetpath = f.filename[1:]
                else:
                    targetpath = f.filename
                targetpath = targetpath.replace('usersys',botsglobal.ini.get('directories','usersysabs'),1)
                targetpath = targetpath.replace('botssys',botsglobal.ini.get('directories','botssys'),1)
                targetpath = botslib.join(orgtargetpath, targetpath)
                #targetpath is OK now.
                botsglobal.logger.info(_(u'    Start writing file: "%s".'),targetpath)
                
                if botslib.dirshouldbethere(os.path.dirname(targetpath)):
                    botsglobal.logger.info(_(u'        Create directory "%s".'),os.path.dirname(targetpath))
                if f.filename[-1] == '/':    #check if this is a dir; if so continue
                    continue
                if os.path.isfile(targetpath):  #check if file already exists
                    try:    #this ***sometimes*** fails. (python25, for static/help/home.html...only there...)
                        os.rename(targetpath,targetpath+'.'+time.strftime('%Y%m%d%H%M%S'))
                        warnrenamed=True
                        botsglobal.logger.info(_(u'        Renamed existing file "%(from)s" to "%(to)s".'),{'from':targetpath,'to':targetpath+time.strftime('%Y%m%d%H%M%S')})
                    except:
                        pass
                source = z.read(f.filename)
                target = open(targetpath, "wb")
                target.write(source)
                target.close()
                botsglobal.logger.info(_(u'        File written: "%s".'),targetpath)
    except:
        txt = botslib.txtexc()
        z.close()
        raise botslib.PluginError(_(u'Error writing files to system. Nothing is written to database. Error: "%s"')%(txt))
    else:
        z.close()
        botsglobal.logger.info(_(u'Writing files to filesystem is OK.'))
        return warnrenamed

def dump(filename,function):    #filename is without extension!
    database2indexfile(filename,function)
    pluginzipfilehandler = zipfile.ZipFile(filename+'.zip', 'w')
    pluginzipfilehandler.write(filename+'.py','botsindex.py')   #write index file to pluginfile
    os.remove(filename+'.py')
    files2plugin(pluginzipfilehandler,function)
    pluginzipfilehandler.close()

def database2indexfile(filename,function):
    db_objects = \
            list(models.ccodetrigger.objects.all()) + \
            list(models.ccode.objects.all())
    if function in ['configuration','snapshot']:
        db_objects += \
            list(models.channel.objects.all()) + \
            list(models.partner.objects.all()) + \
            list(models.chanpar.objects.all()) + \
            list(models.translate.objects.all()) +  \
            list(models.routes.objects.all()) +  \
            list(models.confirmrule.objects.all())
        if function=='snapshot':
            db_objects += \
                list(models.uniek.objects.all()) + \
                list(models.mutex.objects.all()) + \
                list(models.ta.objects.all()) + \
                list(models.filereport.objects.all()) + \
                list(models.report.objects.all())
                #~ list(models.persist.objects.all()) + \
    orgplugs = serializers.serialize("python", db_objects)
    #~ print orgpluglist
    #convertedplugs = []
    f = open(filename + '.py','wb')
    f.write('import datetime\n')
    f.write('version = 2\n')
    f.write('plugins = [\n')
    for plug in orgplugs:
        app,tablename = plug['model'].split('.',1)
        plug['fields']['plugintype'] = tablename
        table = django.db.models.get_model(app,tablename)
        pk = table._meta.pk.name
        if pk != 'id':
            plug['fields'][pk] = plug['pk']
        #convertedplugs.append(plug['fields'])
        f.write(repr(plug['fields'])+',\n')
        botsglobal.logger.debug(u'    write in index: %s',plug['fields'])
        #check confirmrule: id is non-artificla key?
    #f.write(repr(convertedplugs))
    f.write(']\n')
    f.close()
    
def files2plugin(pluginzipfilehandler,function):
    if function=='codelist':
        return
    #get usersys files
    usersys = botsglobal.ini.get('directories','usersysabs')
    files2pluginbydir(function,pluginzipfilehandler,usersys,'usersys')
    
    botssys = botsglobal.ini.get('directories','botssys')
    if function=='snapshot':
        #get config files
        config = botsglobal.ini.get('directories','config')
        files2pluginbydir(function,pluginzipfilehandler,config,'config')
        #get data files
        data = botsglobal.ini.get('directories','data')
        files2pluginbydir(function,pluginzipfilehandler,data,'botssys/data')
        #get log files
        log_file = botsglobal.ini.get('directories','logging')
        files2pluginbydir(function,pluginzipfilehandler,log_file,'botssys/logging')
        #get sqlite database
        files2pluginbydir(function,pluginzipfilehandler,os.path.join(botssys,'sqlitedb'),'botssys/sqlitedb.copy')
    else:
        files2pluginbydir(function,pluginzipfilehandler,os.path.join(botssys,'infile'),'botssys/infile')


def files2pluginbydir(function,pluginzipfilehandler,dirname,defaultdirname):
    onlysnapshotdirs = [os.path.normpath(x) for x in ['usersys/charsets']]
    for root, dirs, files in os.walk(dirname):
        head, tail = os.path.split(root)
        if tail in ['.svn']:
            del dirs[:]     #os.walk will not look in subdirecties 
            continue        #skip this .svn directory
        rootinplugin = root.replace(dirname,defaultdirname,1)
        if function != 'snapshot':
            if rootinplugin in onlysnapshotdirs:    #do not use charsets in configuration plugin
                del dirs[:]
                continue
        for bestand in files:
            ext = os.path.splitext(bestand)[1]
            if ext in ['.pyc','.pyo'] or bestand in ['__init__.py']:
                continue
            pluginzipfilehandler.write(os.path.join(root,bestand),os.path.join(rootinplugin,bestand))
            botsglobal.logger.debug(_(u'    write file "%s".'),os.path.join(rootinplugin,bestand))

