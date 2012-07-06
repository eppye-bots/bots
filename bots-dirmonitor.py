import sys
import os
import subprocess
import fnmatch
import pyinotify
from bots import job2queue
import traceback

#parameters needed:
#each dir is a separate watch. so multiple watches have to be configured....
#should be integrated in bots: get parameters from routees/channels....indicate watch or not
#per watch
PAR_directory = '/home/hje/Bots/botsdev/bots/botssys/infile/stress06/xml'
PAR_recursive = False
PAR_filemask = '*.xml'
PAR_route = ''
PAR_botsengine = '/home/hje/Bots/botsdev/bots-engine.py'    #determine this via .....

class EventHandler(pyinotify.ProcessEvent):
    def process_default(self,event):
        #~ print "Received as watch:", repr(event)
        if fnmatch.fnmatch(event.name, PAR_filemask):
            try:
                job2queue.send_job_to_jobqueue([sys.executable,PAR_botsengine,PAR_route])
                #~ result = subprocess.call([sys.executable,'/home/hje/Bots/botsdev/bots-job2queue.py',sys.executable,'/home/hje/Bots/botsdev/bots-engine.py'],stdin=open(os.devnull,'r'),stdout=open(os.devnull,'w'),stderr=open(os.devnull,'w'))
            except Exception, msg:
                traceback.print_exc()
                print 'Error in running task: "%s".'%msg
    #event contains:
        #~ dir=False    check!
        #~ mask=0x80    
        #~ maskname=IN_MOVED_TO 
        #~ name=desadvfull01.xml275.xml 
        #~ path=/home/hje/Bots/botsdev/bots/botssys/infile/stress06/xml 
        #~ pathname=/home/hje/Bots/botsdev/bots/botssys/infile/stress06/xml/desadvfull01.xml275.xml 
        #~ wd=1     

def start():
    watch_manager = pyinotify.WatchManager()
    handler = EventHandler()
    notifier = pyinotify.Notifier(watch_manager, handler)
    watched_events = pyinotify.IN_CLOSE_WRITE | pyinotify.IN_MOVED_TO
    wdd = watch_manager.add_watch(PAR_directory, watched_events, rec=PAR_recursive)

    notifier.loop()


if __name__ == '__main__':
    start()
