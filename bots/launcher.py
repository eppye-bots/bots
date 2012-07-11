#!/usr/bin/env python
''' contact jobqserver (via xmlrpc) to see if a job needs to be run.
    if so, launch it; poll to see when launched task is finished.
    launcher is started by jobqueueserver. 
    when jobqueueserver dies launcher will die after all launched jobs are finished.
'''
import os
import xmlrpclib
import time
import subprocess

def launch(task_to_run):
    try:
        return subprocess.call(task_to_run,stdin=open(os.devnull,'r'),stdout=open(os.devnull,'w'),stderr=open(os.devnull,'w'))
    except OSError:
        return 5    #indicate process could not be started

def start():
    xmlrpcclient = xmlrpclib.ServerProxy('http://localhost:6000')
    while True:
        time.sleep(3)
        task_to_run = xmlrpcclient.getjob()
        if task_to_run:       #0 means nothing to launch
            task_result = launch(task_to_run)
            xmlrpcclient.logresult(task_to_run,task_result)


if __name__ == '__main__':
    start()
