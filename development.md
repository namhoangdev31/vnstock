# Hướng Dẫn Phát Triển & Triển Khai (Development & Deployment Guide)

Tài liệu hướng dẫn toàn diện từ môi trường phát triển local (tối ưu riêng cho macOS) đến triển khai production bằng Docker Compose (1 lệnh duy nhất kèm HTTPS tự động) và Cloud.

---

## 1. Môi Trường Phát Triển Local (Local Development)

### Phương Án A: Chạy trực tiếp trên máy (Khuyên dùng khi dev nhanh)

Phương án này tiết kiệm CPU/RAM tối đa và phản hồi tức thì khi sửa code:

1. **Khởi động database PostgreSQL**:
   ```bash
   docker compose up -d db
   ```
   *(Hoặc cấu hình `DATABASE_URL` kết nối trực tiếp đến Supabase / PostgreSQL cloud trong file `.env`)*

2. **Cài đặt và chạy Backend (FastAPI)**:
   ```bash
   cd backend
   uv sync
   uv run bash scripts/prestart.sh
   uv run fastapi dev
   ```
   Backend khởi chạy tại: <http://localhost:8000>
   Swagger UI API docs: <http://localhost:8000/docs>

3. **Cài đặt và chạy Frontend (Nuxt / Vue 3)**:
   Mở terminal riêng tại thư mục gốc:
   ```bash
   cd frontend
   bun install
   bun run dev
   ```
   Frontend Vite dev server khởi chạy tại: <http://localhost:5173>

4. **Build Frontend tĩnh tích hợp vào FastAPI**:
   ```bash
   cd frontend
   bun run build
   ```
   Bản build được xuất ra `backend/app/frontend` và FastAPI tự động phục vụ giao diện tại <http://localhost:8000>.

---

### Phương Án B: Chạy Backend qua Docker Compose (`watch` mode)

Khi chạy local, hệ thống chỉ khởi chạy container `backend` (FastAPI + Nuxt static) và kết nối thẳng vào database cloud (Supabase) qua `DATABASE_URL` trong `.env`. Dịch vụ `proxy` và `db` được tách riêng cho môi trường production, giúp không bị chiếm cổng 80/5432 và tối ưu tài nguyên tối đa cho Mac:

```bash
docker compose watch
```

Docker Compose chạy trực tiếp trên file `compose.yml` duy nhất:
* **Hot-reload source code**: Tự động đồng bộ file Python khi chỉnh sửa thư mục `backend/`.
* **Tự động rebuild**: Khi `pyproject.toml` hoặc thư mục `frontend/` thay đổi.

**Địa chỉ truy cập trực tiếp:**
* **Ứng dụng (Frontend + API)**: <http://localhost:8000>
* **API Documentation (Swagger UI)**: <http://localhost:8000/docs>

---

## 2. Hướng Dẫn Tối Ưu Cho macOS & Apple Silicon

Khi chạy Docker trên macOS (M1/M2/M3/M4 hoặc Intel Mac), áp dụng các thiết lập sau để đạt hiệu năng cao nhất:

### 1. Cấu hình Docker Desktop / OrbStack
* **File Sharing (VirtioFS)**: Trong **Docker Desktop > Settings > General**, bật **VirtioFS**. Tốc độ I/O nhanh hơn tới 10 lần so với gRPC-FUSE cũ.
* **Rosetta 2 Emulation**: Bật **Use Rosetta for x86/amd64 emulation on Apple Silicon** để giả lập các image x86 với tốc độ gần như native.
* **Tài nguyên**: Cấp tối thiểu **4 Cores CPU** và **4 - 6 GB RAM** trong **Settings > Resources**.
* **Giải pháp OrbStack**: [OrbStack](https://orbstack.dev) chạy container cực nhẹ trên macOS, tiêu tốn gần như 0% CPU khi idle và khởi động chỉ mất 1-2 giây.

### 2. Xử lý xung đột cổng 80 trên macOS
Trên macOS, cổng 80 thường bị chiếm bởi dịch vụ Apache mặc định (`httpd`):
* **Kiểm tra tiến trình chiếm cổng 80**:
  ```bash
  sudo lsof -i :80
  ```
* **Tắt Apache mặc định của macOS**:
  ```bash
  sudo apachectl stop
  ```
* **Hoặc đổi cổng HTTP trong `.env`**:
  Thêm dòng `PORT_HTTP=8080` vào `.env`. Traefik sẽ lắng nghe trên cổng 8080 thay vì 80.

### 3. Tối ưu hoá File Watcher (`docker compose watch`)
Hệ thống đã cấu hình sẵn ignore rules loại bỏ các file rác macOS:
* Loại bỏ `**/.DS_Store` và Apple metadata (`**/._*`).
* Loại bỏ bytecode và cache Python (`**/__pycache__`, `**/*.pyc`, `.pytest_cache`, `.ruff_cache`, `.venv`).
* Loại bỏ build artifacts frontend (`.nuxt`, `.output`, `node_modules`, `dist`).
Điều này triệt tiêu tình trạng Docker watch bị trigger liên tục gây tăng vọt CPU trên Mac.

---

## 3. Triển Khai Production (Production Deployment)

### Phương Án 1: Docker Compose trên VPS/Server riêng (Khuyên dùng)

Đây là phương pháp triển khai nhanh và chuẩn hoá nhất. Stack đã được tinh gọn chỉ gồm 3 container: **`proxy`** (Traefik v3.7), **`db`** (PostgreSQL 18), và **`backend`** (FastAPI + Nuxt static).

#### Bước 1: Chuẩn bị DNS & Server
1. Thuê VPS Linux (Ubuntu 22.04 / 24.04 khuyên dùng).
2. Cài đặt Docker Engine trên server: [Hướng dẫn cài Docker Engine](https://docs.docker.com/engine/install/ubuntu/).
3. Trỏ 1 bản ghi DNS **A/AAAA** duy nhất từ tên miền của bạn (ví dụ: `vnstock.example.com`) về địa chỉ IP của VPS. *(Không cần tạo thêm bất kỳ subdomain phụ nào)*.

#### Bước 2: Thiết lập biến môi trường trên Server
Tạo hoặc export các biến môi trường trên server:
```bash
export DOMAIN=vnstock.example.com
export ENABLE_TLS=true
export HTTP_MIDDLEWARES=redirect-https
export RESTART_POLICY=always
export BACKEND_COMMAND="fastapi run --workers 4"
export PROJECT_NAME="VNStock Quantitative Engine"
export FIRST_SUPERUSER=admin@example.com
export FIRST_SUPERUSER_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export POSTGRES_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
```

#### Bước 3: Triển khai với 1 lệnh duy nhất (Fast Deploy)
Kích hoạt profile `prod` để chạy đầy đủ cả Traefik HTTPS proxy và PostgreSQL server:
```bash
docker compose --profile prod up --build -d
```
*(Hoặc export `COMPOSE_PROFILES=prod` trên server, khi đó chỉ cần gõ `docker compose up --build -d`)*

**Cơ chế tự động hoá:**
* **HTTPS / SSL tự động**: Traefik tự động gửi TLS challenge đến Let's Encrypt và kích hoạt chứng chỉ SSL hợp lệ cho `${DOMAIN}`. Mọi truy cập HTTP cổng 80 tự động chuyển hướng sang HTTPS cổng 443 thông qua middleware `redirect-https`.
* **Auto Migration & Seed**: Khi container `backend` khởi động, `lifespan` tự động áp dụng các Alembic migrations mới nhất và tạo tài khoản superuser ban đầu (không cần chạy thủ công `prestart.sh`).
* **Storage chuẩn**: Dữ liệu database được gắn kết bền vững tại Docker volume `app-db-data:/var/lib/postgresql/data` kèm `shm_size: 512mb`.

#### Bước 4: Giám sát và quản lý
* **Xem log backend theo thời gian thực**:
  ```bash
  docker compose logs -f backend
  ```
* **Xem log cấp chứng chỉ SSL của Traefik**:
  ```bash
  docker compose logs -f proxy
  ```
* **Dừng toàn bộ hệ thống**:
  ```bash
  docker compose down
  ```

---

### Phương Án 2: Triển Khai FastAPI Cloud (PaaS)

Nếu bạn sử dụng dịch vụ đám mây [FastAPI Cloud](https://fastapicloud.com):

1. Tạo ứng dụng mới trên FastAPI Cloud và đặt **Application Directory** là `backend`.
2. Kết nối cơ sở dữ liệu PostgreSQL thông qua tích hợp Supabase hoặc Neon.
3. Thiết lập biến môi trường:
   * **Variables**: `PROJECT_NAME`, `FIRST_SUPERUSER`, `FRONTEND_HOST=https://your-app.fastapicloud.dev`
   * **Secrets**: `SECRET_KEY`, `FIRST_SUPERUSER_PASSWORD`, `DATABASE_URL`
4. Cấu hình Continuous Deployment qua GitHub Actions:
   * Sử dụng file workflow `.github/workflows/deploy.yml`.
   * Cấu hình secret `FASTAPI_CLOUD_TOKEN` và `FASTAPI_CLOUD_APP_ID` trên repository GitHub.

---

## 4. CI/CD Tự Động Hoá Với GitHub Actions

Trong thư mục `.github/workflows/` đã có sẵn các kịch bản tự động hoá:

* **`deploy-docker-compose.yml`**: Tự động triển khai lên server VPS riêng khi merge code vào nhánh chính thông qua GitHub Self-Hosted Runner.
* **`deploy.yml`**: Tự động build và deploy lên FastAPI Cloud.
* **`test.yml`**: Tự động chạy unit test, linter (`ruff`), type checker (`ty`) trước khi merge PR.

---

## 5. Quản Lý File Cấu Hình & Biến Môi Trường (`.env`)

File `.env` ở thư mục gốc chứa các thiết lập mặc định cho môi trường chạy:

| Biến môi trường | Mục đích | Ví dụ / Mặc định |
|---|---|---|
| `FASTAPI_ENV` | Chế độ chạy | `development` hoặc `production` |
| `PROJECT_NAME` | Tên dự án | `"VNStock Quantitative Engine"` |
| `DOMAIN` | Tên miền triển khai production | `vnstock.example.com` |
| `SECRET_KEY` | Khoá bí mật mã hoá JWT tokens | Chuỗi ngẫu nhiên 32 ký tự |
| `FIRST_SUPERUSER` | Email quản trị viên khởi tạo | `admin@example.com` |
| `FIRST_SUPERUSER_PASSWORD` | Mật khẩu quản trị viên khởi tạo | Mật khẩu bảo mật |
| `DATABASE_URL` | Chuỗi kết nối PostgreSQL | `postgresql://user:pass@db:5432/app` hoặc URL Supabase pooler |
| `POSTGRES_PASSWORD` | Mật khẩu root PostgreSQL nội bộ | Mật khẩu ngẫu nhiên |
| `PORT_HTTP` | Cổng HTTP proxy cục bộ (tuỳ chọn) | `80` (hoặc `8080` nếu tránh trùng cổng trên Mac) |
| `VNSTOCK_APIKEY` | Khoá API tài trợ Vnstock | `vnstock_...` |
| `DNSE_API_KEY` | OpenAPI key DNSE | Chuỗi base64 OpenAPI |
| `DNSE_API_SECRET` | OpenAPI secret DNSE | Secret ký xác thực |

> [!CAUTION]
> Tuyệt đối không commit các khoá bí mật production (`SECRET_KEY`, `POSTGRES_PASSWORD`, API Keys) lên kho lưu trữ Git công khai.

---

## 6. Tiêu Chuẩn Chất Lượng Code & Pre-commit Hooks

Dự án sử dụng bộ công cụ hiện đại tốc độ cao:
* **Backend**: `uv`, `ruff` (linter & formatter), `ty` (type checking).
* **Frontend**: `bun`, `@biomejs/biome` (linter & formatter), `vue-tsc` (type checking).
* **Git Hooks**: `prek` (công cụ thay thế `pre-commit` viết bằng Rust, tốc độ siêu nhanh).

### Cài đặt Hook tự động kiểm tra trước khi Commit
```bash
uv run prek install -f
```
Mỗi khi bạn thực hiện `git commit`, `prek` sẽ tự động định dạng và kiểm tra toàn bộ mã nguồn.

### Chạy kiểm tra thủ công nhanh:
* **Kiểm tra Backend**:
  ```bash
  uv run ruff check backend
  uv run ruff format --check backend
  uv run ty check
  ```
* **Kiểm tra Frontend**:
  ```bash
  cd frontend && bun run lint
  ```
