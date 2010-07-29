import sys
import os
import tarfile
import glob
import shutil
import subprocess
import traceback
import bots.botsglobal as botsglobal


def join(path,*paths):
    return os.path.normpath(os.path.join(path,*paths))



#******************************************************************************
#***    start                     *********************************************
#******************************************************************************
def start():
    print 'Installation of Bots open source EDI translator.'
    #python version dependencies
    version = str(sys.version_info[0]) + str(sys.version_info[1])
    if version == '25':
        pass
    elif version == '26':
        pass
    elif version == '27':
        pass
    else:
        raise Exception('Wrong python version, use python 2.5.*, 2.6.* or 2.7.*')
        
    botsdir = os.path.dirname(botsglobal.__file__)
    print '    Installed Bots in "%s".'%(botsdir)

#******************************************************************************
#***    shortcuts       *******************************************************
#******************************************************************************
    scriptpath = join(sys.prefix,'Scripts')
    shortcutdir = join(get_special_folder_path('CSIDL_COMMON_PROGRAMS'),'Bots2.0')
    try:
        os.mkdir(shortcutdir)
    except: 
        pass
    else:
        directory_created(shortcutdir)
        
    try:
        #~ create_shortcut(join(scriptpath,'botswebserver'),'Bots open source EDI translator',join(shortcutdir,'Bots-webserver.lnk'))
        create_shortcut(join(sys.prefix,'python'),'Bots open source EDI translator',join(shortcutdir,'Bots-webserver.lnk'),join(scriptpath,'bots-webserver.py'))
        file_created(join(shortcutdir,'Bots-webserver.lnk'))
    except: 
        print '    Failed to install shortcut/link for Bots in your menu.'
    else:
        print '    Installed shortcut in "Program Files".'
    
#******************************************************************************
#***    install libraries, dependencies  ***************************************
#******************************************************************************
    for library in glob.glob(join(botsdir,'installwin','*.gz')):
        tar = tarfile.open(library)
        tar.extractall(path=os.path.dirname(library))
        tar.close()
        untar_dir = library[:-len('.tar.gz')]
        subprocess.call([join(sys.prefix,'pythonw'), 'setup.py','install'],cwd=untar_dir,stdin=open(os.devnull,'r'),stdout=open(os.devnull,'w'),stderr=open(os.devnull,'w'))
        shutil.rmtree(untar_dir, ignore_errors=True)
    print '    Installed needed libraries.'

#******************************************************************************
#***    install configuration files      **************************************
#******************************************************************************
    if os.path.exists(join(botsdir,'config','settings.py')):    #use this to see if this is an existing installation
        print '    Found existing configuration files'
        print '        Configuration files bots.ini and settings.py not overwritten.'
        print '        Manual action is needed.'
        print '        See bots web site-documentation-migrate for more info.'
    else:
        shutil.copy(join(botsdir,'install','bots.ini'),join(botsdir,'config','bots.ini'))
        shutil.copy(join(botsdir,'install','settings.py'),join(botsdir,'config','settings.py'))
        print '    Installed configuration files'
        
#******************************************************************************
#***    install database; upgrade existing db *********************************
#******************************************************************************
    sqlitedir = join(botsdir,'botssys','sqlitedb')
    if os.path.exists(join(sqlitedir,'botsdb')):    #use this to see if this is an existing installation
        print '    Found existing database file botssys/sqlitedb/botsdb'
        print '        Manual action is needed - there is a tool/program to update the database.'
        print '        See bots web site-documentation-migrate for more info.'
    else:
        if not os.path.exists(sqlitedir):    #use this to see if this is an existing installation
            os.makedirs(sqlitedir)
        shutil.copy(join(botsdir,'install','botsdb'),join(sqlitedir,'botsdb'))
        print '    Installed SQLite database'


#******************************************************************************
#******************************************************************************

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='-install':
        try:
            start()
        except:
            print traceback.format_exc(0)
            print
            print 'Bots installation failed.'
        else:
            print
            print 'Bots installation succeeded.'
