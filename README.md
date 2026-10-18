# **HƯỚNG DẪN CÀI ĐẶT VÀ VẬN HÀNH DỰ ÁN ROCKSDB FPS TELEMETRY**

Tài liệu này hướng dẫn chi tiết quy trình thiết lập môi trường và vận hành hệ thống lưu trữ dữ liệu cục bộ tốc độ cao cho ứng dụng quản lý nhật ký và sự kiện dựa trên công nghệ cơ sở dữ liệu NoSQL Key-Value **RocksDB**, môi trường ảo hóa đóng gói **Docker** và giao diện điều khiển **Streamlit Dashboard** thông qua các kịch bản tự động hóa `.bat`.

<br>

## **📝 BƯỚC 1. YÊU CẦU CHUẨN BỊ TRƯỚC KHI CÀI ĐẶT**

Để đảm bảo hệ thống tự động hóa hoạt động chính xác và không phát sinh lỗi trong quá trình thực nghiệm, máy tính cần cài đặt sẵn công cụ nền tảng sau **(Đường dẫn tải ở cuối tài liệu)**:

- **Docker Desktop:** Sử dụng để quản lý, đóng gói và khởi chạy tự động toàn bộ môi trường động cơ lưu trữ gồm Linux Debian, Python 3.10, thư viện nhị phân C++ RocksDB (`rocksdict`) và bảng điều khiển Streamlit.
- **Dung lượng ổ đĩa khả dụng:** Ổ đĩa cài đặt dự án cần còn trống tối thiểu 5GB để Docker tải các hình ảnh nền tảng và khởi tạo không gian lưu trữ cho các tệp bảng chuỗi sắp xếp (`.sst`) và nhật ký ghi trước (`.log`).

<br>

**⚠️ LƯU Ý QUAN TRỌNG VỀ TỐI ƯU PHẦN CỨNG (WSL2 / RAM)**

Mặc định máy ảo Linux của Docker Desktop (WSL2) có thể chiếm dụng tới 50% tổng dung lượng RAM của hệ điều hành máy tính. Để tối ưu hóa tài nguyên phần cứng và tránh hiện tượng cạnh tranh bộ nhớ đệm, bạn nên thiết lập cấu hình giới hạn tài nguyên như sau:

1. Nhấn tổ hợp phím `Windows + R`, gõ `%UserProfile%` rồi nhấn **Enter**.
2. Tạo một tệp văn bản mới mang tên **`.wslconfig`** (chọn lưu ở định dạng All Files).
3. Dán nội dung cấu hình sau vào và lưu lại:
   ```ini
   [wsl2]
   memory=3GB
   processors=4
   autoMemoryReclaim=gradual
   ```
4. Mở Command Prompt (CMD) và thực thi lệnh `wsl --shutdown` để hệ thống áp dụng giới hạn này.

<br>

**⚠️ LƯU Ý KHI KHỞI CHẠY DOCKER**

- Trước khi thực hiện cài đặt hoặc chạy dự án, luôn đảm bảo phần mềm **Docker Desktop đã được bật và đang ở trạng thái Engine running**.
- Toàn bộ quy trình cài đặt môi trường và khởi chạy đã được tự động hóa 100%, không cần cài đặt thêm bất kỳ công cụ dòng lệnh hay trình biên dịch C++ nào trực tiếp lên hệ điều hành máy chủ Windows.

<br>

## **🚀 BƯỚC 2. QUY TRÌNH KHỞI CHẠY VÀ KIỂM THỬ HỆ THỐNG**

Hệ thống được thiết kế theo kiến trúc lưu trữ nhúng cục bộ độc lập: tầng động cơ lưu trữ NoSQL hiệu năng cao **RocksDB Engine (LSM-tree)** và tầng quản trị, trực quan hóa qua **Web Dashboard**.

<br>

### 1: THIẾT LẬP MÔI TRƯỜNG DOCKER BAN ĐẦU (Chỉ chạy 1 lần duy nhất)

1. Mở sẵn phần mềm Docker Desktop.
2. Di chuyển vào thư mục dự án `Du_an_RocksDB_FPS_Telemetry`.
3. Nhấp đúp chuột để chạy tệp `setup.bat`.

_Cơ chế hoạt động:_ Kịch bản sẽ tự động kiểm tra trạng thái Docker, tải hình ảnh nền tảng Python 3.10-slim, nạp thư viện kết nối nhị phân C++ của RocksDB cùng các gói khoa học dữ liệu Pandas, NumPy, Plotly, Streamlit vào container `nosql-rocksdb-engine`. Khi cửa sổ dòng lệnh xuất hiện thông báo `[OK] CAI DAT HOAN TAT!`, nhấn phím bất kỳ để hoàn thành.

<br>

### 2: THỰC THI KIỂM THỬ VÀ ĐO ĐẠC HIỆU NĂNG ROCKSDB (Có thể bỏ qua)

Để đo lường định lượng tốc độ và chứng minh tính ưu việt của cơ sở dữ liệu Key-Value:

- Nhấp đúp chuột để chạy tệp `run_benchmark.bat`.

_Cơ chế hoạt động:_ Kịch bản sẽ kích hoạt chương trình kiểm thử độc lập bên trong container nhằm:

- Đo đạc thông lượng ghi đơn lẻ từng bản ghi (`Put`).
- Đo đạc thông lượng ghi gom lô hiệu năng cao qua bộ đệm (`WriteBatch`).
- So sánh tỷ lệ gia tăng hiệu năng (Speedup) giữa hai phương thức ghi nhận.
- Đo tốc độ quét dải thời gian liên tục (`Range Scan`) thông qua con trỏ `Iterator.seek()`.

<br>

### 3: KHỞI CHẠY BẢNG ĐIỀU KHIỂN QUẢN TRỊ VÀ TRỰC QUAN HÓA

Để mở bảng điều khiển tương tác phục vụ báo cáo và nghiệm thu đề tài:

- Nhấp đúp chuột để chạy tệp `run_demo.bat`.

_Kết quả:_ Trình duyệt web sẽ tự động mở trang quản trị tại địa chỉ:

- Giao diện Web Quản trị RocksDB: **http://localhost:8505**
- Cổng dịch vụ được thiết lập riêng biệt (`8505:8505`), tuyệt đối không gây xung đột cổng với các dự án khác trên máy chủ.

<br>

### 4: TIỆN ÍCH DỌN DẸP DOCKER (Khi hoàn thành nghiệm thu)

Nếu muốn giải phóng hoàn toàn dung lượng ổ đĩa và gỡ bỏ môi trường Docker sau khi hoàn tất:

- Nhấp đúp chuột vào tệp `clean_docker.bat`.
- Kịch bản sẽ tự động dừng container, xóa bỏ hình ảnh vùng chứa và dọn sạch bộ nhớ đệm xây dựng (Build Cache) của Docker chỉ với một thao tác.

<br>

## **📂 CẤU TRÚC THƯ MỤC DỰ ÁN**

Cấu trúc thư mục nguồn của dự án được tổ chức khoa học như sau:

```ini
Du_an_RocksDB_FPS_Telemetry/
│
├── dataset/                              <-- [GitHub] Thư mục chứa tập dữ liệu
│   └── ...
│
├── rocksdb_data/                         <-- [Tự động tạo] Thư mục chứa các tệp nhị phân SSTable, WAL của RocksDB
│   └── ...
│
├── scripts/                              <-- [GitHub] Kịch bản kiểm thử và đo đạc định lượng độc lập
│   └── ...
│
├── src/                                  <-- [GitHub] Mã nguồn ứng dụng và logic xử lý cốt lõi
│   └── ...
│
├── .dockerignore
│
├── .gitattributes
│
├── .gitignore
│
├── docker-compose.yml
│
├── Dockerfile
│
├── requirements.txt                      <-- [GitHub] Danh mục các gói thư viện phụ thuộc
│
├── setup.bat                             <-- [GitHub] Kịch bản khởi tạo và biên dịch môi trường Docker tự động
│
├── run_benchmark.bat                     <-- [GitHub] Kịch bản chạy đo đạc kiểm thử hiệu năng RocksDB
│
├── run_demo.bat                          <-- [GitHub] Kịch bản khởi chạy giao diện Web Dashboard tại cổng 8505
│
├── clean_docker.bat                      <-- [GitHub] Tiện ích dọn dẹp sạch sẽ tài nguyên Docker của dự án
│
└── README.md
```

<br>

## **🌐 NGUỒN GỐC DỮ LIỆU THỰC NGHIỆM**

- **Bộ dữ liệu gốc:** Bộ dữ liệu sự kiện đo đạc từ xa (Telemetry Events) của tựa game PUBG được phát hành công khai trên nền tảng Kaggle tại đường dẫn: https://www.kaggle.com/datasets/skihikingkevin/pubg-match-deaths/data
- **Đặc tính kỹ thuật của dữ liệu gốc:** Bộ dữ liệu bao gồm hai tệp lớn là `agg_match_stats_0.csv` (chỉ số thống kê người chơi theo trận) và `kill_match_stats_final_0.csv` (nhật ký chi tiết các sự kiện hạ gục theo chuỗi thời gian), tổng dung lượng đạt xấp xỉ 4.0 GB với hơn 13 triệu dòng bản ghi.
- **Tối ưu hóa và chuẩn hóa dữ liệu:** Để phù hợp với tài nguyên bộ nhớ máy tính cá nhân (RAM 8GB – 16GB) và bảo đảm tính linh hoạt khi thử nghiệm, dữ liệu được trích xuất có kiểm soát thành 2 tập chuẩn hóa:
  - **Tập kiểm thử nhanh (50.000 bản ghi):** Sử dụng để kiểm tra nhanh các chức năng truy vấn, lọc dữ liệu và kết xuất bản đồ nhiệt với độ trễ thấp nhất.
  - **Tập thực nghiệm quy mô lớn (300.000 bản ghi):** Đóng vai trò là tập dữ liệu chính đại diện cho tải ghi lớn của hệ thống, dùng để kiểm chứng năng lực tiếp nhận hàng trăm nghìn sự kiện của kiến trúc LSM-tree trên RocksDB và đo đạc các chỉ số hiệu năng thực tế.

<br>

## **📥 ĐƯỜNG DẪN TẢI CÔNG CỤ NỀN TẢNG**

Để thuận tiện cho quá trình cài đặt và nghiệm thu, bạn có thể truy cập liên kết chính thức dưới đây để tải Docker Desktop:

- Tải Docker Desktop cho Windows: https://docs.docker.com/desktop/setup/install/windows-install/
