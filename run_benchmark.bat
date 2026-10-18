@echo off
chcp 65001 >nul
title Tien ich do kiem hieu nang CSDL - RocksDB Benchmark
cls
@echo off

echo ==================================================================================================================
echo THUC THI TIEN TRINH DO KIEM HIEU NANG ROCKSDB (PUT VS WRITEBATCH ^& RANGE SCAN)
echo ==================================================================================================================
echo.
echo.

:: --------------------------------------------------------------------------------------------------------------------
:: KIEM TRA TRANG THAI CONTAINER
:: --------------------------------------------------------------------------------------------------------------------
echo ------------------------------------------------------------------------------------------------------------------
echo [-] Dang kiem tra trang thai Container 'nosql-rocksdb-engine'...
echo.

docker ps -q --filter "name=nosql-rocksdb-engine" --filter "status=running" | findstr /r "." >nul 2>&1
if errorlevel 1 (
    echo [INFO] Container chua bat, dang tu dong khoi dong container...
    docker compose up -d
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
