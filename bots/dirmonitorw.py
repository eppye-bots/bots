import sys
import os
import fnmatch
import win32file
import win32con
#bots imports
import botsinit
import botsglobal
import job2queue

def windows_event_handler():
    ACTIONS = { 1 : "Created",      #tekst for printing results
                2 : "Deleted",
                3 : "Updated",
                4 : "Renamed from something",
                5 : "Renamed to something",
                }
    FILE_LIST_DIRECTORY = 0x0001

    path_to_watch = "."
    hDir = win32file.CreateFile(path_to_watch,              #path to directory
                                FILE_LIST_DIRECTORY,        #access (read/write) mode
                                win32con.FILE_SHARE_WRITE,  #share mode: FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE
                                None,                       #security descriptor
                                win32con.OPEN_EXISTING,     #how to create
                                win32con.FILE_FLAG_BACKUP_SEMANTICS,    # file attributes: FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OVERLAPPED
                                None,
                                )
    while True:
        results = win32file.ReadDirectoryChangesW(  hDir,
                                                    8192,   #buffer size was 1024, do not want to miss anything
                                                    True,   #recursive 
                                                    win32con.FILE_NOTIFY_CHANGE_FILE_NAME |         
                                                    #~ win32con.FILE_NOTIFY_CHANGE_DIR_NAME |
                                                    #~ win32con.FILE_NOTIFY_CHANGE_ATTRIBUTES |
                                                    #~ win32con.FILE_NOTIFY_CHANGE_SIZE |
                                                    #~ win32con.FILE_NOTIFY_CHANGE_SECURITY |
                                                    win32con.FILE_NOTIFY_CHANGE_LAST_WRITE,
                                                    None,
                                                    None
                                                    )
        for action, file in results:
            full_filename = os.path.join (path_to_watch, file)
            print file, ACTIONS.get (action, "Unknown")



def start():
    #***command line arguments**************************
    configdir = 'config'
    for arg in sys.argv[1:]:
        if arg.startswith('-c'):
            configdir = arg[2:]
            if not configdir:
                print 'Configuration directory indicated, but no directory name.'
                sys.exit(1)
        else:
            showusage()
            sys.exit(0)

    botsinit.generalinit(configdir)         #needed to read config
    botsenginepath = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])),'bots-engine.py')        #find the bots-engine

    #initialize linux directory monitor
    watch_manager = pyinotify.WatchManager()
    mask = pyinotify.IN_CLOSE_WRITE | pyinotify.IN_MOVED_TO | pyinotify.IN_MODIFY
    #loop thru sections of bots.ini to get the information about the directories to monitor
    #each dir is a separate watch, so multiple watches can be configured....
    #should be integrated in bots: get parameters from routes/channels....indicate watch or not
    relation_between_watch_and_config = {}
    for section in botsglobal.ini.sections():
        if section.startswith('dirmonitor'):
            section_extension = section[len('dirmonitor'):]
            wd = watch_manager.add_watch(path=botsglobal.ini.get(section,'path'),mask=mask,rec=botsglobal.ini.getboolean(section,'recursive',False),auto_add=False,do_glob=True)
            #one directory can have multiple watches; need to know what watch is related to what configuration section in order to get eg route to call.
            for key,value in wd.iteritems():
                relation_between_watch_and_config[value] = section_extension
    if not relation_between_watch_and_config:
        print 'nothing to watch!'
        sys.exit(0)
    
    handler = LinuxEventHandler(botsenginepath=botsenginepath,relation_between_watch_and_config=relation_between_watch_and_config)
    notifier = pyinotify.Notifier(watch_manager, handler)
    print 'start watching'
    notifier.loop()
    sys.exit(0)


if __name__ == '__main__':
    start()

