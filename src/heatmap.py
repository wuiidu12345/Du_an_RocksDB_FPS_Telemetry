import os
import matplotlib.pyplot as plt
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")

def generate_spatial_heatmap(df_events, selected_map="ERANGEL", selected_weapon="Tất cả", max_points=8000):
    """
    Vẽ lớp phủ mật độ giao tranh lên hình ảnh bản đồ game thực tế.
    Kích thước chuẩn Unreal Engine của PUBG: 800,000 x 800,000 units.
    """
    map_filename = "erangel.jpg" if selected_map == "ERANGEL" else "miramar.jpg"
    img_path = os.path.join(DATASET_DIR, map_filename)

    if df_events.empty:
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.text(0.5, 0.5, "Chưa có dữ liệu sự kiện từ RocksDB\nVui lòng nạp dữ liệu ở Tab 2 trước!", 
                ha="center", va="center", color="#38bdf8", fontsize=14)
        ax.set_facecolor("#1e293b")
        return fig

    # Lọc dữ liệu theo bản đồ
    df_filtered = df_events[df_events['map'] == selected_map].copy()
    if selected_weapon != "Tất cả":
        df_filtered = df_filtered[df_filtered['killed_by'] == selected_weapon]

    # Lọc các tọa độ hợp lệ trên đất liền (0 -> 800,000)
    df_filtered = df_filtered[
        (df_filtered['victim_pos_x'] > 0) & (df_filtered['victim_pos_x'] <= 800000) &
        (df_filtered['victim_pos_y'] > 0) & (df_filtered['victim_pos_y'] <= 800000)
    ]

    if len(df_filtered) > max_points:
        df_filtered = df_filtered.sample(max_points, random_state=42)

    fig, ax = plt.subplots(figsize=(9, 9), dpi=120)

    # Nạp ảnh vệ tinh bản đồ
    if os.path.exists(img_path):
        bg_img = Image.open(img_path)
        ax.imshow(bg_img, extent=[0, 800000, 800000, 0])
    else:
        ax.set_facecolor("#1e293b")
        ax.set_xlim(0, 800000)
        ax.set_ylim(800000, 0)

    # Vẽ lớp điểm nhiệt màu đỏ giao tranh
    ax.scatter(
        df_filtered['victim_pos_x'], 
        df_filtered['victim_pos_y'], 
        c='red', 
        s=5, 
        alpha=0.35, 
        edgecolors='none',
        label='Sự kiện từ RocksDB'
    )

    ax.set_title(f"Bản đồ nhiệt khu vực giao tranh nóng ({selected_map}) - {len(df_filtered):,} điểm từ RocksDB", fontsize=12, pad=12)
    ax.set_xlabel("Tọa độ không gian X (West - East)", fontsize=9)
    ax.set_ylabel("Tọa độ không gian Y (North - South)", fontsize=9)
    ax.grid(False)
    plt.tight_layout()

    return fig
