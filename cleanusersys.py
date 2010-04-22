#!/usr/bin/env python
import sys
import zipfile
import os

def start(dirname):
    print ' yes'
    for root, dirs, files in os.walk(dirname):
        head, tail = os.path.split(root)
        if tail in ['.svn','charsets']:
            del dirs[:]
            continue
        print root, dirs, files
        #~ #check if symbolic link
        for bestand in files:
            print '    ', os.path.join(root,bestand)
            if bestand in ['__init__.py','fake' ]:
                continue
            print '    delete', os.path.join(root,bestand)
            os.remove(os.path.join(root,bestand))


if __name__ == '__main__':
    for arg in sys.argv[1:]:
        if os.path.isdir(arg):
            start(arg)
    
