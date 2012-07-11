@echo off
RMDIR /s /q "C:\Documents and Settings\hje\My Documents\botsup2\build"
DEL /Q "C:\Documents and Settings\hje\My Documents\botsup2\MANIFEST"
RMDIR /s /q "C:\Documents and Settings\hje\My Documents\botsup2\bots.egg-info"


MOVE /Y "C:\Documents and Settings\hje\My Documents\botsup2\bots\config\bots.ini"         "C:\Documents and Settings\hje\My Documents\abots"
MOVE /Y "C:\Documents and Settings\hje\My Documents\botsup2\bots\config\settings.py"       "C:\Documents and Settings\hje\My Documents\abots"
MOVE /Y "C:\Documents and Settings\hje\My Documents\botsup2\bots\botssys\sqlitedb\botsdb" "C:\Documents and Settings\hje\My Documents\abots"


ECHO build exe
DEL /Q "C:\Documents and Settings\hje\My Documents\botsup2\setup.py"
COPY /Y "C:\Documents and Settings\hje\My Documents\botsup2\setup_win.py" "C:\Documents and Settings\hje\My Documents\botsup2\setup.py"
REM ~ c:\python26\python setup.py --quiet bdist_wininst  --target-version=2.6 --install-script=postinstallation.py  --no-target-compile  --no-target-optimize  --user-access-control=auto --bitmap=botslogo.bmp --title="Bots open source edi translator"
c:\python27\python setup.py --quiet bdist_wininst   --install-script=postinstallation.py  --no-target-compile  --no-target-optimize  --user-access-control=force --bitmap=botslogo.bmp --title="Bots open source edi translator"


REM COPY /Y "C:\Documents and Settings\hje\My Documents\botsup2\bots\install\settings.py"  "C:\Documents and Settings\hje\My Documents\botsup2\bots\config"
REM COPY /Y "C:\Documents and Settings\hje\My Documents\botsup2\bots\install\bots.ini"     "C:\Documents and Settings\hje\My Documents\botsup2\bots\config"
REM COPY /Y "C:\Documents and Settings\hje\My Documents\botsup2\bots\install\botsdb"       "C:\Documents and Settings\hje\My Documents\botsup2\bots\botssys\sqlitedb"


MOVE /Y "C:\Documents and Settings\hje\My Documents\abots\botsdb"       "C:\Documents and Settings\hje\My Documents\botsup2\bots\botssys\sqlitedb" 
MOVE /Y "C:\Documents and Settings\hje\My Documents\abots\bots.ini"     "C:\Documents and Settings\hje\My Documents\botsup2\bots\config" 
MOVE /Y "C:\Documents and Settings\hje\My Documents\abots\settings.py"  "C:\Documents and Settings\hje\My Documents\botsup2\bots\config" 


RMDIR /s /q "C:\Documents and Settings\hje\My Documents\botsup2\build"
DEL /Q "C:\Documents and Settings\hje\My Documents\botsup2\MANIFEST"
ECHO BUILD FINISHED
