@echo off
chcp 65001
cls
echo ========================================
echo   启动Chrome浏览器调试模式
echo ========================================
echo.
echo 正在启动Chrome调试模式（端口9333）...
echo.

REM 查找Chrome路径
set CHROME_PATH=

REM 尝试常见Chrome路径
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH="C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
) else if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH="%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
)

if "%CHROME_PATH%"=="" (
    echo 未找到Chrome浏览器，请手动指定路径
    pause
    exit /b 1
)

echo Chrome路径: %CHROME_PATH%
echo.

REM 创建用户数据目录
set USER_DATA_DIR=%TEMP%\ChromeDebugProfile
if not exist "%USER_DATA_DIR%" mkdir "%USER_DATA_DIR%"

REM 启动Chrome调试模式
start "" %CHROME_PATH% --remote-debugging-port=9333 --user-data-dir="%USER_DATA_DIR%" "about:blank"

echo Chrome调试模式已启动！
echo 远程调试端口: 9333
echo.
echo 请保持此窗口运行，不要关闭
echo 现在可以启动北大法宝图书馆自动爬虫了
echo.
pause
