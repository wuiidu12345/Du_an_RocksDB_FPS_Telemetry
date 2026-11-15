@echo off
chcp 65001 >nul
title Tien ich do kiem hieu nang CSDL - RocksDB Benchmark

cd /d "%~dp0.."

cls
@echo off

echo ==================================================================================================================
echo THUC THI TIEN TRINH DO KIEM HIEU NANG ROCKSDB
echo ==================================================================================================================
echo.
echo.

:: --------------------------------------------------------------------------------------------------------------------
:: KIEM TRA TRANG THAI CONTAINER
:: --------------------------------------------------------------------------------------------------------------------
echo ------------------------------------------------------------------------------------------------------------------
echo [-] Dang kiem tra trang thai Container 'nosql-rocksdb-engine'...
echo.

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Desktop chua duoc bat! Vui long mo Docker Desktop len truoc.
    echo.
    pause
    exit /b
)

docker ps -a -q --filter "name=nosql-rocksdb-engine" | findstr /r "." >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Khong tim thay Docker Container 'nosql-rocksdb-engine' cua du an!
    echo.
    echo [+] Nguyen nhan: Ban chua khoi tao moi truong lan nao hoac truoc do da chay 'clean_docker.bat'.
    echo [+] HUONG XU LY: Vui long chay file 'setup.bat' truoc de cai dat va khoi tao Docker!
    echo ==================================================================================================================
    echo.
    pause
    exit /b
)

docker ps -q --filter "name=nosql-rocksdb-engine" --filter "status=running" | findstr /r "." >nul 2>&1
if errorlevel 1 (
    echo [INFO] Container chua bat, dang khoi dong lai container...
    docker start nosql-rocksdb-engine >nul 2>&1
    echo.
)

echo [OK] Container dang hoat dong.
echo.
echo.

:: --------------------------------------------------------------------------------------------------------------------
:: THUC THI KICH BAN KIEM THU HIEU NANG ROCKSDB
:: --------------------------------------------------------------------------------------------------------------------
echo ------------------------------------------------------------------------------------------------------------------
echo [-] Dang thuc thi kịch ban do dac thong luong ghi va truy van tren CSDL RocksDB...
echo.

docker exec -it nosql-rocksdb-engine python scripts/benchmark_rocksdb.py

echo.
echo ==================================================================================================================
echo [OK] DA HOAN TAT TIEN TRINH DO KIEM HIEU NANG ROCKSDB!
echo Cac so lieu thuc nghiem da san sang de trinh bay trong Bao cao Chuong 4 va Chuong 5.
echo ==================================================================================================================
echo.
pause
