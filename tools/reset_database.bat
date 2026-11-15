@echo off
chcp 65001 >nul
title Tien ich Reset CSDL va Lam moi Du an - RocksDB FPS Telemetry

cd /d "%~dp0.."

cls
@echo off

echo ==================================================================================================================
echo TIEN ICH LAM MOI CO SO DU LIEU VA DU AN
echo ==================================================================================================================
echo.

:: --------------------------------------------------------------------------------------------------------------------
:: KIEM TRA DOCKER DESKTOP VA CONTAINER HIEN CO
:: --------------------------------------------------------------------------------------------------------------------
echo ------------------------------------------------------------------------------------------------------------------
echo [-] Dang kiem tra trang thai he thong Docker...
echo.

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Desktop chua duoc bat! Vui long bat phan mem Docker Desktop truoc.
    echo.
    pause
    exit /b
)

docker ps -a -q --filter "name=nosql-rocksdb-engine" | findstr /r "." >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Khong tim thay Docker Container 'nosql-rocksdb-engine' cua du an!
    echo.
    echo [+] Nguyen nhan: Ban chua khoi tao moi truong lan nao hoac truoc do da chay 'clean_docker.bat' de xoa sach.
    echo [+] HUONG XU LY: Vui long chay file 'setup.bat' tai thu muc goc de cai dat va khoi tao Docker!
    echo.
    echo [*] Ghi chu: Kich ban nay chi phu trach reset du lieu cho Container da ton tai, khong tu y build lai tu dau.
    echo ==================================================================================================================
    echo.
    pause
    exit /b
)

echo [OK] Docker Desktop va Container 'nosql-rocksdb-engine' da san sang.
echo.
echo.

:: --------------------------------------------------------------------------------------------------------------------
:: XAC NHAN THAO TAC RESET
:: --------------------------------------------------------------------------------------------------------------------
echo ------------------------------------------------------------------------------------------------------------------
echo [+] Chuc nang nay se:
echo     1. Giai phong khoa du lieu (File Lock) va dung Container RocksDB hien tai.
echo     2. Xoa sach toan bo du lieu cu (SSTable, WAL, MANIFEST) trong thu muc 'rocksdb_data/'.
echo     3. Xoa sach thu muc kiem thu tam thoi 'benchmark_db/' (neu co).
echo     4. Don dep toan bo bo nho dem Python (__pycache__, *.pyc).
echo     5. Bat lai Container da co de du an tro ve trang thai "moi tinh" san sang nghiem thu.
echo.
echo [*] LUU Y: Lenh nay KHONG xoa va KHONG build lai Docker Image, chi reset du lieu!
echo ------------------------------------------------------------------------------------------------------------------
set /p CONFIRM="Ban co chac chan muon reset toan bo du lieu ve ban dau? (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo.
    echo [INFO] Da huy thao tac reset.
    echo.
    pause
    exit /b
)

echo.
echo ------------------------------------------------------------------------------------------------------------------
echo [-] Dang giai phong khoa doc quyen va tam dung Container...
echo.

docker stop nosql-rocksdb-engine >nul 2>&1
timeout /t 1 /nobreak >nul

echo [OK] Da giai phong file lock thanh cong.
echo.

echo ------------------------------------------------------------------------------------------------------------------
echo [-] Dang xoa sach du lieu RocksDB va thu muc tam...
echo.

if exist "rocksdb_data" (
    rmdir /s /q "rocksdb_data"
    echo  - Da xoa thu muc du lieu: rocksdb_data/
) else (
    echo  - Thu muc 'rocksdb_data/' hien dang trong.
)

if exist "benchmark_db" (
    rmdir /s /q "benchmark_db"
    echo  - Da xoa thu muc kiem thu: benchmark_db/
)

echo.
echo [-] Dang don dep bo nho dem Python (__pycache__)...
for /d /r . %%d in (__pycache__) do @if exist "%%d" (
    rd /s /q "%%d" >nul 2>&1
)
for /r . %%f in (*.pyc) do @if exist "%%f" (
    del /f /q "%%f" >nul 2>&1
)
echo [OK] Da don sach tat ca tep cache cua du an.
echo.

echo ------------------------------------------------------------------------------------------------------------------
echo [-] Dang bat lai Container da co o trang thai moi tinh...
echo.

docker start nosql-rocksdb-engine >nul 2>&1

echo.
echo ==================================================================================================================
echo [OK] HOAN TAT! TOAN BO CO SO DU LIEU ROCKSDB VA BO NHO DEM DA DUOC RESET NHU MOI!
echo  - Du lieu CSDL: Da ve trang thai rong (0 MB, 0 ban ghi).
echo  - Docker Container: Dang chay san sang o che do nen.
echo  - Buoc tiep theo: Nhap dup 'run_demo.bat' de mo Dashboard va bat dau thuc nghiem moi!
echo ==================================================================================================================
echo.
pause
