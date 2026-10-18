@echo off
chcp 65001 >nul
title Tien ich don dep Docker - Du an RocksDB FPS Telemetry
cls
@echo off

echo ==================================================================================================================
echo TIEN ICH DON DEP TOAN DIEN DOCKER CHO DU AN NOSQL ROCKSDB
echo ==================================================================================================================
echo.
echo.

:: --------------------------------------------------------------------------------------------------------------------
:: KIEM TRA DOCKER DESKTOP
:: --------------------------------------------------------------------------------------------------------------------
echo ------------------------------------------------------------------------------------------------------------------
echo [-] Dang kiem tra trang thai Docker Desktop...
echo.

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Desktop chua duoc bat! Vui long bat Docker Desktop truoc khi don dep.
    echo.
    pause
    exit /b
)
echo [OK] Docker Desktop dang hoat dong.
echo.
echo.

:: --------------------------------------------------------------------------------------------------------------------
:: DUNG VA GO BO CONTAINER, VOLUME, IMAGE CUA DU AN
:: --------------------------------------------------------------------------------------------------------------------
echo ------------------------------------------------------------------------------------------------------------------
echo [-] Dang dung va go bo Container, Image cua du an NoSQL RocksDB...
echo.

docker compose down --rmi all -v

echo.
echo [OK] Da go bo thanh cong Container va Image cua du an nay.
echo.
echo.

:: --------------------------------------------------------------------------------------------------------------------
:: XOA BO NHO DEM BUILD CACHE CUA DOCKER
:: --------------------------------------------------------------------------------------------------------------------
echo ------------------------------------------------------------------------------------------------------------------
echo [-] Dang xoa sach bo nho dem (Build Cache) cua Docker...
echo.

docker builder prune -a -f

echo.
echo ==================================================================================================================
echo [OK] DA DON DEP SACH SE TOAN BO TAI NGUYEN DOCKER CUA DU AN NOSQL ROCKSDB!
echo He thong da duoc giai phong hoan toan dung luong o dia.
echo ==================================================================================================================
echo.
pause
