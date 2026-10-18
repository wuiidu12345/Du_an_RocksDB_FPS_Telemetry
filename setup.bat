@echo off
chcp 65001 >nul
title Khoi tao va Cai dat - Du an RocksDB FPS Telemetry
cls
@echo off

echo ==================================================================================================================
echo KHOI TAO VA CAI DAT MOI TRUONG DOCKER CHO DU AN ROCKSDB FPS TELEMETRY
echo ==================================================================================================================
echo.
echo.

:: --------------------------------------------------------------------------------------------------------------------
:: KIEM TRA DOCKER DESKTOP VA DOCKER ENGINE
:: --------------------------------------------------------------------------------------------------------------------
echo ------------------------------------------------------------------------------------------------------------------
echo [-] Dang kiem tra trang thai Docker Desktop...
echo.

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Desktop chua duoc bat hoac Docker Engine chua khoi dong xong!
    echo [+] Vui long bat phan mem Docker Desktop len va chay lai file setup.bat.
    echo.
    pause
    exit /b
)
echo [OK] Docker Desktop dang hoat dong on dinh va san sang xu ly.
echo.
echo.

:: --------------------------------------------------------------------------------------------------------------------
:: KIEM TRA CAC TEP CAU HINH CO BAN
:: --------------------------------------------------------------------------------------------------------------------
echo ------------------------------------------------------------------------------------------------------------------
echo [-] Dang kiem tra cac tep cau hinh he thong...
echo.

if not exist "requirements.txt" (
    echo [ERROR] Khong tim thay tep 'requirements.txt'!
    echo [+] Vui long kiem tra lai thu muc du an truoc khi tiep tuc.
    echo.
    pause
    exit /b
)

if not exist "Dockerfile" (
    echo [ERROR] Khong tim thay tep 'Dockerfile'!
    echo [+] Vui long kiem tra lai thu muc du an truoc khi tiep tuc.
    echo.
    pause
    exit /b
)

if not exist "docker-compose.yml" (
    echo [ERROR] Khong tim thay tep 'docker-compose.yml'!
    echo [+] Vui long kiem tra lai thu muc du an truoc khi tiep tuc.
    echo.
    pause
    exit /b
)

echo [OK] Cac tep cau hinh 'requirements.txt', 'Dockerfile', 'docker-compose.yml' da hop le.
echo.
echo.

:: --------------------------------------------------------------------------------------------------------------------
:: XAY DUNG VA KHOI DONG CONTAINER NOSQL ROCKSDB ENGINE
:: --------------------------------------------------------------------------------------------------------------------
echo ------------------------------------------------------------------------------------------------------------------
echo [-] Dang tien hanh dong goi va build Image Docker cho du an NoSQL RocksDB...
echo [+] Qua trinh nay se cai dat Python 3.10 va cac thu vien: rocksdict, pandas, streamlit.
echo.

docker compose down >nul 2>&1
docker compose up -d --build

if errorlevel 1 (
    echo.
    echo [ERROR] Build Container that bai! Vui long kiem tra lai ket noi mang hoac Docker Desktop.
    echo.
    pause
    exit /b
)

echo.
echo [OK] Container 'nosql-rocksdb-engine' da duoc tao moi va khoi chay thanh cong.
echo.
echo.

:: --------------------------------------------------------------------------------------------------------------------
:: HOAN TAT
:: --------------------------------------------------------------------------------------------------------------------
echo ==================================================================================================================
echo [OK] CAI DAT HOAN TAT! Moi truong Docker da san sang hoat dong.
echo  - Container: nosql-rocksdb-engine (Python 3.10 ^& RocksDB Engine)
echo  - San sang thuc thi: RocksDB Storage, Ingestion Pipeline, Streamlit Dashboard
echo  - Buoc tiep theo: Chay file 'run_demo.bat' de mo giao dien quan tri CSDL RocksDB.
echo ==================================================================================================================
echo.
pause
