@echo off
RMDIR /s /q "C:\Documents and Settings\hje\My Documents\botsup2\build"
RMDIR /s /q "C:\Documents and Settings\hje\My Documents\botsup2\bots.egg-info"
DEL /Q "C:\Documents and Settings\hje\My Documents\botsup2\MANIFEST"


MOVE /Y "C:\Documents and Settings\hje\My Documents\botsup2\bots\config\bots.ini"         "C:\Documents and Settings\hje\My Documents\abots"
MOVE /Y "C:\Documents and Settings\hje\My Documents\botsup2\bots\config\settings.py"       "C:\Documents and Settings\hje\My Documents\abots"
MOVE /Y "C:\Documents and Settings\hje\My Documents\botsup2\bots\botssys\sqlitedb\botsdb" "C:\Documents and Settings\hje\My Documents\abots"
MOVE /Y "C:\Documents and Settings\hje\My Documents\botsup2\bots\test.py"                 "C:\Documents and Settings\hje\My Documents\abots"


ECHO build exe
DEL /Q "C:\Documents and Settings\hje\My Documents\botsup2\setup.py"
COPY /Y "C:\Documents and Settings\hje\My Documents\botsup2\winsetup.py" "C:\Documents and Settings\hje\My Documents\botsup2\setup.py"
REM ~ c:\python25\python setup.py --quiet bdist_wininst  --target-version=2.5 --install-script=postinstallation.py  --no-target-compile  --no-target-optimize
REM ~ c:\python26\python setup.py --quiet bdist_wininst  --target-version=2.6 --install-script=postinstallation.py  --no-target-compile  --no-target-optimize  --user-access-control=auto --bitmap=botslogo.bmp --title="Bots open source edi translator"
c:\python26\python setup.py --quiet bdist_wininst   --install-script=postinstallation.py  --no-target-compile  --no-target-optimize  --user-access-control=auto --bitmap=botslogo.bmp --title="Bots open source edi translator"
REM ~ c:\python26\python setup.py --quiet bdist_wininst  --install-script=postinstallation.py 


RMDIR /s /q "C:\Documents and Settings\hje\My Documents\botsup2\build"
RMDIR /s /q "C:\Documents and Settings\hje\My Documents\botsup2\bots.egg-info"
DEL /Q "C:\Documents and Settings\hje\My Documents\botsup2\MANIFEST"


COPY /Y "C:\Documents and Settings\hje\My Documents\botsup2\bots\install\settings.py"  "C:\Documents and Settings\hje\My Documents\botsup2\bots\config"
COPY /Y "C:\Documents and Settings\hje\My Documents\botsup2\bots\install\bots.ini"     "C:\Documents and Settings\hje\My Documents\botsup2\bots\config"
COPY /Y "C:\Documents and Settings\hje\My Documents\botsup2\bots\install\botsdb"       "C:\Documents and Settings\hje\My Documents\botsup2\bots\botssys\sqlitedb"
MOVE /Y "C:\Documents and Settings\hje\My Documents\botsup2\bots\installwin"           "C:\Documents and Settings\hje\My Documents\abots\installwin"


ECHO build source distr
DEL /Q "C:\Documents and Settings\hje\My Documents\botsup2\setup.py"
COPY /Y "C:\Documents and Settings\hje\My Documents\botsup2\linsetup.py"               "C:\Documents and Settings\hje\My Documents\botsup2\setup.py"
c:\python26\python setup.py --quiet sdist


MOVE /Y "C:\Documents and Settings\hje\My Documents\abots\installwin"   "C:\Documents and Settings\hje\My Documents\botsup2\bots\installwin"
MOVE /Y "C:\Documents and Settings\hje\My Documents\abots\botsdb"       "C:\Documents and Settings\hje\My Documents\botsup2\bots\botssys\sqlitedb" 
MOVE /Y "C:\Documents and Settings\hje\My Documents\abots\bots.ini"     "C:\Documents and Settings\hje\My Documents\botsup2\bots\config" 
MOVE /Y "C:\Documents and Settings\hje\My Documents\abots\settings.py"  "C:\Documents and Settings\hje\My Documents\botsup2\bots\config" 
MOVE /Y "C:\Documents and Settings\hje\My Documents\abots\test.py"      "C:\Documents and Settings\hje\My Documents\botsup2\bots" 


RMDIR /s /q "C:\Documents and Settings\hje\My Documents\botsup2\build"
DEL /Q "C:\Documents and Settings\hje\My Documents\botsup2\MANIFEST"
ECHO BUILD FINISHED