#!/bin/sh
cp setup_rpm.py setup.py
python2.7 setup.py bdist_rpm --quit --source-only --requires="python>=2.5, django>1.2.0, cherrypy>3.1.0" 
rm setup.py


