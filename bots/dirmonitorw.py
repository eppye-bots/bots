import sys
import os
import fnmatch
import threading
import time
import win32file
import win32con
#bots imports
import botsinit
import botsglobal
import job2queue

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
    '''
    want to detect: new file,  move, drop, rename, write/append to file
    only FILE_NOTIFY_CHANGE_LAST_WRITE: copy yes, no move
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
            for action, filename in results:
                print filename, ACTIONS.get (action, "Unknown")
            for action, filename in results:
                if action in [1,3,5] and fnmatch.fnmatch(filename, dir_watch['filemask']):
                    if dir_watch['rec'] and os.sep in filename:
                        continue
                    #~ full_filename = os.path.join (path_to_watch, file)
                    cond.acquire()
                    tasks.add(dir_watch['route'])
                    cond.notify()
                    cond.release()
                    break       #the route is triggered, do not need to trigger more often


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

    botsinit.generalinit(configdir)         #find bots, read config, set correct file paths
    botsenginepath = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])),'bots-engine.py')        #get path to bots-engine
    
    #get data for watchers
    dir_watch_data = []
    for section in botsglobal.ini.sections():
        if section.startswith('dirmonitor') and section[len('dirmonitor')]:
            dir_watch_data.append({})
            dir_watch_data[-1]['path'] = botsglobal.ini.get(section,'path')
            dir_watch_data[-1]['rec'] = botsglobal.ini.getboolean(section,'recursive',False)
            dir_watch_data[-1]['filemask'] = botsglobal.ini.getboolean(section,'filemask','*')
            dir_watch_data[-1]['route'] = botsglobal.ini.getboolean(section,'route','')
    
    cond = threading.Condition()
    tasks= set()    
    #~ logger.info(u'Jobqueue server started.')
    #start a thread per directory watcher
    for dir_watch in dir_watch_data:
        dir_watch_thread = threading.Thread(target=windows_event_handler, args=(dir_watch,cond,tasks))
        dir_watch_thread.daemon = True  #do not wait for thread when exiting
        dir_watch_thread.start()

    # this main thread get the results from the watch-threads.
    print 'start watching'
    active_receiving = False
    TIMEOUT = 2.0
    cond.acquire()
    while True:
        cond.wait(timeout=TIMEOUT)    #get back when results, or after x sec
        if tasks:
            if not active_receiving:
                active_receiving = True
                last_time = time.time()
                print 'no active receiving.'
            else:     #active receiving events
                current_time = time.time()
                print 'active receiving.'
                if current_time - last_time >= TIMEOUT:  #passed the waiting threshold
                    try:
                        for task in tasks:
                            job2queue.send_job_to_jobqueue([sys.executable,botsenginepath,task])
                        print 'send to queue:',task
                    except Exception, msg:
                        print 'Error in running task: "%s".'%msg
                    tasks.clear()
                    active_receiving = False
                else:
                    print 'time difference to small.'
                last_time = current_time
    cond.release()
    sys.exit(0)


if __name__ == '__main__':
    start()

