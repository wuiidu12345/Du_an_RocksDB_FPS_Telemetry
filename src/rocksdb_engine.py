import os
import shutil
import json
import time
from rocksdict import Rdict, Options, BlockBasedOptions

# Import Cache nếu phiên bản rocksdict hỗ trợ, dự phòng an toàn
try:
    from rocksdict import Cache
except ImportError:
    Cache = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "rocksdb_data")

def get_rocksdb_options(write_buffer_size_mb=64, max_write_buffer_number=4):
    """
    Thiết lập cấu hình nâng cao cho RocksDB tối ưu hóa ghi tải cao (SSD / NVMe).
    """
    opt = Options()
    opt.create_if_missing(True)
    
    # 1. Tối ưu đa luồng nền cho Flush và Compaction
    opt.set_max_background_jobs(4)
    
    # 2. Cấu hình bộ nhớ đệm ghi MemTable
    opt.set_write_buffer_size(write_buffer_size_mb * 1024 * 1024)
    opt.set_max_write_buffer_number(max_write_buffer_number)
    opt.set_min_write_buffer_number_to_merge(2)
    
    # 3. Cấu hình Leveled Compaction
    opt.set_level_zero_file_num_compaction_trigger(4)
    opt.set_max_bytes_for_level_base(256 * 1024 * 1024)
    opt.set_target_file_size_base(64 * 1024 * 1024)
    
    # 4. Cấu hình Block Based Table với Bloom Filter
    table_opts = BlockBasedOptions()
    table_opts.set_block_size(16 * 1024)
    table_opts.set_bloom_filter(10, False)
    opt.set_block_based_table_factory(table_opts)
    
    return opt

def open_rocksdb(db_path=DB_PATH):
    """Mở kết nối tới RocksDB Storage Engine"""
    os.makedirs(db_path, exist_ok=True)
    opt = get_rocksdb_options()
    try:
        db = Rdict(db_path, options=opt)
        return db
    except Exception as e:
        print(f"[ERROR] Không thể mở RocksDB tại {db_path}: {e}")
        return None

def get_storage_statistics(db_path=DB_PATH):
    """Thống kê chi tiết tài nguyên thư mục lưu trữ cục bộ của RocksDB"""
    if not os.path.exists(db_path):
        return {
            "total_size_mb": 0.0,
            "total_files": 0,
            "sst_files_count": 0,
            "wal_files_count": 0
        }
    
    total_size = 0
    total_files = 0
    sst_count = 0
    wal_count = 0
    
    for root, _, files in os.walk(db_path):
        for f in files:
            fp = os.path.join(root, f)
            total_size += os.path.getsize(fp)
            total_files += 1
            if f.endswith(".sst"):
                sst_count += 1
            elif f.endswith(".log"):
                wal_count += 1
                
    return {
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "total_files": total_files,
        "sst_files_count": sst_count,
        "wal_files_count": wal_count
    }

def clear_rocksdb_keys(db):
  """Xóa toàn bộ các bản ghi trong RocksDB bằng cơ chế Tombstone"""
  if db is not None:
    try:
      for k in list(db.keys()):
        del db[k]
    except Exception as e:
      print(f"[WARN] Lỗi khi xóa keys: {e}")

# Tạo alias dự phòng để không bao giờ bị lỗi import
clear_rocksdb_storage = clear_rocksdb_keys

def list_db_physical_files(db_path=DB_PATH):
  """Liệt kê danh sách chi tiết các tệp vật lý nội tại mà RocksDB tạo ra dưới đĩa"""
  if not os.path.exists(db_path):
    return []

  files_info = []
  for f in sorted(os.listdir(db_path)):
    fp = os.path.join(db_path, f)
    if os.path.isfile(fp):
      size_kb = round(os.path.getsize(fp) / 1024, 2)
      mtime = time.strftime(
          "%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(fp))
      )

      # Phân loại vai trò tệp theo kiến trúc RocksDB
      if f.endswith(".sst"):
        ftype = "Bảng dữ liệu chuỗi sắp xếp (SSTable - Lưu trữ đĩa)"
      elif f.endswith(".log"):
        ftype = "Nhật ký ghi trước (WAL)"
      elif f.startswith("MANIFEST"):
        ftype = "Tệp theo dõi siêu dữ liệu trạng thái (MANIFEST)"
      elif f == "CURRENT":
        ftype = "Con trỏ nhận diện tệp MANIFEST hiện hành"
      elif f.startswith("OPTIONS"):
        ftype = "Tệp cấu hình tham số động cơ RocksDB"
      elif f == "LOCK":
        ftype = "Khóa chống xung đột đa tiến trình"
      else:
        ftype = "Tệp siêu dữ liệu hệ thống"

      files_info.append({
          "Tên tệp vật lý": f,
          "Thành phần kiến trúc": ftype,
          "Kích thước (KB)": size_kb,
          "Thời điểm cập nhật": mtime,
      })
  return files_info

def get_direct_rocksdb_records(db, limit=30):
  """Duyệt trực tiếp các cặp Key-Value thô từ RocksDB thông qua Iterator"""
  if db is None:
    return []

  it = db.iter()
  it.seek_to_first()
  records = []
  count = 0

  while it.valid() and count < limit:
    raw_key = it.key()
    raw_val = it.value()

    # Đo độ dài byte thực tế
    key_bytes = len(raw_key.encode("utf-8"))
    val_bytes = len(raw_val.encode("utf-8"))

    try:
      parsed_val = json.loads(raw_val)
      detail_preview = f"Vũ khí: {parsed_val.get('killed_by')} | Người hạ: {parsed_val.get('killer_name')} | Nạn nhân: {parsed_val.get('victim_name')}"
    except Exception:
      detail_preview = str(raw_val)[:80]

    records.append({
        "Khóa cấu trúc": raw_key,
        "Độ dài Key (bytes)": key_bytes,
        "Độ dài Value (bytes)": val_bytes,
        "Trích xuất dữ liệu giá trị": detail_preview,
    })
    count += 1
    it.next()

  return records
