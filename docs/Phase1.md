Chào bạn, với tư cách là chuyên gia lập trình và mentor dự án, tôi sẽ hướng dẫn bạn triển khai **Phase 1: Xây dựng Cơ sở Hạ tầng (Infrastructure)**. Đây là giai đoạn quan trọng nhất, vì một nền móng yếu sẽ khiến việc mở rộng Big Data sau này bị đổ vỡ.

Chúng ta sẽ chuyển đổi kiến trúc từ "Monolithic script" (chạy 1 file python đơn lẻ như mô tả trong) sang kiến trúc **Event-Driven Microservices** sử dụng Docker và Kafka.

Dưới đây là hướng dẫn chi tiết từng bước:

-----

### 📋 MỤC TIÊU PHASE 1

1.  **Môi trường hóa:** Đóng gói môi trường bằng Docker để đảm bảo "chạy được trên máy tôi thì cũng chạy được trên server".
2.  **Message Broker:** Thiết lập Apache Kafka làm trung tâm trung chuyển dữ liệu (thay thế việc lưu file `.csv`/`.pkl` dễ lỗi).
3.  **Bảo mật:** Khắc phục triệt để vấn đề lộ Token bằng biến môi trường.

-----

### 🛠️ BƯỚC 1: CHUẨN HÓA CẤU TRÚC DỰ ÁN (PROJECT STRUCTURE)

Trước khi code, hãy tổ chức thư mục theo chuẩn Microservices. Đừng để tất cả trong thư mục gốc như cũ.

**Hành động:** Tạo cấu trúc thư mục như sau:

```text
crypto-trading-bot/
├── config/                  # Chứa file cấu hình (nếu có)
├── docker-compose.yml       # File "nhạc trưởng" điều phối Kafka & Zookeeper
├── .env                     # Nơi chứa bí mật (Token, Password) - KHÔNG COMMIT FILE NÀY
├── .gitignore               # Chặn git theo dõi .env và data rác
├── requirements.txt         # Các thư viện Python cần thiết
└── app/
    ├── __init__.py
    ├── producers/           # Service thu thập dữ liệu (thay thế data_collector)
    ├── consumers/           # Service xử lý ML & Trading
    ├── ml/                  # Core thuật toán (RandomForest, SVM...)
    └── utils/               # Các hàm dùng chung (Logger, Config Loader)
```

**Tại sao làm thế này?**

  * Tách biệt rõ ràng trách nhiệm (Separation of Concerns).
  * Dễ dàng scale: Ví dụ sau này muốn chạy 2 con Bot, chỉ cần nhân bản container `consumers`.

-----

### 🔐 BƯỚC 2: THIẾT LẬP BẢO MẬT (ENVIRONMENT VARIABLES)

Dựa trên vấn đề bảo mật nghiêm trọng đã nêu trong tài liệu cũ (lộ Token trong `token.txt`), chúng ta bắt buộc phải dùng `.env`.

**Hành động 1:** Tạo file `.env` tại thư mục gốc:

```ini
# KAFKA CONFIG
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# DISCORD CONFIG
DISCORD_BOT_TOKEN=your_real_discord_token_here_dont_share

# DATABASE / API CONFIG
BINANCE_API_KEY=your_binance_key
BINANCE_SECRET_KEY=your_binance_secret
```

**Hành động 2:** Cập nhật `.gitignore` ngay lập tức:

```text
__pycache__/
*.pyc
.env           <-- Quan trọng nhất
.venv/
data/          <-- Không commit dữ liệu training nặng
```

-----

### 🐳 BƯỚC 3: KHỞI TẠO KAFKA VỚI DOCKER COMPOSE

Đây là phần cốt lõi của Big Data. Chúng ta dùng **Docker Compose** để dựng cụm Kafka mà không cần cài đặt Java hay Kafka thủ công lên máy tính cá nhân.

**Thư viện/Công nghệ sử dụng:**

  * **Docker Engine:** Để chạy container.
  * **Image `confluentinc/cp-kafka`:** Bản Kafka ổn định nhất cho developer.
  * **Zookeeper:** Dịch vụ quản lý trạng thái cho Kafka (bắt buộc phải có để Kafka chạy).

**Hành động:** Tạo file `docker-compose.yml` với nội dung tối ưu sau:

```yaml
version: '3.8'

services:
  # 1. Zookeeper: Quản lý cluster Kafka
  zookeeper:
    image: confluentinc/cp-zookeeper:7.4.0
    hostname: zookeeper
    container_name: crypto_zookeeper
    ports:
      - "2181:2181"
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000

  # 2. Kafka Broker: Trái tim của hệ thống
  kafka:
    image: confluentinc/cp-kafka:7.4.0
    hostname: kafka
    container_name: crypto_kafka
    depends_on:
      - zookeeper
    ports:
      - "9092:9092" # Port để code Python bên ngoài kết nối vào
      - "29092:29092" # Port để các container nội bộ giao tiếp
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: 'zookeeper:2181'
      # Cấu hình listener để chấp nhận kết nối từ cả trong Docker và ngoài máy thật (Localhost)
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: 0
    volumes:
      - kafka_data:/var/lib/kafka/data # Persist data: Restart không bị mất dữ liệu

  # 3. Kafka UI (Optional): Giao diện web để debug dữ liệu cho tiện
  kafka-ui:
    image: provectuslabs/kafka-ui:latest
    container_name: crypto_kafka_ui
    ports:
      - "8080:8080"
    depends_on:
      - kafka
    environment:
      KAFKA_CLUSTERS_0_NAME: local
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:29092

volumes:
  kafka_data:
```

**Giải thích kỹ thuật chuyên sâu:**

  * `KAFKA_ADVERTISED_LISTENERS`: Đây là chỗ hay lỗi nhất. Chúng ta thiết lập 2 luồng:
      * `localhost:9092`: Để code Python chạy trên PyCharm/VSCode của bạn kết nối được.
      * `kafka:29092`: Để sau này nếu bạn đưa code Python vào Docker, nó sẽ dùng đường này.
  * `volumes`: Tôi đã thêm volume `kafka_data`. Nếu bạn tắt máy, dữ liệu giá coin đã thu thập **không bị mất**. Đây là điểm tối ưu so với việc chỉ chạy lệnh docker run thông thường.

-----

### 🐍 BƯỚC 4: THIẾT LẬP MÔI TRƯỜNG PYTHON

Để code Python giao tiếp được với hạ tầng trên, ta cần các thư viện driver.

**Hành động:** Tạo file `requirements.txt`:

```text
# Kafka Driver hiệu năng cao (C-based)
confluent-kafka==2.3.0

# Quản lý biến môi trường .env
python-dotenv==1.0.0

# Xử lý dữ liệu
pandas==2.1.0
numpy==1.26.0
scikit-learn==1.3.0  # Chuẩn bị cho Phase ML sau này

# Visualization (cho Dashboard sau này)
streamlit==1.28.0
plotly==5.18.0
```

**Cài đặt:**

```bash
python -m venv venv
# Windows
.\venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

-----

### 🚀 BƯỚC 5: VẬN HÀNH & KIỂM TRA (OPERATION)

Cuối cùng, hãy khởi động cỗ máy này lên.

1.  **Khởi động Docker:**
    Mở terminal tại thư mục dự án, chạy lệnh:

    ```bash
    docker-compose up -d
    ```

    *(Tham số `-d` nghĩa là Detached mode - chạy ngầm, không chiếm dụng terminal)*.

2.  **Kiểm tra trạng thái:**

    ```bash
    docker ps
    ```

    Bạn phải thấy 3 container (`crypto_kafka`, `crypto_zookeeper`, `crypto_kafka_ui`) có trạng thái **Up**.

3.  **Kiểm tra Kafka UI:**
    Mở trình duyệt truy cập: `http://localhost:8080`.
    Nếu thấy giao diện xanh lá báo "Online", chúc mừng bạn\! Bạn đã có một hệ thống Big Data sẵn sàng để hứng dữ liệu.

### 💡 LỜI KHUYÊN TỪ CHUYÊN GIA (OPTIMIZATION TIPS)

  * **Tài nguyên:** Với project crypto, lượng dữ liệu text không lớn. Tuy nhiên, nếu sau này scale, hãy giới hạn RAM cho Kafka trong `docker-compose.yml` (ví dụ: `mem_limit: 1g`) để tránh nó ăn hết RAM của máy development.
  * **Cơ chế lưu trữ:** Hiện tại đang dùng `KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1` vì chạy 1 node. Nếu đưa lên Production thật, tham số này phải là 3 để đảm bảo an toàn dữ liệu.

Đây là kết thúc **Phase 1**. Hạ tầng của bạn hiện tại đã mạnh mẽ hơn rất nhiều so với kiến trúc cũ mô tả trong. Bạn đã sẵn sàng để viết code Producer bắn dữ liệu vào hệ thống này ở Phase 2.