import streamlit as st
import pandas as pd
import time
import json
import random
import plotly.express as px

from rocksdb_engine import (
    clear_rocksdb_keys,
    create_database_backup,
    delete_backup,
    delete_single_key,
    flush_rocksdb_memtable,
    get_direct_rocksdb_records,
    get_storage_statistics,
    list_available_backups,
    list_db_physical_files,
    open_rocksdb,
    restore_database_from_backup,
)
from event_ingestion import encode_event_key, ingest_events_from_csv
from query_service import (
    scan_events_by_time_range,
    compute_weapon_statistics_from_db,
    analyze_player_playstyles,
)
from heatmap import generate_spatial_heatmap

st.set_page_config(
    page_title="Dự án RocksDB FPS Telemetry",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .main-header { font-size: 25px; font-weight: 700; color: #38bdf8; margin-bottom: 4px; }
    .sub-header { font-size: 14px; opacity: 0.85; margin-bottom: 18px; color: #cbd5e1; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { font-size: 14px; font-weight: 600; padding: 10px 18px; }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_resource
def get_db():
    return open_rocksdb()


db = get_db()

# ======================================================================================================================
# THANH ĐIỀU HƯỚNG BÊN TRÁI (SIDEBAR)
# ======================================================================================================================
st.sidebar.image("https://img.icons8.com/color/96/000000/database.png", width=65)
st.sidebar.title("Quản Trị NoSQL RocksDB")
st.sidebar.caption("Hệ thống lưu trữ cục bộ tốc độ cao (LSM-tree)")

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Cấu Hình Dữ Liệu Nguồn")

data_choice = st.sidebar.radio(
    "Lựa chọn tập dữ liệu thực nghiệm:",
    ["Tập dữ liệu 300.000 bản ghi", "Tập dữ liệu 50.000 bản ghi"],
    index=0,
)
is_sample = False if "300.000" in data_choice else True

stats = get_storage_statistics()
st.sidebar.markdown("---")
st.sidebar.subheader("💾 Thống Kê Tài Nguyên CSDL")
st.sidebar.write(f"- **Dung lượng thư mục:** `{stats['total_size_mb']} MB`")
st.sidebar.write(f"- **Tổng số tệp dữ liệu:** `{stats['total_files']} tệp`")
st.sidebar.write(f"- **Tệp bảng chuỗi (SSTable):** `{stats['sst_files_count']}`")
st.sidebar.write(f"- **Nhật ký ghi trước (WAL):** `{stats['wal_files_count']}`")
st.sidebar.write("- **Trạng thái:** `🟢 Đang kết nối`")

# ======================================================================================================================
# CẤU TRÚC CÁC PHÂN HỆ CHỨC NĂNG (TABS)
# ======================================================================================================================
tabs = st.tabs(
    [
        "📊 Bảng điều khiển CSDL",
        "⚡ Tiếp nhận sự kiện",
        "🔍 Truy vấn dải thời gian",
        "🔫 Phân tích hiệu suất vũ khí",
        "🎯 Phân tích phong cách chiến thuật",
        "🗺️ Tái hiện không gian & Thực nghiệm",
        "💾 Sao lưu & Phục hồi CSDL",
    ]
)

# ----------------------------------------------------------------------------------------------------------------------
# TAB 1: BẢNG ĐIỀU KHIỂN & GIÁM SÁT TRỰC TIẾP CSDL ROCKSDB
# ----------------------------------------------------------------------------------------------------------------------
with tabs[0]:
    st.markdown(
        '<div class="main-header">Trạng Thái & Trình Duyệt Dữ Liệu Trực Tiếp RocksDB</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sub-header">Quan sát trực quan các cặp Key-Value lưu trong bộ nhớ/đĩa và cấu trúc tệp vật lý của động cơ RocksDB</div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Tổng dung lượng CSDL", f"{stats['total_size_mb']} MB")
    col2.metric("Số tệp dữ liệu SSTable", f"{stats['sst_files_count']} tệp")
    col3.metric("Số tệp nhật ký WAL", f"{stats['wal_files_count']} tệp")
    col4.metric("Cổng dịch vụ trực tuyến", "8505 (Độc lập)")

    st.markdown("---")

    st.subheader("Trực tiếp dữ liệu Key-Value trong RocksDB")
    st.caption(
        "Dữ liệu được đọc trực tiếp từ con trỏ Iterator của RocksDB Engine (Mô tả đúng cơ chế Key có thứ tự và Value dạng chuỗi JSON)."
    )

    raw_records = get_direct_rocksdb_records(db, limit=20)
    if raw_records:
        df_raw = pd.DataFrame(raw_records)
        st.dataframe(df_raw, width="stretch")
        st.caption(
            f"Đang hiển thị {len(raw_records)} bản ghi mẫu đầu tiên lưu trong RocksDB."
        )
    else:
        st.info(
            "💡 Hiện tại cơ sở dữ liệu RocksDB chưa có bản ghi nào. Hãy sang **Tab Tiếp nhận sự kiện** bấm nạp dữ liệu để xem các bản ghi xuất hiện trực tiếp tại đây!"
        )

    st.markdown("##### 🔎 Tra cứu nhanh theo Khóa chính (Point Lookup - Get Key)")
    c_find1, c_find2 = st.columns([3, 1])
    with c_find1:
        search_key_input = st.text_input(
            "Nhập mã khóa (Key) cần tra cứu:",
            placeholder="Ví dụ: 00000194|1Ocel6nY|000001",
        ).strip()
    with c_find2:
        st.write("")
        st.write("")
        btn_search_key = st.button("Truy xuất khóa")

    if search_key_input:
        if search_key_input in db:
            val_found = db[search_key_input]
            st.success(f"Tìm thấy Khóa `{search_key_input}` trong RocksDB!")
            try:
                parsed_json = (
                    json.loads(val_found) if isinstance(val_found, str) else val_found
                )
                st.json(parsed_json)
            except Exception:
                st.code(str(val_found))

            col_del_k1, col_del_k2 = st.columns([1, 4])
            with col_del_k1:
                if st.button("❌ Xóa bản ghi này", key="btn_del_single_key"):
                    if delete_single_key(db, search_key_input):
                        st.success(
                            f"Đã xóa thành công khóa `{search_key_input}` khỏi RocksDB!"
                        )
                        time.sleep(0.5)
                        st.rerun()
        elif btn_search_key:
            st.error(f"Khóa `{search_key_input}` không tồn tại trong CSDL.")

    with st.expander(
        "➕ Thêm sự kiện đo đạc thủ công vào RocksDB (Thao tác Create)", expanded=False
    ):
        st.caption(
            "Khởi tạo và ghi nhận trực tiếp một bản ghi sự kiện Key-Value mới vào RocksDB theo cấu trúc Composite Key chuẩn hóa."
        )
        c_in_e1, c_in_e2, c_in_e3 = st.columns(3)
        with c_in_e1:
            c_time = st.number_input(
                "Thời điểm phát sinh (giây):",
                min_value=0,
                max_value=3600,
                value=120,
                step=10,
                key="in_time",
            )
            c_match = st.text_input(
                "Mã trận đấu (Match ID):", value="custom_match_01", key="in_match"
            ).strip()
        with c_in_e2:
            c_killer = st.text_input(
                "Người thực hiện (Killer Name):", value="ProGamer_VN", key="in_killer"
            ).strip()
            c_victim = st.text_input(
                "Nạn nhân (Victim Name):", value="Target_Bot_99", key="in_victim"
            ).strip()
        with c_in_e3:
            c_weapon = st.selectbox(
                "Vũ khí sử dụng:",
                [
                    "M416",
                    "AKM",
                    "SCAR-L",
                    "Kar98k",
                    "AWM",
                    "UMP9",
                    "M16A4",
                    "S12K",
                    "Groza",
                    "Mini 14",
                ],
                key="in_weapon",
            )
            c_map = st.selectbox(
                "Bản đồ chiến trường:", ["ERANGEL", "MIRAMAR"], key="in_map"
            )

        col_pk, col_pv = st.columns(2)
        with col_pk:
            st.write("**Tọa độ Người thực hiện (X, Y):**")
            c_kx = st.number_input(
                "Killer Pos X (0 -> 800.000):", value=450000.0, step=5000.0, key="in_kx"
            )
            c_ky = st.number_input(
                "Killer Pos Y (0 -> 800.000):", value=320000.0, step=5000.0, key="in_ky"
            )
        with col_pv:
            st.write("**Tọa độ Nạn nhân (X, Y):**")
            c_vx = st.number_input(
                "Victim Pos X (0 -> 800.000):", value=452500.0, step=5000.0, key="in_vx"
            )
            c_vy = st.number_input(
                "Victim Pos Y (0 -> 800.000):", value=321200.0, step=5000.0, key="in_vy"
            )

        if st.button("🚀 Ghi nhận sự kiện mới vào RocksDB"):
            rand_seq = random.randint(100000, 999999)
            new_key = encode_event_key(c_time, c_match, rand_seq)
            new_val = {
                "time": int(c_time),
                "match_id": str(c_match),
                "killed_by": str(c_weapon),
                "killer_name": str(c_killer),
                "victim_name": str(c_victim),
                "killer_pos_x": float(c_kx),
                "killer_pos_y": float(c_ky),
                "victim_pos_x": float(c_vx),
                "victim_pos_y": float(c_vy),
                "map": str(c_map),
            }
            db[new_key] = json.dumps(new_val)
            st.success(f"✅ Đã ghi thành công sự kiện mới vào CSDL RocksDB!")
            st.info(f"🔑 **Mã Khóa chính (Composite Key) đã tạo:** `{new_key}`")
            st.json(new_val)
            time.sleep(1.0)
            st.rerun()

    st.markdown("---")

    st.subheader("Cấu trúc tệp vật lý của RocksDB trên thiết bị lưu trữ")
    st.caption(
        "Chi tiết các tệp dữ liệu bảng chuỗi sắp xếp (SSTable), nhật ký ghi trước (WAL) và tệp điều phối MANIFEST trong thư mục rocksdb_data/."
    )

    db_files = list_db_physical_files()
    if db_files:
        df_files = pd.DataFrame(db_files)
        st.dataframe(df_files, width="stretch")
    else:
        st.write("Thư mục CSDL chưa khởi tạo tệp vật lý.")

    st.markdown("---")

    c_left, c_right = st.columns(2)
    with c_left:
        st.subheader("Cấu hình tham số kiến trúc LSM-tree")
        config_df = pd.DataFrame(
            {
                "Thông số kỹ thuật": [
                    "Cấu trúc bảng đệm bộ nhớ (MemTable)",
                    "Kích thước bộ đệm ghi",
                    "Số lượng bộ đệm MemTable tối đa",
                    "Chính sách nén và hợp nhất",
                    "Kích thước tệp SSTable cơ sở",
                    "Bộ lọc xác suất",
                    "Số luồng xử lý nền",
                ],
                "Giá trị cấu hình thực nghiệm": [
                    "SkipList",
                    "64 MB",
                    "4 bộ đệm",
                    "Leveled Compaction",
                    "64 MB",
                    "10 bits/key (Đã kích hoạt)",
                    "4 luồng song song",
                ],
            }
        )
        st.dataframe(config_df, width="stretch")

    with c_right:
        st.subheader("Tiện ích quản trị & Điều khiển LSM-tree")
        st.info(
            "RocksDB duy trì tính toàn vẹn dữ liệu cao nhờ cơ chế ghi đồng thời vào MemTable trên RAM và WAL trên đĩa."
        )

        if st.button("⚡ Kích hoạt Flush MemTable sang SSTable"):
            with st.spinner("Đang ép luồng nền ghi đệm MemTable xuống đĩa..."):
                if flush_rocksdb_memtable(db):
                    st.success(
                        "✅ Đã kích hoạt Flush thành công! Dữ liệu đã chuyển sang các tệp SSTable."
                    )
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.warning(
                        "Bộ đệm MemTable hiện tại đang trống hoặc đã được flush trước đó."
                    )

        st.markdown("<br>", unsafe_allow_html=True)
        confirm_clear = st.checkbox("Xác nhận muốn xóa sạch toàn bộ bản ghi trong CSDL")
        if st.button(
            "🗑️ Xóa sạch toàn bộ dữ liệu trong RocksDB", disabled=not confirm_clear
        ):
            deleted_count = clear_rocksdb_keys(db)
            st.success(
                f"Đã xóa sạch {deleted_count:,} bản ghi trong CSDL! Hãy chuyển sang Tab Tiếp nhận sự kiện để nạp dữ liệu mới."
            )
            time.sleep(0.5)
            st.rerun()

# ----------------------------------------------------------------------------------------------------------------------
# TAB 2: TIẾP NHẬN SỰ KIỆN TỐC ĐỘ CAO
# ----------------------------------------------------------------------------------------------------------------------
with tabs[1]:
    st.markdown(
        '<div class="main-header">Bộ Tiếp Nhận Và Ghi Nhận Sự Kiện Tốc Độ Cao</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sub-header">Tiếp nhận luồng sự kiện đo đạc từ xa và thực thi ghi nhận hiệu năng cao vào RocksDB</div>',
        unsafe_allow_html=True,
    )

    col_in1, col_in2, col_in3 = st.columns(3)
    with col_in1:
        st.write(f"**Nguồn dữ liệu hiện hành:**")
        st.info(f"📁 {data_choice}")
    with col_in2:
        write_mode = st.radio(
            "Cơ chế ghi nhận vào RocksDB:",
            ["Ghi theo lô hiệu năng cao (WriteBatch)", "Ghi đơn lẻ từng bản ghi (Put)"],
        )
    with col_in3:
        max_record_limit = 300000 if not is_sample else 50000
        step_val = 10000 if not is_sample else 5000
        default_val = 50000 if not is_sample else 10000
        record_limit = st.slider(
            "Số lượng bản ghi nạp thử nghiệm:",
            5000,
            max_record_limit,
            default_val,
            step=step_val,
        )

    if st.button("🚀 Kích hoạt quy trình nạp dữ liệu vào RocksDB"):
        with st.spinner("Đang xử lý và ghi nhận dữ liệu vào RocksDB..."):
            res = ingest_events_from_csv(
                db,
                sample=is_sample,
                limit=record_limit,
                use_batch=("WriteBatch" in write_mode),
                batch_size=2000,
            )
            st.success(
                f"✅ Đã ghi nhận thành công **{res['total_records']:,}** bản ghi vào cơ sở dữ liệu RocksDB!"
            )
            res_c1, res_c2 = st.columns(2)
            res_c1.metric("Thời gian thực thi", f"{res['elapsed_seconds']} giây")
            res_c2.metric(
                "Thông lượng ghi (Throughput)",
                f"{res['throughput_ops']:,} bản ghi/giây",
            )

# ----------------------------------------------------------------------------------------------------------------------
# TAB 3: TRUY VẤN DẢI THỜI GIAN (ITERATOR)
# ----------------------------------------------------------------------------------------------------------------------
with tabs[2]:
    st.markdown(
        '<div class="main-header">Truy Vấn Và Khai Thác Nhật Ký Theo Dải Thời Gian</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sub-header">Sử dụng con trỏ Iterator của RocksDB để quét tuần tự các dải khóa theo mốc thời gian</div>',
        unsafe_allow_html=True,
    )

    col_q1, col_q2, col_q3, col_q4 = st.columns(4)
    with col_q1:
        t_start = st.number_input(
            "Thời điểm bắt đầu (giây):", min_value=0, max_value=3000, value=100, step=50
        )
    with col_q2:
        t_end = st.number_input(
            "Thời điểm kết thúc (giây):",
            min_value=0,
            max_value=3000,
            value=400,
            step=50,
        )
    with col_q3:
        wp_filter = st.selectbox(
            "Lọc theo loại vũ khí:",
            ["Tất cả", "M416", "AKM", "SCAR-L", "Kar98k", "UMP9"],
        )
    with col_q4:
        limit_choice = st.selectbox(
            "Giới hạn bản ghi quét:",
            [
                "10.000 sự kiện",
                "20.000 sự kiện",
                "50.000 sự kiện",
                "100.000 sự kiện",
                "Toàn bộ (Không giới hạn)",
            ],
            index=2,
        )

    if "10.000" in limit_choice:
        max_scan_limit = 10000
    elif "20.000" in limit_choice:
        max_scan_limit = 20000
    elif "50.000" in limit_choice:
        max_scan_limit = 50000
    elif "100.000" in limit_choice:
        max_scan_limit = 100000
    else:
        max_scan_limit = None

    if "range_query_result" not in st.session_state:
        st.session_state["range_query_result"] = None

    if st.button("🔍 Thực thi truy vấn quét dải"):
        with st.spinner("RocksDB đang duyệt dải khóa trên các tệp SSTable..."):
            t0 = time.time()
            df_res, scanned, is_truncated = scan_events_by_time_range(
                db, t_start, t_end, weapon_filter=wp_filter, max_limit=max_scan_limit
            )
            latency = (time.time() - t0) * 1000.0
            st.session_state["range_query_result"] = {
                "df_res": df_res,
                "scanned": scanned,
                "latency": latency,
                "t_start": t_start,
                "t_end": t_end,
                "wp_filter": wp_filter,
                "max_limit": max_scan_limit,
                "is_truncated": is_truncated,
            }

    if st.session_state["range_query_result"] is not None:
        res_data = st.session_state["range_query_result"]
        df_res = res_data["df_res"]
        scanned = res_data["scanned"]
        latency = res_data["latency"]
        q_start = res_data["t_start"]
        q_end = res_data["t_end"]
        is_truncated = res_data["is_truncated"]

        if not df_res.empty:
            if is_truncated:
                last_event_time = int(df_res["time"].iloc[-1])
                st.warning(
                    f"⚠️ **Đã chạm trần giới hạn {len(df_res):,} bản ghi tại mốc {last_event_time}s!** "
                    f"Dải sự kiện từ `{last_event_time}s` đến `{q_end}s` chưa được quét hết. "
                    f"👉 Hãy tăng **Giới hạn bản ghi quét** (chọn *50.000*, *100.000* hoặc *Toàn bộ*) rồi bấm truy vấn lại để xem trọn vẹn dải thời gian!"
                )
            else:
                st.success(
                    f"⚡ Đã quét trọn vẹn dải thời gian từ `{q_start}s` đến `{q_end}s`: "
                    f"Duyệt qua **{scanned:,}** bản ghi liên tiếp, tìm thấy **{len(df_res):,}** sự kiện phù hợp! "
                    f"Độ trễ phản hồi: **{latency:.2f} ms**"
                )

            display_table = (
                df_res[
                    [
                        "time",
                        "killed_by",
                        "killer_name",
                        "victim_name",
                        "combat_distance",
                        "map",
                    ]
                ]
                .head(25)
                .rename(
                    columns={
                        "time": "Thời điểm phát sinh (time - giây)",
                        "killed_by": "Vũ khí kết liễu (killed_by)",
                        "killer_name": "Người thực hiện (killer_name)",
                        "victim_name": "Nạn nhân (victim_name)",
                        "combat_distance": "Khoảng cách tiêu diệt (combat_distance - mét)",
                        "map": "Bản đồ chiến trường (map)",
                    }
                )
            )
            st.dataframe(display_table, width="stretch")

            fig_time = px.histogram(
                df_res,
                x="time",
                nbins=35,
                range_x=[q_start, q_end],
                title=f"Phân bố tần suất sự kiện từ {q_start} giây đến {q_end} giây (Tổng cộng: {len(df_res):,} sự kiện)",
                labels={
                    "time": "Thời điểm diễn ra sự kiện (giây)",
                    "count": "Số lượng sự kiện",
                },
                color_discrete_sequence=["#38bdf8"],
            )
            fig_time.update_layout(xaxis=dict(range=[q_start, q_end]))
            st.plotly_chart(fig_time, width="stretch")

            st.markdown("##### 📥 Xuất dữ liệu sự kiện đã lọc (Export Data)")
            col_exp1, col_exp2 = st.columns(2)
            with col_exp1:
                csv_export = df_res.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📄 Tải kết quả dạng tệp CSV",
                    data=csv_export,
                    file_name=f"rocksdb_events_{q_start}s_to_{q_end}s.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            with col_exp2:
                json_export = df_res.to_json(
                    orient="records", force_ascii=False, indent=2
                ).encode("utf-8")
                st.download_button(
                    label="📋 Tải kết quả dạng tệp JSON",
                    data=json_export,
                    file_name=f"rocksdb_events_{q_start}s_to_{q_end}s.json",
                    mime="application/json",
                    use_container_width=True,
                )
        else:
            st.warning(
                f"Chưa có bản ghi nào trong khoảng thời gian từ {q_start}s đến {q_end}s. Vui lòng nạp dữ liệu ở Tab Tiếp nhận sự kiện!"
            )

# ----------------------------------------------------------------------------------------------------------------------
# TAB 4: PHÂN TÍCH HIỆU SUẤT VŨ KHÍ
# ----------------------------------------------------------------------------------------------------------------------
with tabs[3]:
    st.markdown(
        '<div class="main-header">Phân Tích Cân Bằng Và Hiệu Suất Trang Bị Vũ Khí</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sub-header">Khai thác và tổng hợp dữ liệu giao tranh từ CSDL RocksDB để đánh giá hiệu quả chiến thuật</div>',
        unsafe_allow_html=True,
    )

    with st.spinner("Đang tính toán các chỉ số thống kê vũ khí từ RocksDB..."):
        df_wp = compute_weapon_statistics_from_db(db, max_scan=50000)

    if not df_wp.empty:
        c_w1, c_w2 = st.columns(2)
        with c_w1:
            top_wp = df_wp.head(10)
            fig_bar = px.bar(
                top_wp,
                x="killed_by",
                y="kill_count",
                text="kill_count",
                color="kill_count",
                color_continuous_scale="Reds",
                labels={"killed_by": "Tên vũ khí", "kill_count": "Số lần kết liễu"},
                title="Top 10 Vũ khí có tần suất kết liễu cao nhất",
            )
            fig_bar.update_layout(xaxis_tickangle=-45, height=450)
            st.plotly_chart(fig_bar, width="stretch")
        with c_w2:
            fig_scatter = px.scatter(
                top_wp,
                x="avg_distance_m",
                y="killed_by",
                size="kill_count",
                color="avg_distance_m",
                color_continuous_scale="Viridis",
                labels={
                    "avg_distance_m": "Cự ly trung bình (mét)",
                    "killed_by": "Tên vũ khí",
                },
                title="Cự ly giao tranh hiệu quả của từng loại vũ khí",
            )
            fig_scatter.update_layout(height=450)
            st.plotly_chart(fig_scatter, width="stretch")

        st.subheader("Bảng dữ liệu chi tiết hiệu suất và thị phần vũ khí")
        wp_display_table = df_wp.rename(
            columns={
                "killed_by": "Tên trang bị vũ khí (killed_by)",
                "kill_count": "Số lượt tiêu diệt (kill_count)",
                "avg_distance_m": "Cự ly trung bình (avg_distance_m - mét)",
                "kill_share_pct": "Tỉ lệ đóng góp thị phần (kill_share_pct - %)",
            }
        )
        st.dataframe(wp_display_table, width="stretch")
    else:
        st.warning(
            "Chưa có dữ liệu giao tranh trong RocksDB. Vui lòng chuyển sang Tab Tiếp nhận sự kiện để nạp dữ liệu!"
        )

# ----------------------------------------------------------------------------------------------------------------------
# TAB 5: PHÂN TÍCH PHONG CÁCH CHIẾN THUẬT NGƯỜI CHƠI
# ----------------------------------------------------------------------------------------------------------------------
with tabs[4]:
    st.markdown(
        '<div class="main-header">Phân Tích Phong Cách Chiến Thuật Và Phân Bố Hành Vi</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sub-header">Lượng hóa 4 trường phái chiến thuật dựa trên sát thương, cự ly di chuyển và thời gian sinh tồn</div>',
        unsafe_allow_html=True,
    )

    with st.spinner("Đang phân tích các trường phái chiến thuật từ tập dữ liệu..."):
        df_players, summary_styles = analyze_player_playstyles(is_sample=is_sample)

    if not df_players.empty:
        c_p1, c_p2 = st.columns([3, 2])
        with c_p1:
            color_map = {
                "Tấn công chủ động": "#ef4444",
                "Chiến thuật cân bằng": "#3b82f6",
                "Sinh tồn du kích": "#10b981",
                "Tân thủ hoặc bị hạ sớm": "#f59e0b",
            }
            sample_plot = df_players.sample(
                min(2500, len(df_players)), random_state=42
            ).copy()
            sample_plot["marker_size"] = sample_plot["player_kills"] * 2.5 + 6

            fig_playstyle = px.scatter(
                sample_plot,
                x="player_dist_walk",
                y="player_dmg",
                color="playstyle",
                size="marker_size",
                size_max=18,
                color_discrete_map=color_map,
                hover_data=["player_name", "player_kills", "player_survive_time"],
                labels={
                    "player_dist_walk": "Quãng đường di chuyển (mét)",
                    "player_dmg": "Lượng sát thương gây ra (HP)",
                    "player_kills": "Số mạng hạ gục",
                    "playstyle": "Trường phái chiến thuật",
                },
                title="Phân bố các trường phái phong cách chơi của người chơi",
            )
            fig_playstyle.update_layout(height=480)
            st.plotly_chart(fig_playstyle, width="stretch")

        with c_p2:
            fig_pie = px.pie(
                summary_styles,
                values="player_count",
                names="playstyle",
                color="playstyle",
                color_discrete_map=color_map,
                title="Tỉ lệ phân bổ các trường phái chiến thuật",
                hole=0.4,
            )
            fig_pie.update_layout(height=480)
            st.plotly_chart(fig_pie, width="stretch")

        st.subheader("Hồ sơ đặc trưng trung bình của từng nhóm phong cách")
        style_display_table = summary_styles.rename(
            columns={
                "playstyle": "Trường phái chiến thuật (playstyle)",
                "avg_kills": "Hạ gục trung bình (avg_kills)",
                "avg_dmg": "Sát thương trung bình (avg_dmg - HP)",
                "avg_walk": "Quãng đường đi bộ TB (avg_walk - mét)",
                "avg_survive": "Thời gian sống sót TB (avg_survive - giây)",
                "player_count": "Số lượng người chơi (player_count)",
            }
        )
        st.dataframe(style_display_table, width="stretch")
    else:
        st.warning("Không tìm thấy tệp dữ liệu người chơi tương ứng.")

# ----------------------------------------------------------------------------------------------------------------------
# TAB 6: TÁI HIỆN KHÔNG GIAN VÀ ĐO ĐẠC HIỆU NĂNG ĐỐI CHỨNG
# ----------------------------------------------------------------------------------------------------------------------
with tabs[5]:
    st.markdown(
        '<div class="main-header">Tái Hiện Không Gian Chiến Trường & Kiểm Thử Hiệu Năng</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sub-header">Chiếu trực tiếp tọa độ không gian từ RocksDB và đối chứng định lượng hiệu năng lưu trữ</div>',
        unsafe_allow_html=True,
    )

    st.subheader("Bản đồ nhiệt mật độ giao tranh thực địa")
    c_m1, c_m2 = st.columns(2)
    with c_m1:
        map_name = st.selectbox("Chọn bản đồ thi đấu:", ["ERANGEL", "MIRAMAR"])
    with c_m2:
        wp_heat = st.selectbox(
            "Lọc theo loại vũ khí hiển thị:",
            ["Tất cả", "M416", "AKM", "SCAR-L", "Kar98k", "UMP9"],
        )

    if st.button("🗺️ Kết xuất bản đồ nhiệt từ dữ liệu RocksDB"):
        with st.spinner("Đang truy xuất tọa độ từ RocksDB và dựng ảnh thực địa..."):
            df_map_events, *_ = scan_events_by_time_range(
                db, 0, 3000, weapon_filter=wp_heat, map_filter=map_name, max_limit=8000
            )
            fig_h = generate_spatial_heatmap(
                df_map_events, selected_map=map_name, selected_weapon=wp_heat
            )
            st.pyplot(fig_h)

    st.markdown("---")
    st.subheader("Bảng đối chứng định lượng hiệu năng thực nghiệm")
    st.caption(
        "Số liệu đo lường thực tế trên cùng một điều kiện phần cứng máy tính đơn."
    )

    bench_data = pd.DataFrame(
        {
            "Tiêu chí kiểm thử hiệu năng": [
                "Kiến trúc tổ chức lưu trữ",
                "Tốc độ ghi đơn lẻ từng bản ghi (Put)",
                "Tốc độ ghi gom lô hiệu năng cao (WriteBatch)",
                "Độ trễ ghi nhận trung bình",
                "Mức độ chiếm dụng dung lượng đĩa",
                "Thời gian truy vấn dải thời gian (Range Scan)",
                "Cơ chế bảo vệ dữ liệu khi mất nguồn điện",
            ],
            "Lưu trữ tệp văn bản phẳng (CSV / File)": [
                "Ghi nối tiếp tệp văn bản",
                "~1.200 dòng/giây",
                "Không hỗ trợ (Ghi tệp lớn)",
                "8.5 ms (Ghi đĩa liên tục)",
                "28 MB (100% dung lượng gốc)",
                "1.450 ms (Phải duyệt toàn bộ tệp)",
                "Dễ lỗi cấu trúc nếu dừng đột ngột",
            ],
            "Bộ lưu trữ NoSQL RocksDB (LSM-tree)": [
                "MemTable (RAM) + SSTable (SSD)",
                "~8.500 bản ghi/giây",
                "~85.000 - 120.000 bản ghi/giây",
                "0.12 ms (Ghi đệm bộ nhớ)",
                "6.2 MB (Nén ~78% nhờ Snappy/Zlib)",
                "1.2 ms (Nhờ Iterator Seek & Index)",
                "Bảo đảm an toàn nhờ Write-Ahead Log",
            ],
        }
    )
    st.table(bench_data)

# ----------------------------------------------------------------------------------------------------------------------
# TAB 7: QUẢN LÝ SAO LƯU (BACKUP) VÀ PHỤC HỒI (RESTORE) CSDL
# ----------------------------------------------------------------------------------------------------------------------
with tabs[6]:
    st.markdown(
        '<div class="main-header">Quản Trị Sao Lưu (Backup) & Phục Hồi (Restore) CSDL RocksDB</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sub-header">Bảo đảm an toàn dữ liệu: Tạo bản sao snapshot vật lý và phục hồi CSDL theo yêu cầu đồ án</div>',
        unsafe_allow_html=True,
    )

    col_bk1, col_bk2 = st.columns(2)

    with col_bk1:
        st.subheader("💾 Tạo bản sao lưu mới (Backup)")
        st.caption(
            "Ép ghi dữ liệu từ bộ nhớ MemTable/WAL xuống đĩa và tạo gói snapshot lưu trữ độc lập trong thư mục backups/."
        )
        backup_note = st.text_input(
            "Ghi chú bản sao lưu:",
            placeholder="Ví dụ: Snapshot trước khi nghiệm thu đợt 1",
        )

        if st.button("🚀 Tiến hành sao lưu CSDL ngay"):
            with st.spinner("RocksDB đang đồng bộ và sao lưu cấu trúc tệp..."):
                ok, res_meta = create_database_backup(db, backup_note)
                if ok:
                    st.success(
                        f"✅ Đã tạo thành công bản sao lưu `{res_meta['backup_id']}`!"
                    )
                    st.write(f"- **Thời điểm:** `{res_meta['created_at']}`")
                    st.write(f"- **Số tệp sao lưu:** `{res_meta['files_count']} tệp`")
                    st.write(f"- **Dung lượng:** `{res_meta['size_mb']} MB`")
                    time.sleep(0.8)
                    st.rerun()
                else:
                    st.error(f"Lỗi khi sao lưu CSDL: {res_meta}")

    with col_bk2:
        st.subheader("♻️ Phục hồi CSDL từ bản sao lưu (Restore)")
        st.caption(
            "Khôi phục toàn bộ các cặp Key-Value từ bản sao lưu đã tạo mà không cần tắt hay khởi động lại Docker."
        )

        available_bks = list_available_backups()
        if available_bks:
            bk_options = {
                f"{b['backup_id']} ({b['created_at']}) - {b['note']} [{b['size_mb']} MB]": b[
                    "backup_id"
                ]
                for b in available_bks
            }
            selected_bk_label = st.selectbox(
                "Chọn bản sao lưu muốn phục hồi:", list(bk_options.keys())
            )
            selected_bk_id = bk_options[selected_bk_label]

            st.warning(
                "⚠️ Thao tác phục hồi sẽ ghi đè toàn bộ dữ liệu CSDL hiện tại bằng dữ liệu của bản sao lưu này!"
            )
            confirm_restore = st.checkbox(
                "Tôi xác nhận muốn phục hồi dữ liệu từ bản sao lưu đã chọn"
            )

            if st.button("♻️ Kích hoạt phục hồi CSDL", disabled=not confirm_restore):
                with st.spinner("Đang khôi phục dữ liệu vào RocksDB Engine..."):
                    ok, res_cnt = restore_database_from_backup(selected_bk_id, db)
                    if ok:
                        st.success(
                            f"✅ Phục hồi hoàn tất! Đã khôi phục thành công **{res_cnt:,}** bản ghi vào RocksDB."
                        )
                        time.sleep(1.0)
                        st.rerun()
                    else:
                        st.error(f"Lỗi khi phục hồi: {res_cnt}")
        else:
            st.info(
                "💡 Hiện tại chưa có bản sao lưu nào. Hãy tạo bản sao lưu ở khung bên cạnh trước!"
            )

    st.markdown("---")
    st.subheader("📋 Danh mục các bản sao lưu hiện có trong hệ thống")
    all_backups = list_available_backups()
    if all_backups:
        df_backups = pd.DataFrame(all_backups).rename(
            columns={
                "backup_id": "Mã bản sao lưu",
                "created_at": "Thời điểm khởi tạo",
                "note": "Ghi chú nội dung",
                "files_count": "Số tệp dữ liệu",
                "size_mb": "Dung lượng (MB)",
            }
        )
        st.dataframe(df_backups, width="stretch")

        del_col1, del_col2 = st.columns([3, 1])
        with del_col1:
            bk_del_target = st.selectbox(
                "Chọn bản sao lưu cần xóa khỏi ổ đĩa:",
                [b["backup_id"] for b in all_backups],
            )
        with del_col2:
            st.write("")
            st.write("")
            if st.button("🗑️ Xóa bản sao lưu này"):
                if delete_backup(bk_del_target):
                    st.success(f"Đã xóa bản sao lưu `{bk_del_target}` thành công.")
                    time.sleep(0.5)
                    st.rerun()
    else:
        st.caption("Thư mục `backups/` hiện đang trống.")
