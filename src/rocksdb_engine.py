import os
import shutil
import json
import time
from rocksdict import Rdict, Options, BlockBasedOptions, WriteBatch

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

    opt.set_max_background_jobs(4)

    opt.set_write_buffer_size(write_buffer_size_mb * 1024 * 1024)
    opt.set_max_write_buffer_number(max_write_buffer_number)
    opt.set_min_write_buffer_number_to_merge(2)

    opt.set_level_zero_file_num_compaction_trigger(4)
    opt.set_max_bytes_for_level_base(256 * 1024 * 1024)
    opt.set_target_file_size_base(64 * 1024 * 1024)

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
            "wal_files_count": 0,
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
        "wal_files_count": wal_count,
    }


def clear_rocksdb_keys(db):
    """Xóa toàn bộ các bản ghi trong RocksDB bằng WriteBatch hiệu năng cao"""
    if db is None:
        return 0
    try:
        all_keys = list(db.keys())
        total_keys = len(all_keys)
        if total_keys == 0:
            return 0

        wb = WriteBatch()
        count = 0
        for k in all_keys:
            wb.delete(k)
            count += 1
            if count >= 2000:
                db.write(wb)
                wb = WriteBatch()
                count = 0
        if count > 0:
            db.write(wb)
        return total_keys
    except Exception as e:
        print(f"[WARN] Lỗi khi xóa keys bằng WriteBatch: {e}")
        try:
            for k in list(db.keys()):
                del db[k]
        except Exception:
            pass
        return 0


def delete_single_key(db, key):
    """Xóa một bản ghi cụ thể theo Khóa chính"""
    if db is None or not key:
        return False
    try:
        if key in db:
            del db[key]
            return True
    except Exception as e:
        print(f"[ERROR] Không thể xóa khóa {key}: {e}")
    return False


def flush_rocksdb_memtable(db):
    """Ép chuyển dữ liệu từ bộ nhớ đệm MemTable (RAM) xuống tệp SSTable (Disk)"""
    if db is None:
        return False
    try:
        if hasattr(db, "flush"):
            db.flush(wait=True)
            return True
        elif hasattr(db, "flush_wal"):
            db.flush_wal(sync=True)
            return True
    except Exception as e:
        print(f"[WARN] Lỗi khi flush MemTable: {e}")
    return False


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

            files_info.append(
                {
                    "Tên tệp vật lý": f,
                    "Thành phần kiến trúc": ftype,
                    "Kích thước (KB)": size_kb,
                    "Thời điểm cập nhật": mtime,
                }
            )
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

        key_bytes = len(raw_key.encode("utf-8"))
        val_bytes = len(raw_val.encode("utf-8"))

        try:
            parsed_val = json.loads(raw_val)
            detail_preview = f"Vũ khí: {parsed_val.get('killed_by')} | Người hạ: {parsed_val.get('killer_name')} | Nạn nhân: {parsed_val.get('victim_name')}"
        except Exception:
            detail_preview = str(raw_val)[:80]

        records.append(
            {
                "Khóa cấu trúc": raw_key,
                "Độ dài Key (bytes)": key_bytes,
                "Độ dài Value (bytes)": val_bytes,
                "Trích xuất dữ liệu giá trị": detail_preview,
            }
        )
        count += 1
        it.next()

    return records


# ======================================================================================================================
# QUẢN LÝ SAO LƯU VÀ PHỤC HỒI CƠ SỞ DỮ LIỆU
# ======================================================================================================================


def get_backup_dir():
    backup_dir = os.path.join(BASE_DIR, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir


def create_database_backup(db, note=""):
    """
    Tạo bản sao lưu snapshot vật lý an toàn cho CSDL RocksDB.
    Đồng bộ dữ liệu MemTable xuống đĩa và sao chép cấu trúc tệp dữ liệu.
    """
    if db is None:
        return False, "CSDL chưa được khởi tạo hoặc chưa kết nối."

    try:
        flush_rocksdb_memtable(db)
        time.sleep(0.3)

        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        backup_id = f"backup_{timestamp_str}"
        backup_folder = os.path.join(get_backup_dir(), backup_id)
        os.makedirs(backup_folder, exist_ok=True)

        copied_files = 0
        total_size = 0

        for f in os.listdir(DB_PATH):
            if f == "LOCK":
                continue
            src_file = os.path.join(DB_PATH, f)
            dst_file = os.path.join(backup_folder, f)
            if os.path.isfile(src_file):
                shutil.copy2(src_file, dst_file)
                copied_files += 1
                total_size += os.path.getsize(src_file)

        size_mb = round(total_size / (1024 * 1024), 2)

        meta = {
            "backup_id": backup_id,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "note": note.strip() or "Bản sao lưu thủ công định kỳ",
            "files_count": copied_files,
            "size_mb": size_mb,
        }
        with open(
            os.path.join(backup_folder, "backup_info.json"), "w", encoding="utf-8"
        ) as f_meta:
            json.dump(meta, f_meta, ensure_ascii=False, indent=2)

        return True, meta
    except Exception as e:
        return False, str(e)


def list_available_backups():
    """Liệt kê danh sách tất cả các bản sao lưu hiện có trong thư mục backups/"""
    backup_dir = get_backup_dir()
    if not os.path.exists(backup_dir):
        return []

    backups = []
    for folder_name in sorted(os.listdir(backup_dir), reverse=True):
        folder_path = os.path.join(backup_dir, folder_name)
        if os.path.isdir(folder_path):
            meta_path = os.path.join(folder_path, "backup_info.json")
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                        backups.append(meta)
                except Exception:
                    pass
            else:
                backups.append(
                    {
                        "backup_id": folder_name,
                        "created_at": "Không xác định",
                        "note": "Bản sao lưu cấu trúc tệp",
                        "files_count": len(os.listdir(folder_path)),
                        "size_mb": 0.0,
                    }
                )
    return backups


def restore_database_from_backup(backup_id, db):
    """
    Phục hồi toàn bộ dữ liệu CSDL RocksDB từ bản sao lưu chỉ định.
    Sử dụng WriteBatch nạp dữ liệu trực tiếp để tránh xung đột file lock của hệ điều hành.
    """
    if db is None or not backup_id:
        return False, "CSDL hoặc mã bản sao lưu không hợp lệ."

    backup_folder = os.path.join(get_backup_dir(), backup_id)
    if not os.path.exists(backup_folder):
        return False, f"Không tìm thấy thư mục bản sao lưu tại {backup_folder}"

    try:
        clear_rocksdb_keys(db)

        opt = Options()
        opt.create_if_missing(False)
        backup_db = Rdict(backup_folder, options=opt)

        it = backup_db.iter()
        it.seek_to_first()
        wb = WriteBatch()
        restored_count = 0

        while it.valid():
            wb.put(it.key(), it.value())
            restored_count += 1
            if restored_count % 2000 == 0:
                db.write(wb)
                wb = WriteBatch()
            it.next()

        try:
            db.write(wb)
        except Exception:
            pass

        del it
        backup_db.close()
        del backup_db

        flush_rocksdb_memtable(db)
        return True, restored_count
    except Exception as e:
        return False, str(e)


def delete_backup(backup_id):
    """Xóa một bản sao lưu cụ thể khỏi hệ thống lưu trữ"""
    backup_folder = os.path.join(get_backup_dir(), backup_id)
    if os.path.exists(backup_folder):
        try:
            shutil.rmtree(backup_folder, ignore_errors=True)
            return True
        except Exception:
            pass
    return False
