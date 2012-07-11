import sys
import os
import fnmatch
try:
    import pyinotify
except Exception, msg: 
    raise ImportError(_(u'Dependency failure: bots directory monitoring requires python library "pyinotify" on linux. Error:\n%s'%msg))
#bots imports
import botsinit
import botsglobal
import job2queue

#about parameters:
PAR_botsengine = '/home/hje/Bots/botsdev/bots-engine.py'    #determine this via .....

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
    def my_init(self, botsenginepath,relation_between_watch_and_config):
        self.botsenginepath = botsenginepath
        self.relation_between_watch_and_config = relation_between_watch_and_config
        
    def process_default(self,event):
        #~ print 'event detected',event.name,event.maskname, event.wd
        inisection = 'dirmonitor'+self.relation_between_watch_and_config[event.wd]
        if fnmatch.fnmatch(event.name, botsglobal.ini.get(inisection,'filemask','*')):
            try:
                job2queue.send_job_to_jobqueue([sys.executable,self.botsenginepath,botsglobal.ini.get(inisection,'route','')])
            except Exception, msg:
                print 'Error in running task: "%s".'%msg


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
