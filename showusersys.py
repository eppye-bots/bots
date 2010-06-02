#!/usr/bin/env python
import sys
import zipfile
import os

def start(dirname):
    print 'Show content of',dirname
    for root, dirs, files in os.walk(dirname):
        head, tail = os.path.split(root)
        if tail in ['.svn','charsets']:
            del dirs[:]
            continue
        #~ print root, dirs, files
        #~ #check if symbolic link
        for bestand in files:
            if bestand in ['__init__.py','fake' ]:
                continue
            if os.path.splitext(bestand)[1] in ['.pyo','.pyc' ]:
                continue
            print '    ', os.path.join(root,bestand)


if __name__ == '__main__':
    for arg in sys.argv[1:]:
        print arg
        if os.path.isdir(arg):
            start(arg)
    
