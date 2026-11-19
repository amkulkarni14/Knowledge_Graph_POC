@echo off
setlocal
if not defined NVM_HOME (
    echo NVM_HOME is not set. This launcher requires NVM for Windows. 1>&2
    exit /b 1
)
set NODE_DIR=%NVM_HOME%\v22.23.5
if not exist %NODE_DIR%\node.exe goto missing
if not exist %NODE_DIR%\npm.cmd goto missing
set PATH=%NODE_DIR%;%PATH%
pushd %~dp0 || exit /b 1
call %NODE_DIR%\npm.cmd %*
set NPM_EXIT=%ERRORLEVEL%
popd
exit /b %NPM_EXIT%

:missing
echo Node 22.23.5 or npm is missing. Run: nvm install 22.23.5 1>&2
exit /b 1
