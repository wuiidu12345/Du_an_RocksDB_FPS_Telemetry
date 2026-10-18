@echo off
chcp 65001 >nul
title Khoi chay Ung dung Demo - Du an RocksDB FPS Telemetry
cls
@echo off

echo ==================================================================================================================
echo TIEN ICH KHOI CHAY DEMO DASHBOARD QUAN TRI VA KHAI THAC ROCKSDB
echo ==================================================================================================================
echo.
echo.

:: --------------------------------------------------------------------------------------------------------------------
:: KIEM TRA TRANG THAI DOCKER DESKTOP VA CONTAINER
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

docker ps -q --filter "name=nosql-rocksdb-engine" --filter "status=running" | findstr /r "." >nul 2>&1
if errorlevel 1 (
    echo [INFO] Container chua bat, dang tu dong khoi dong container...
    docker compose up -d
    echo.
)

echo [OK] Container 'nosql-rocksdb-engine' dang hoat dong on dinh.
echo.
echo.

:: --------------------------------------------------------------------------------------------------------------------
:: KHOI DONG SERVER STREAMLIT BEN TRONG CONTAINER
:: --------------------------------------------------------------------------------------------------------------------
echo ------------------------------------------------------------------------------------------------------------------
echo [-] Dang khoi chay ung dung Dashboard bang Streamlit tai cong 8505...
echo [+] Cua so Web se tu dong mo tai dia chi: http://localhost:8505
echo.

:: Tu dong don dep tien trinh Streamlit cu tranh chiem cong 8505
docker exec nosql-rocksdb-engine pkill -9 -f streamlit >nul 2>&1
timeout /t 1 /nobreak >nul

:: Mo trinh duyet sau 2 giay de cho server khoi dong
start "" http://localhost:8505

echo [OK] Da kich hoat tien trinh Web Dashboard.
echo.
echo ------------------------------------------------------------------------------------------------------------------
echo THONG TIN TRUY CAP VA QUAN TRI HE THONG:
echo  - Giao dien Web Demo RocksDB: http://localhost:8505
echo  - Cong dich vu Docker da anh xa: 8505:8505 (Khong trung lap voi cac du an khac)
echo ------------------------------------------------------------------------------------------------------------------
echo.
echo (Nhan to hop phim Ctrl + C trong cua so nay neu muon dung chuong trinh)
echo.

docker exec -it nosql-rocksdb-engine streamlit run src/app.py --server.port 8505 --server.address 0.0.0.0

pause
