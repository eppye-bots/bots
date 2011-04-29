#!/bin/sh
cp rpmsetup.py setup.py
python rpmsetup.py --quiet bdist_rpm --source-only --requires="python>=2.6, django>1.1.0, cherrypy>3.1.0" 
rm setup.py
rm -r build


