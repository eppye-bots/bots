import subprocess
import os
import sys
import shutil
import traceback
import bots.botsconfig as botsconfig

def join(path,*paths):
    return os.path.normpath(os.path.join(path,*paths))

def txtexc():
    ''' Get text from last exception    '''
    return traceback.format_exc(0)

#******************************************************************************
#***    install shortcuts/links in menu ***************************************
#******************************************************************************
def installshortcuts(scriptpath):
    shortcutdir = join(get_special_folder_path('CSIDL_COMMON_PROGRAMS'),'Bots16')
    try:
        os.mkdir(shortcutdir)
    except: 
        pass
    else:
        directory_created(shortcutdir)
        
    try:
        create_shortcut(join(scriptpath,'bots-engine'),'Bots open source EDI translator',join(shortcutdir,'Bots-engine.lnk'))
        file_created(join(shortcutdir,'Bots-engine.lnk'))
        create_shortcut(join(scriptpath,'bots-webserver'),'Bots open source EDI translator',join(shortcutdir,'Bots-webserver.lnk'))
        file_created(join(shortcutdir,'Bots-webserver.lnk'))
    except: 
        print '    Failed to install shortcuts/links for Bots in your menu.'
    else:
        print '    Installed shortcuts/links for Bots in your menu.'


def start():
    botsdir = os.path.dirname(botsconfig.__file__)
    scriptpath = join(sys.prefix,'Scripts')
    installfromdir = 'installwin'
    optioninstallfrom = '-f' + join(botsdir,installfromdir)
    
    lijst =['SymbolType',
            'tgMochiKit',
            'Extremes' ,
            'Paste',
            'PasteDeploy',
            'CherryPy',
            'configobj',
            'decoratortools',
            'AddOns',
            'BytecodeAssembler',
            'PEAK-Rules',
            'prioritized_methods',
            'FormEncode',
            'PasteScript',
            'TurboJson',
            'kid',
            'TurboKid',
            'SQLAlchemy',
            'Genshi',
            'TurboGears']
    lijst24 =['elementtree','celementtree']
    lijst25 =['simplejson']
    
    #python version dependencies
    version = str(sys.version_info[0]) + str(sys.version_info[1])
    if version == '24':
        modulesetuptool = 'setuptools-0.6c11.win32-py2.4.exe'
        lijst = lijst24 + lijst25 + lijst
    elif version == '25':
        lijst = lijst25 + lijst
        modulesetuptool = 'setuptools-0.6c11.win32-py2.5.exe'
    elif version == '26':
        modulesetuptool = 'setuptools-0.6c11.win32-py2.6.exe'
    else:
        raise Exception('Wrong python version, use python 2.4.*, 2.5.* or 2.6.*')

#******************************************************************************
#***    start install             *********************************************
#******************************************************************************
    print 'Start bots postinstallation.'
    print '    Bots is installed in: "%s".'%(botsdir)
    installshortcuts(scriptpath)
    
#******************************************************************************
#***    install setuptools        *********************************************
#******************************************************************************
    try:
        import setuptools   #test if setuptools is already installed
    except:
        if subprocess.call(join(botsdir,installfromdir,modulesetuptool),cwd=join(botsdir,installfromdir),bufsize=-1):
            raise Exception('failed to install "setuptools".')
    
    try:
        import setuptools   #test if setuptools is installed
    except:
        raise Exception('failed to install "setuptools".')
    
#******************************************************************************
#***    install libraries, dependencies  ***************************************
#******************************************************************************
    for item in lijst:
        #~ f = open(join(botsdir,'install%s.txt'%item),'w')
        #~ print join(botsdir,installfromdir),item
        #~ if subprocess.call([join(scriptpath,'easy_install'), '-q','-Z','--allow-hosts=None',optioninstallfrom,item],stdout=f,stderr=subprocess.STDOUT):
        if subprocess.call([join(scriptpath,'easy_install'), '-q','-Z','--allow-hosts=None',optioninstallfrom,item]):
            #~ f.close()
            raise Exception('failed to install "%s".'%item)
        #~ f.close()

#******************************************************************************
#***    install configuration files, database; upgrade existing db ************
#******************************************************************************
    if os.path.exists(join(botsdir,'config','bots.ini')):    #use this to see if this is an existing installation
        print '    Found existing configuration files'
        print '        Configuration files bots.ini and botstg.cfg not overwritten.'
        print '        Manual action is needed.'
        print '        See bots web site-documentation-migrate for more info.'
    else:
        shutil.copy(join(botsdir,'install','bots.ini'),join(botsdir,'config','bots.ini'))
        shutil.copy(join(botsdir,'install','botstg.cfg'),join(botsdir,'config','botstg.cfg'))
        
    sqlitedir = join(botsdir,'botssys','sqlitedb')
    if os.path.exists(join(sqlitedir,'botsdb')):    #use this to see if this is an existing installation
        print '    Found existing database file botssys/sqlitedb/botsdb'
        print '        Manual action is needed - there is a tool/program to update the database.'
        print '        See bots web site-documentation-migrate for more info.'
    else:
        if not os.path.exists(sqlitedir):    #use this to see if this is an existing installation
            os.makedirs(sqlitedir)
        shutil.copy(join(botsdir,'install','botsdb'),join(sqlitedir,'botsdb'))

#******************************************************************************
#***    install pysqlite2; installing this earlier caused problems  ***********
#******************************************************************************
    if version == '24':
        try:
            from pysqlite2 import dbapi2 as sqlite
        except:
            if subprocess.call(join(botsdir,installfromdir,'pysqlite-2.5.5.win32-py2.4.exe'),cwd=join(botsdir,installfromdir),bufsize=-1):
                raise Exception('could not install "pysqlite".')

    print '    Installed required python packages.'

#******************************************************************************
#******************************************************************************

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='-install':
        try:
            start()
        except:
            print txtexc()
            print
            print 'Bots installation failed.'
        else:
            print
            print 'Bots installation succeeded.'
