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
#~ some tabel have 'id' as primary key. This is always an artificial key.
#~ this is not usable for plugins: 'id' is never written to a plugin.
#~ often a tabel with 'id' has an 'unique together' attribute.
#~ than this is used to check if the entry already exists (this is reported).
#~ existing entries are always overwritten.
#~ exceptions:
#~ - confirmrule; there is no clear unique key. AFAICS this will never be a problem.
#~ - translate: may be confusing. But anyway, no existing translate will be overwritten....

#PLUGINCOMPARELIST is used for filtering and sorting the plugins.
PLUGINCOMPARELIST = ['uniek','persist','mutex','ta','filereport','report','ccodetrigger','ccode', 'channel','partner','chanpar','translate','routes','confirmrule']


def pluglistcmp(key1,key2):
    #sort by PLUGINCOMPARELIST
    return PLUGINCOMPARELIST.index(key1) - PLUGINCOMPARELIST.index(key2)

def pluglistcmpisgroup(plug1,plug2):
    #sort partnergroups before parters
    if plug1['plugintype'] == 'partner' and plug2['plugintype'] == 'partner':
        return  int(plug2['isgroup']) - int(plug1['isgroup'])
    else:
        return 0

def writetodatabase(orgpluglist):
    #sanity checks on pluglist
    if not orgpluglist:  #list of plugins is empty: is OK. DO nothing
        return
    if not isinstance(orgpluglist,list):   #has to be a list!!
        raise botslib.PluginError(_(u'plugins should be list of dicts. Nothing is written.'))
    for plug in orgpluglist:
        if not isinstance(plug,dict):
            raise botslib.PluginError(_(u'plugins should be list of dicts. Nothing is written.'))
        for key in plug.keys():
            if not isinstance(key,basestring):
                raise botslib.PluginError(_(u'key of dict is not a string: "%s". Nothing is written.')%(plug))
        if 'plugintype' not in plug:
            raise botslib.PluginError(_(u'"plugintype" missing in: "%s". Nothing is written.')%(plug))

    #special case: compatibility with bots 1.* plugins.
    #in bots 1.*, partnergroup was in separate tabel; in bots 2.* partnergroup is in partner
    #later on, partnergroup will get filtered
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
        if plug['plugintype'] == 'ccode':   #add ccodetrigger. #20101223: this is NOT needed; codetrigger shoudl be in plugin.
            for seachccodetriggerplug in pluglist:
                if seachccodetriggerplug['plugintype'] == 'ccodetrigger' and seachccodetriggerplug['ccodeid'] == plug['ccodeid']:
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
        elif plug['plugintype'] not in PLUGINCOMPARELIST:   #if not in PLUGINCOMPARELIST: do not use
            continue
        pluglist.append(plug)
    #sort pluglist: this is needed for relationships
    pluglist.sort(cmp=pluglistcmp,key=operator.itemgetter('plugintype'))
    #2nd sort: sort partenergroups before partners
    pluglist.sort(cmp=pluglistcmpisgroup)
    #~ for plug in pluglist:
        #~ print 'list:',plug

    for plug in pluglist:
        botsglobal.logger.info(u'    Start write to database for: "%s".'%plug)
        #remember the plugintype
        plugintype = plug['plugintype']
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

        #get key(s), put in dict 'sleutel'
        pk = table._meta.pk.name
        if pk == 'id':
            sleutel = {}
            if table._meta.unique_together:
                for key in table._meta.unique_together[0]:
                    sleutel[key] = plug.pop(key)
        else:
            sleutel = {pk:plug.pop(pk)}

        #now we have:
        #- sleutel: unique key fields. mind: translate and confirmrule have empty 'sleutel' now
        #- plug: rest of database fields
        sleutelorg = sleutel.copy()     #make a copy of the original sleutel; this is needed later

        #get real column names for fields in plug
        loopdictionary = plug.keys()
        for fieldname in loopdictionary:
            fieldobject = table._meta.get_field_by_name(fieldname)[0]
            try:
                if fieldobject.column != fieldname:     #if name in plug is not the real field name (in database)
                    plug[fieldobject.column] = plug[fieldname]  #add new key in plug
                    del plug[fieldname]                         #delete old key in plug
                    #~ print 'replace _id for:',fieldname
            except:
                print 'no field column for:',fieldname          #should this be raised?

        #get real column names for fields in sleutel; basically the same loop but now for sleutel
        loopdictionary = sleutel.keys()
        for fieldname in loopdictionary:
            fieldobject = table._meta.get_field_by_name(fieldname)[0]
            try:
                if fieldobject.column != fieldname:
                    sleutel[fieldobject.column] = sleutel[fieldname]
                    del sleutel[fieldname]
            except:
                print 'no field column for',fieldname
        #now we have:
        #- sleutel: unique key fields. mind: translate and confirmrule have empty 'sleutel' now
        #- sleutelorg: original key fields
        #- plug: rest of database fields
        #- plugintype
        #all fields have the right database name

        #~ print 'plug attr',plug
        #~ print 'orgsleutel',sleutelorg
        #~ print 'sleutel',sleutel

        #existing ccodetriggers are not overwritten (as deleting ccodetrigger also deletes ccodes)
        if plugintype == 'ccodetrigger':
            listexistingentries = table.objects.filter(**sleutelorg).all()
            if listexistingentries:
                continue
        #now find the entry using the keys in sleutelorg; delete the existing entry.
        elif sleutelorg:  #not for translate and confirmrule; these have an have an empty 'sleutel'
            listexistingentries = table.objects.filter(**sleutelorg).all()
        elif plugintype == 'translate':   #for translate: delete existing entry
            listexistingentries = table.objects.filter(fromeditype=plug['fromeditype'],frommessagetype=plug['frommessagetype'],alt=plug['alt'],frompartner=plug['frompartner_id'],topartner=plug['topartner_id']).all()
        elif plugintype == 'confirmrule':   #for confirmrule: delete existing entry; but how to find this??? what are keys???
            listexistingentries = table.objects.filter(confirmtype=plug['confirmtype'],
                                                        ruletype=plug['ruletype'],
                                                        negativerule=plug['negativerule'],
                                                        idroute=plug.get('idroute'),
                                                        idchannel=plug.get('idchannel_id'),
                                                        editype=plug.get('editype'),
                                                        messagetype=plug.get('messagetype'),
                                                        frompartner=plug.get('frompartner_id'),
                                                        topartner=plug.get('topartner_id')).all()

        if listexistingentries:
            for entry in listexistingentries:
                entry.delete()
            botsglobal.logger.info(_(u'        Existing entry in database is deleted.'))

        dbobject = table(**sleutel)   #create db-object
        if plugintype == 'partner':   #for partners, first the partner needs to be saved before groups can be made
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
        myzipimport = zipimport.zipimporter(pathzipfile)
        importedbotsindex = myzipimport.load_module('botsindex')
        pluglist = importedbotsindex.plugins[:]
        if 'botsindex' in sys.modules:
            del sys.modules['botsindex']
    except:
        txt = botslib.txtexc()
        raise botslib.PluginError(_(u'Error in plugin. Nothing is written. Error:\n%s')%(txt))
    else:
        botsglobal.logger.info(_(u'Plugin is OK.'))
        botsglobal.logger.info(_(u'Start writing to database.'))

    #write content of index file to the bots database
    try:
        writetodatabase(pluglist)
    except:
        txt = botslib.txtexc()
        raise botslib.PluginError(_(u'Error writing plugin to database. Nothing is written. Error:\n%s'%(txt)))
    else:
        botsglobal.logger.info(u'Writing to database is OK.')
        botsglobal.logger.info(u'Start writing to files')

    #write files to the file system.
    try:
        warnrenamed = False     #to report in GUI files have been overwritten.
        myzip = zipfile.ZipFile(pathzipfile, mode="r")
        orgtargetpath = botsglobal.ini.get('directories','botspath')
        if (orgtargetpath[-1:] in (os.path.sep, os.path.altsep) and len(os.path.splitdrive(orgtargetpath)[1]) > 1):
            orgtargetpath = orgtargetpath[:-1]
        for zipfileobject in myzip.infolist():
            if zipfileobject.filename not in ['botsindex.py','README','botssys/sqlitedb/botsdb','config/bots.ini'] and os.path.splitext(zipfileobject.filename)[1] not in ['.pyo','.pyc']:
                #~ botsglobal.logger.info(u'filename in zip "%s".',zipfileobject.filename)
                if zipfileobject.filename[0] == '/':
                    targetpath = zipfileobject.filename[1:]
                else:
                    targetpath = zipfileobject.filename
                targetpath = targetpath.replace('usersys',botsglobal.ini.get('directories','usersysabs'),1)
                targetpath = targetpath.replace('botssys',botsglobal.ini.get('directories','botssys'),1)
                targetpath = botslib.join(orgtargetpath, targetpath)
                #targetpath is OK now.
                botsglobal.logger.info(_(u'    Start writing file: "%s".'),targetpath)

                if botslib.dirshouldbethere(os.path.dirname(targetpath)):
                    botsglobal.logger.info(_(u'        Create directory "%s".'),os.path.dirname(targetpath))
                if zipfileobject.filename[-1] == '/':    #check if this is a dir; if so continue
                    continue
                if os.path.isfile(targetpath):  #check if file already exists
                    try:    #this ***sometimes*** fails. (python25, for static/help/home.html...only there...)
                        os.rename(targetpath,targetpath+'.'+time.strftime('%Y%m%d%H%M%S'))
                        warnrenamed = True
                        botsglobal.logger.info(_(u'        Renamed existing file "%(from)s" to "%(to)s".'),{'from':targetpath,'to':targetpath+time.strftime('%Y%m%d%H%M%S')})
                    except:
                        pass
                source = myzip.read(zipfileobject.filename)
                target = open(targetpath, "wb")
                target.write(source)
                target.close()
                botsglobal.logger.info(_(u'        File written: "%s".'),targetpath)
    except:
        txt = botslib.txtexc()
        myzip.close()
        raise botslib.PluginError(_(u'Error writing files to system. Nothing is written to database. Error:\n%s')%(txt))
    else:
        myzip.close()
        botsglobal.logger.info(_(u'Writing files to filesystem is OK.'))
        return warnrenamed

#*************************************************************
# generate a plugin (plugout)
#*************************************************************
def plugoutcore(cleaned_data,filename):
    pluginzipfilehandler = zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED)

    tmpbotsindex = plugout_database(cleaned_data)
    pluginzipfilehandler.writestr('botsindex.py',tmpbotsindex)      #write index file to pluginfile

    files4plugin = plugout_files(cleaned_data)
    for dirname, defaultdirname in files4plugin:
        pluginzipfilehandler.write(dirname,defaultdirname)
        botsglobal.logger.debug(_(u'    write file "%s".'),defaultdirname)

    pluginzipfilehandler.close()

def plugout_database(cleaned_data):
    #collect all database objects
    db_objects = []
    if cleaned_data['databaseconfiguration']:
        db_objects += \
            list(models.channel.objects.all()) + \
            list(models.partner.objects.all()) + \
            list(models.chanpar.objects.all()) + \
            list(models.translate.objects.all()) +  \
            list(models.routes.objects.all()) +  \
            list(models.confirmrule.objects.all())
    if cleaned_data['umlists']:
        db_objects += \
            list(models.ccodetrigger.objects.all()) + \
            list(models.ccode.objects.all())
    if cleaned_data['databasetransactions']:
        db_objects += \
            list(models.uniek.objects.all()) + \
            list(models.mutex.objects.all()) + \
            list(models.ta.objects.all()) + \
            list(models.filereport.objects.all()) + \
            list(models.report.objects.all())
            #~ list(models.persist.objects.all()) + \       #commetned out......does this need testing?
    #serialize database objects
    orgplugs = serializers.serialize("python", db_objects)
    #write serialized objects to str/buffer
    tmpbotsindex = u'import datetime\nversion = 2\nplugins = [\n'
    for plug in orgplugs:
        app,tablename = plug['model'].split('.',1)
        plug['fields']['plugintype'] = tablename
        table = django.db.models.get_model(app,tablename)
        pk = table._meta.pk.name
        if pk != 'id':
            plug['fields'][pk] = plug['pk']
        tmpbotsindex += repr(plug['fields']) + u',\n'
        botsglobal.logger.debug(u'    write in index: %s',plug['fields'])
        #check confirmrule: id is non-artifical key?
    tmpbotsindex += u']\n'
    return tmpbotsindex

def plugout_files(cleaned_data):
    ''' gather list of files for the plugin that is generated '''
    files2return = []
    usersys = botsglobal.ini.get('directories','usersysabs')
    botssys = botsglobal.ini.get('directories','botssys')
    if cleaned_data['fileconfiguration']:       #gather from usersys
        files2return.extend(plugout_files_bydir(usersys,'usersys'))
        if not cleaned_data['charset']:     #if edifact charsets are not needed: remove them (are included in default bots installation).
            charsetdirs = plugout_files_bydir(os.path.join(usersys,'charsets'),'usersys/charsets')
            for charset in charsetdirs:
                try:
                    index = files2return.index(charset)
                    files2return.pop(index)
                except ValueError:
                    pass
    if cleaned_data['config']:
        config = botsglobal.ini.get('directories','config')
        files2return.extend(plugout_files_bydir(config,'config'))
    if cleaned_data['data']:
        data = botsglobal.ini.get('directories','data')
        files2return.extend(plugout_files_bydir(data,'botssys/data'))
    if cleaned_data['database']:
        files2return.extend(plugout_files_bydir(os.path.join(botssys,'sqlitedb'),'botssys/sqlitedb.copy'))  #yeah...readign a plugin with a new database will cause a crash...do this manually...
    if cleaned_data['infiles']:
        files2return.extend(plugout_files_bydir(os.path.join(botssys,'infile'),'botssys/infile'))
    if cleaned_data['logfiles']:
        log_file = botsglobal.ini.get('directories','logging')
        files2return.extend(plugout_files_bydir(log_file,'botssys/logging'))
    return files2return

def plugout_files_bydir(dirname,defaultdirname):
    ''' gather all files from directory dirname'''
    files2return = []
    for root, dirs, files in os.walk(dirname):
        head, tail = os.path.split(root)
        if tail in ['.svn']:    #skip .svn directries
            del dirs[:]     #os.walk will not look in subdirectories
            continue
        rootinplugin = root.replace(dirname,defaultdirname,1)
        for bestand in files:
            ext = os.path.splitext(bestand)[1]
            if ext and (ext in ['.pyc','.pyo'] or bestand in ['__init__.py'] or (len(ext) == 15 and ext[1:].isdigit())):
                continue
            files2return.append([os.path.join(root,bestand),os.path.join(rootinplugin,bestand)])
    return files2return

