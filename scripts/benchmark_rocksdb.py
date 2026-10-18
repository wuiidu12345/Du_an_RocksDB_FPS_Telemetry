import os
import time
import json
import pandas as pd
from rocksdict import Rdict, Options, WriteBatch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
BENCH_DB = os.path.join(BASE_DIR, "benchmark_db")

print("==================================================================================================================")
print("[-] KHỞI ĐỘNG CHƯƠNG TRÌNH ĐO ĐẠC HIỆU NĂNG ROCKSDB STORAGE ENGINE")
print("==================================================================================================================")

# Chuẩn bị dữ liệu mẫu 10.000 dòng
csv_path = os.path.join(DATASET_DIR, "kill_match_stats_50k.csv")
df = pd.read_csv(csv_path, nrows=10000)
df.columns = df.columns.str.strip()

opt = Options()
opt.create_if_missing(True)
db = Rdict(BENCH_DB, options=opt)

# 1. Đo kiểm tốc độ ghi đơn Put()
print("[-] 1. Đang đo tốc độ ghi từng bản ghi đơn lẻ (Put)...")
t0 = time.time()
for idx, row in df.iterrows():
    key = f"{int(row['time']):08d}|{idx:06d}"
    val = {"time": int(row['time']), "wp": str(row['killed_by'])}
    db[key] = json.dumps(val)
time_put = time.time() - t0
ops_put = len(df) / time_put

print(f" -> Hoàn tất ghi 10.000 bản ghi bằng Put(): {time_put:.4f} giây ({ops_put:.2f} ops/giây)")

# 2. Đo kiểm tốc độ ghi gom lô WriteBatch()
print("\n[-] 2. Đang đo tốc độ ghi theo lô (WriteBatch, batch_size=1000)...")
wb = WriteBatch()
t0 = time.time()
for idx, row in df.iterrows():
    key = f"{int(row['time']):08d}|batch_{idx:06d}"
    val = {"time": int(row['time']), "wp": str(row['killed_by'])}
    wb.put(key, json.dumps(val))
    if idx % 1000 == 0:
        db.write(wb)
        wb = WriteBatch()
db.write(wb)
time_batch = time.time() - t0
ops_batch = len(df) / time_batch

print(f" -> Hoàn tất ghi 10.000 bản ghi bằng WriteBatch(): {time_batch:.4f} giây ({ops_batch:.2f} ops/giây)")
speedup = ops_batch / ops_put if ops_put > 0 else 0
print(f" -> Hiệu năng WriteBatch nhanh gấp: {speedup:.2f} lần so với ghi đơn lẻ!")

# 3. Đo kiểm tốc độ quét dải Iterator.seek()
print("\n[-] 3. Đang đo tốc độ quét dải thời gian (Range Scan with Iterator)...")
t0 = time.time()
it = db.iter()
it.seek("00000200|")
scanned = 0
while it.valid() and scanned < 2000:
    _ = it.key()
    _ = it.value()
    scanned += 1
    it.next()
time_scan = time.time() - t0
print(f" -> Đã quét tuần tự {scanned} bản ghi trong {time_scan * 1000:.2f} mili-giây!")

db.close()
Rdict.destroy(BENCH_DB, opt)

print("\n==================================================================================================================")
print("[OK] TOÀN BỘ BÀI KIỂM THỬ ĐÃ HOÀN TẤT THÀNH CÔNG VÀ CHUẨN XÁC!")
print("==================================================================================================================")
