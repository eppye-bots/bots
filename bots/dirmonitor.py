import sys
import os
import fnmatch
import threading
import time
#bots imports
import botsinit
import botsglobal
import job2queue


if os.name == 'nt':
    try:
        import win32file, win32con
    except Exception, msg: 
        raise ImportError(u'Dependency failure: bots directory monitoring requires python library "Python Win32 Extensions" on windows. Error:\n%s'%msg)
   
    def windows_event_handler(dir_watch,cond,tasks):
        ACTIONS = { 1 : "Created",      #tekst for printing results
                    2 : "Deleted",
                    3 : "Updated",
                    4 : "Renamed from something",
                    5 : "Renamed to something",
                    }
        FILE_LIST_DIRECTORY = 0x0001
        hDir = win32file.CreateFile(dir_watch['path'],           #path to directory
                                    FILE_LIST_DIRECTORY,          #access (read/write) mode
                                    win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,  #share mode: FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE
                                    None,                         #security descriptor
                                    win32con.OPEN_EXISTING,       #how to create
                                    win32con.FILE_FLAG_BACKUP_SEMANTICS,    # file attributes: FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OVERLAPPED
                                    None,
                                    )
        ''' detecting right events is not easy in windows :-(
            want to detect: new file,  move, drop, rename, write/append to file
            only FILE_NOTIFY_CHANGE_LAST_WRITE: copy yes, no move
            for rec=True: event that subdirectory itself is updated (for file deletes in dir)
        '''
        while True:
            results = win32file.ReadDirectoryChangesW(  hDir,
                                                        8192,                   #buffer size was 1024, do not want to miss anything
                                                        dir_watch['rec'],       #recursive 
                                                        win32con.FILE_NOTIFY_CHANGE_FILE_NAME |         
                                                        #~ win32con.FILE_NOTIFY_CHANGE_DIR_NAME |
                                                        #~ win32con.FILE_NOTIFY_CHANGE_ATTRIBUTES |
                                                        #~ win32con.FILE_NOTIFY_CHANGE_SIZE |
                                                        #~ win32con.FILE_NOTIFY_CHANGE_SECURITY |
                                                        #~ win32con.FILE_NOTIFY_CHANGE_CREATION |       #unknown, does not work!
                                                        #~ win32con.FILE_NOTIFsY_CHANGE_LAST_ACCESS |   #unknown, does not work!
                                                        win32con.FILE_NOTIFY_CHANGE_LAST_WRITE,
                                                        None,
                                                        None
                                                        )
            if results:
                #for each incoming event: place route to run in a set. Main thread takes action.
                for action, filename in results:
                    print filename, ACTIONS.get (action, "Unknown")
                for action, filename in results:
                    if action in [1,3,5] and fnmatch.fnmatch(filename, dir_watch['filemask']):
                        #~ if dir_watch['rec'] and os.sep in filename:
                            #~ continue
                        #~ full_filename = os.path.join (path_to_watch, file)
                        cond.acquire()
                        tasks.add(dir_watch['route'])
                        cond.notify()
                        cond.release()
                        break       #the route is triggered, do not need to trigger more often
    #end of windows-specific functions##################################################################################
else:
    try:
        import pyinotify
    except Exception, msg: 
        raise ImportError(u'Dependency failure: bots directory monitoring requires python library "pyinotify" on linux. Error:\n%s'%msg)
    
    class LinuxEventHandler(pyinotify.ProcessEvent):
        ''' 
        incoming event contains:
            dir=<bool>    check? - looks like the mask does nover contains dirs.
            mask=0x80
            maskname=eg IN_MOVED_TO 
            name=<filename>
            path=<path>
            pathname=<path>/<fielanme> 
            wd=<int>     #the watch
        ''' 
        def my_init(self, watch_data,cond,tasks):
            self.watch_data = watch_data
            self.cond = cond
            self.tasks = tasks
            
        def process_default(self,event):
            ''' for each incoming event: place route to run in a set. Main thread takes action.
            '''
            #~ print 'event detected',event.name,event.maskname, event.wd
            if fnmatch.fnmatch(event.name, self.watch_data[event.wd][0]):
                self.cond.acquire()
                self.tasks.add(self.watch_data[event.wd][1])
                self.cond.notify()
                self.cond.release()

    def linux_event_handler(cond,tasks):
        #initialize linux directory monitor
        watch_manager = pyinotify.WatchManager()
        mask = pyinotify.IN_CLOSE_WRITE | pyinotify.IN_MOVED_TO | pyinotify.IN_MODIFY
        #loop thru sections of bots.ini to get the information about the directories to monitor
        #each dir is a separate watch, so multiple watches can be configured....
        #integrate in bots?? parameters should be in channels....indicate watch or not, have  path, filename. can retrieve route. add: rec
        watch_data = {}
        for section in botsglobal.ini.sections():
            if section.startswith('dirmonitor') and  section[len('dirmonitor'):]:
                wd = watch_manager.add_watch(path=botsglobal.ini.get(section,'path'),mask=mask,rec=botsglobal.ini.getboolean(section,'recursive',False),auto_add=False,do_glob=True)
                #one directory can have multiple watches; need to know what watch is related to what configuration section in order to get eg route to call.
                for watch_id in wd.itervalues():
                    watch_data[watch_id] = (botsglobal.ini.get(section,'filemask','*'),botsglobal.ini.get(section,'route',''))
        if not watch_data:
            print 'nothing to watch!'
            sys.exit(0)
        
        handler = LinuxEventHandler(watch_data=watch_data,cond=cond,tasks=tasks)
        notifier = pyinotify.Notifier(watch_manager, handler)
        notifier.loop()
    #end of linux-specific functions##################################################################################


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
    botsenginepath = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])),'bots-engine.py')        #get path to bots-engine
    
    cond = threading.Condition()
    tasks= set()    

    if os.name == 'nt':
        dir_watch_data = []
        for section in botsglobal.ini.sections():
            if section.startswith('dirmonitor') and section[len('dirmonitor')]:
                dir_watch_data.append({})
                dir_watch_data[-1]['path'] = botsglobal.ini.get(section,'path')
                dir_watch_data[-1]['rec'] = botsglobal.ini.getboolean(section,'recursive',False)
                dir_watch_data[-1]['filemask'] = botsglobal.ini.getboolean(section,'filemask','*')
                dir_watch_data[-1]['route'] = botsglobal.ini.getboolean(section,'route','')
         #start a thread per directory watcher
        for dir_watch in dir_watch_data:
            dir_watch_thread = threading.Thread(target=windows_event_handler, args=(dir_watch,cond,tasks))
            dir_watch_thread.daemon = True  #do not wait for thread when exiting
            dir_watch_thread.start()
    else:
        #one watch-thread, but multiple watches. 
        dir_watch_thread = threading.Thread(target=linux_event_handler, args=(cond,tasks))
        dir_watch_thread.daemon = True  #do not wait for thread when exiting
        dir_watch_thread.start()

    # this main thread get the results from the watch-threads.
    print 'start watching'
    active_receiving = False
    TIMEOUT = 2.0
    cond.acquire()
    while True:
        #this functions as a buffer: all events go into set tasks.
        #the tasks are fired to jobqueue after TIMOUT sec.
        #this is to avoid firing to many tasks to jobqueue; events typically come in bursts.
        #is value of TIMEOUT is larger, reaction times are slower...but less tasks are fired to jobqueue.
        #in itself this is not a problem, as jobqueue will alos discard duplicate jobs.
        #2 sec seems to e a good value: reasonable quick, not to nervous. 
        cond.wait(timeout=TIMEOUT)    #get back when results, or after TIMEOUT sec
        if tasks:
            if not active_receiving:    #first request (after tasks have been  fired, or startup of dirmonitor)
                active_receiving = True
                last_time = time.time()
            else:     #active receiving events
                current_time = time.time()
                if current_time - last_time >= TIMEOUT:  #cond.wait returned probably because of a timeout
                    try:
                        for task in tasks:
                           job2queue.send_job_to_jobqueue([sys.executable,botsenginepath,task])
                        print 'send to queue:',[sys.executable,botsenginepath,task]
                    except Exception, msg:
                        print 'Error in running task: "%s".'%msg
                    tasks.clear()
                    active_receiving = False
                else:                                   #cond.wait returned probably because of a timeout
                    print 'time difference to small.'
                    last_time = current_time
    cond.release()
    sys.exit(0)


if __name__ == '__main__':
    start()
