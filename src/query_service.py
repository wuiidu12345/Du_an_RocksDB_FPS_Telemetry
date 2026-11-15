import os
import json
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")


def scan_events_by_time_range(
    db,
    start_time_sec,
    end_time_sec,
    weapon_filter=None,
    map_filter=None,
    max_limit=20000,
):
    start_key_prefix = f"{int(start_time_sec):08d}|"

    it = db.iter()
    it.seek(start_key_prefix)

    matched_events = []
    scanned_count = 0
    is_truncated = False

    while it.valid():
        if max_limit is not None and len(matched_events) >= max_limit:
            is_truncated = True
            break

        k = it.key()
        parts = k.split("|")
        current_time = int(parts[0])

        if current_time > end_time_sec:
            break

        scanned_count += 1
        raw_val = it.value()
        try:
            event_data = json.loads(raw_val) if isinstance(raw_val, str) else raw_val
        except Exception:
            it.next()
            continue

        if weapon_filter and weapon_filter != "Tất cả":
            if event_data.get("killed_by") != weapon_filter:
                it.next()
                continue

        if map_filter and map_filter != "Tất cả":
            if event_data.get("map") != map_filter:
                it.next()
                continue

        k_x = float(event_data.get("killer_pos_x", 0) or 0)
        v_x = float(event_data.get("victim_pos_x", 0) or 0)
        k_y = float(event_data.get("killer_pos_y", 0) or 0)
        v_y = float(event_data.get("victim_pos_y", 0) or 0)
        dx = k_x - v_x
        dy = k_y - v_y
        event_data["combat_distance"] = round(np.sqrt(dx**2 + dy**2) / 100.0, 2)

        matched_events.append(event_data)
        it.next()

    df_result = pd.DataFrame(matched_events)
    return df_result, scanned_count, is_truncated


def compute_weapon_statistics_from_db(db, max_scan=50000):
    """Quét dữ liệu trong RocksDB để tổng hợp chỉ số hiệu suất vũ khí phục vụ Dashboard"""
    it = db.iter()
    it.seek_to_first()

    records = []
    count = 0
    excluded = ["Down and Out", "Bluezone", "Redzone", "Drown", "Falling", "Punch"]

    while it.valid() and count < max_scan:
        try:
            raw_v = it.value()
            val = json.loads(raw_v) if isinstance(raw_v, str) else raw_v
            wp = val.get("killed_by", "Unknown")
            if wp not in excluded:
                k_x = float(val.get("killer_pos_x", 0) or 0)
                v_x = float(val.get("victim_pos_x", 0) or 0)
                k_y = float(val.get("killer_pos_y", 0) or 0)
                v_y = float(val.get("victim_pos_y", 0) or 0)
                dx = k_x - v_x
                dy = k_y - v_y
                dist = round(np.sqrt(dx**2 + dy**2) / 100.0, 2)
                records.append(
                    {
                        "killed_by": wp,
                        "combat_distance": dist,
                        "map": val.get("map", "ERANGEL"),
                    }
                )
        except Exception:
            pass
        count += 1
        it.next()

    if not records:
        return pd.DataFrame(
            columns=["killed_by", "kill_count", "avg_distance_m", "kill_share_pct"]
        )

    df = pd.DataFrame(records)
    stats = (
        df.groupby("killed_by")
        .agg(
            kill_count=("killed_by", "count"),
            avg_distance_m=("combat_distance", "mean"),
        )
        .reset_index()
    )

    stats["kill_share_pct"] = (stats["kill_count"] / stats["kill_count"].sum()) * 100
    stats["avg_distance_m"] = stats["avg_distance_m"].round(2)
    stats["kill_share_pct"] = stats["kill_share_pct"].round(2)

    return stats.sort_values(by="kill_count", ascending=False)


def analyze_player_playstyles(is_sample=False):
    """
    Phân tích dữ liệu tổng hợp người chơi và lượng hóa 4 trường phái chiến thuật
    Dựa trên các chỉ số: Sát thương (player_dmg), Quãng đường đi bộ (player_dist_walk),
    Số mạng hạ gục (player_kills) và Thời gian sinh tồn (player_survive_time).
    """
    filename = "agg_match_stats_50k.csv" if is_sample else "agg_match_stats_300k.csv"
    csv_path = os.path.join(DATASET_DIR, filename)
    if not os.path.exists(csv_path):
        return pd.DataFrame(), pd.DataFrame()

    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()

    features = ["player_kills", "player_dmg", "player_dist_walk", "player_survive_time"]
    for col in features:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df = df[
        (df["player_dist_walk"] >= 0)
        & (df["player_dist_walk"] <= 8000)
        & (df["player_survive_time"] >= 0)
        & (df["player_survive_time"] <= 3600)
        & (df["player_dmg"] >= 0)
        & (df["player_dmg"] <= 3500)
    ].copy()

    conditions = [
        (df["player_survive_time"] < 400) & (df["player_kills"] == 0),
        (df["player_dmg"] >= 450) | (df["player_kills"] >= 4),
        (df["player_dist_walk"] >= 2200) & (df["player_dmg"] < 120),
    ]
    choices = ["Tân thủ hoặc bị hạ sớm", "Tấn công chủ động", "Sinh tồn du kích"]
    df["playstyle"] = np.select(conditions, choices, default="Chiến thuật cân bằng")

    summary = (
        df.groupby("playstyle")
        .agg(
            avg_kills=("player_kills", "mean"),
            avg_dmg=("player_dmg", "mean"),
            avg_walk=("player_dist_walk", "mean"),
            avg_survive=("player_survive_time", "mean"),
            player_count=("player_name", "count"),
        )
        .reset_index()
    )

    summary["avg_kills"] = summary["avg_kills"].round(2)
    summary["avg_dmg"] = summary["avg_dmg"].round(1)
    summary["avg_walk"] = summary["avg_walk"].round(1)
    summary["avg_survive"] = summary["avg_survive"].round(1)

    return df, summary
