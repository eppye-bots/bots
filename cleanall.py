#!/usr/bin/env python
import sys
import zipfile
import os
import shutil

def start(dirname):
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
    start('bots/usersys')
    shutil.rmtree('bots/botssys/infile',ignore_errors=True)
    shutil.rmtree('bots/botssys/outfile',ignore_errors=True)
    
