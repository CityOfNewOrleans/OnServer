@echo off
::Quit if there's no search parameter for OnServer.
if "%1" == "" goto noquery
if "%2" == "" goto nouserpass
if "%3" == "" goto nouserpass

echo Starting Map Services Using %1
for /f %%a in ('..\onserver.py -qq %1') do (
    "C:\Program Files\ArcGIS\Server\tools\admin\manageservice.py" -u %2 -p %3 -t -s http://127.0.0.1:6080 -n %%a -o start
    echo - %%a Started
)
goto end

:noquery
echo You must specify a query string to use with OnServer.
goto usage

:nouserpass
echo You must specify an ArcGIS Server Account username and password that can start
echo and stop map services.
goto usage

:usage
echo Usage: %0 <query> <username> <password>
echo   query     an OnServer query string 
echo             (most often the name of a file geodatabase).
echo   username  the name of an ArcGIS Server Account that can 
echo             start and stop map services.
echo   password  the password associated with username.
echo All parameters are required.

:end