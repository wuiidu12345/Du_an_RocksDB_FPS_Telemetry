import os
import json
import time
import pandas as pd
from rocksdict import WriteBatch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")

def encode_event_key(timestamp_sec, match_id, event_seq):
    """
    Thiết kế Composite Key đảm bảo thứ tự Lexicographical:
    Format: <timestamp_8_chữ_số>|<match_id_rút_gọn>|<seq_6_chữ_số>
    """
    ts_str = f"{int(timestamp_sec):08d}"
    match_str = str(match_id)[-12:] if len(str(match_id)) > 12 else str(match_id)
    seq_str = f"{int(event_seq):06d}"
    return f"{ts_str}|{match_str}|{seq_str}"

def ingest_events_from_csv(db, sample=True, limit=None, use_batch=True, batch_size=2000):
    """
    Đọc dữ liệu sự kiện từ tệp CSV và nạp vào RocksDB cục bộ.
    Xử lý sạch dữ liệu đầu vào, ép kiểu số học an toàn.
    """
    filename = "kill_match_stats_50k.csv" if sample else "kill_match_stats_300k.csv"
    csv_path = os.path.join(DATASET_DIR, filename)
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Không tìm thấy tệp dữ liệu tại {csv_path}")
        
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()
    
    # Ép kiểu số an toàn cho tọa độ và thời gian
    df['time'] = pd.to_numeric(df['time'], errors='coerce').fillna(0).astype(int)
    coord_cols = ['killer_position_x', 'killer_position_y', 'victim_position_x', 'victim_position_y']
    for c in coord_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
            
    df['killed_by'] = df['killed_by'].astype(str).str.strip()
    df['match_id'] = df['match_id'].astype(str).str.strip()
    df['map'] = df['map'].astype(str).str.strip().str.upper()

    if limit is not None:
        df = df.head(limit)
        
    total_records = len(df)
    start_time = time.time()
    
    if use_batch:
        wb = WriteBatch()
        current_batch_count = 0
        
        for idx, row in df.iterrows():
            key = encode_event_key(row['time'], row['match_id'], idx)
            val = {
                "time": int(row['time']),
                "match_id": row['match_id'],
                "killed_by": row['killed_by'],
                "killer_name": str(row.get('killer_name', 'Unknown')).strip(),
                "victim_name": str(row.get('victim_name', 'Unknown')).strip(),
                "killer_pos_x": float(row['killer_position_x']),
                "killer_pos_y": float(row['killer_position_y']),
                "victim_pos_x": float(row['victim_position_x']),
                "victim_pos_y": float(row['victim_position_y']),
                "map": row['map']
            }
            wb.put(key, json.dumps(val))
            current_batch_count += 1
            
            if current_batch_count >= batch_size:
                db.write(wb)
                wb = WriteBatch()
                current_batch_count = 0
                
        if current_batch_count > 0:
            db.write(wb)
    else:
        for idx, row in df.iterrows():
            key = encode_event_key(row['time'], row['match_id'], idx)
            val = {
                "time": int(row['time']),
                "match_id": row['match_id'],
                "killed_by": row['killed_by'],
                "killer_name": str(row.get('killer_name', 'Unknown')).strip(),
                "victim_name": str(row.get('victim_name', 'Unknown')).strip(),
                "killer_pos_x": float(row['killer_position_x']),
                "killer_pos_y": float(row['killer_position_y']),
                "victim_pos_x": float(row['victim_position_x']),
                "victim_pos_y": float(row['victim_position_y']),
                "map": row['map']
            }
            db[key] = json.dumps(val)
            
    elapsed = time.time() - start_time
    throughput = total_records / elapsed if elapsed > 0 else 0
    
    return {
        "total_records": total_records,
        "elapsed_seconds": round(elapsed, 4),
        "throughput_ops": round(throughput, 2)
    }
