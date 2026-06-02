@echo off
REM StockOracle 一键启动脚本（Windows）
REM 用法：双击运行 start.bat

cd /d "%~dp0"

echo ========================================
echo   StockOracle 启动中...
echo ========================================
echo.

where python >nul 2>&1
if %errorlevel%==0 (
    set PYTHON=python
) else (
    where python3 >nul 2>&1
    if %errorlevel%==0 (
        set PYTHON=python3
    ) else (
        echo [ERROR] 未找到 Python，请先安装 Python 3.8 或更高版本
        pause
        exit /b 1
    )
)

echo 使用: %PYTHON%
for /f %%v in ('%PYTHON% --version 2^>^&1') do echo %%v
echo.

REM 检查依赖
set REQUIRED=PySide6 pandas numpy akshare pyqtgraph plyer requests
set NEED_INSTALL=0

for %%P in (%REQUIRED%) do (
    %PYTHON% -c "import %%P" >nul 2>&1
    if errorlevel 1 (
        echo [缺失] %%P
        set NEED_INSTALL=1
    )
)

if %NEED_INSTALL%==1 (
    echo.
    echo [信息] 正在安装依赖（首次运行可能需要 5-10 分钟，请耐心等待...
    %PYTHON% -m pip install --user %REQUIRED%
    echo [完成] 依赖安装完成
) else (
    echo [完成] 所有依赖已就绪
)

echo.
echo [启动] StockOracle...
set PYTHONPATH=src
%PYTHON% run.py
pause
