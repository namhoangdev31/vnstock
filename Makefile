.DEFAULT_GOAL := help

# Colors for terminal output
BLUE   := \033[1;34m
GREEN  := \033[1;32m
YELLOW := \033[1;33m
RED    := \033[1;31m
RESET  := \033[0m

.PHONY: help install dev frontend build-frontend docker-watch docker-up docker-down docker-logs docker-prod-up docker-prod-down docker-prod-logs db-migrate db-seed db-revision lint format check prek test test-cov clean

##@ Trợ giúp
help: ## Hiển thị danh sách các lệnh có sẵn
	@echo "$(BLUE)VNStock Quantitative Engine - Makefile Commands$(RESET)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Sử dụng: make $(GREEN)<lệnh>$(RESET)\n\n"} \
		/^[a-zA-Z_-]+:.*?##/ { printf "  $(GREEN)%-18s$(RESET) %s\n", $$1, $$2 } \
		/^##@/ { printf "\n$(BLUE)%s$(RESET)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Cài đặt & Khởi tạo
install: ## Cài đặt dependencies cho cả Backend (uv) và Frontend (bun)
	@echo "$(YELLOW)Cài đặt Python dependencies...$(RESET)"
	uv sync
	@echo "$(YELLOW)Cài đặt Frontend dependencies...$(RESET)"
	cd frontend && bun install

##@ Phát triển Local
dev: ## Khởi chạy Backend FastAPI server ở chế độ dev (port 8000)
	cd backend && uv run fastapi dev

frontend: ## Khởi chạy Frontend Vite/Nuxt dev server (port 5173)
	cd frontend && bun run dev

build-frontend: ## Build Frontend tĩnh xuất vào backend/app/frontend
	cd frontend && bun run build

##@ Docker Compose (Local Dev)
docker-watch: ## Chạy backend với Docker Compose kèm hot-reload (develop.watch)
	docker compose watch

docker-up: ## Khởi chạy container backend ở chế độ background
	docker compose up -d

docker-down: ## Dừng toàn bộ Docker containers môi trường local
	docker compose down

docker-logs: ## Xem log backend thời gian thực
	docker compose logs -f backend

##@ Docker Compose (Production)
docker-prod-up: ## Triển khai Production (Bao gồm Traefik HTTPS, PostgreSQL, Backend)
	docker compose --profile prod up --build -d

docker-prod-down: ## Dừng toàn bộ dịch vụ Production
	docker compose --profile prod down

docker-prod-logs: ## Xem log toàn bộ hệ thống Production
	docker compose --profile prod logs -f

##@ Cơ sở dữ liệu (Alembic)
db-migrate: ## Chạy Alembic migrations lên bản mới nhất (upgrade head)
	cd backend && uv run alembic upgrade head

db-seed: ## Chạy migration và seed dữ liệu ban đầu (scripts/prestart.sh)
	cd backend && uv run bash scripts/prestart.sh

db-revision: ## Tạo migration mới tự động (cú pháp: make db-revision m="mo_ta")
	@if [ -z "$(m)" ]; then echo "$(RED)Vui lòng cung cấp mô tả migration: make db-revision m=\"mo_ta\"$(RESET)"; exit 1; fi
	cd backend && uv run alembic revision --autogenerate -m "$(m)"

##@ Kiểm tra chất lượng mã (Lint & Check)
lint: ## Kiểm tra cú pháp và định dạng mã nguồn (ruff + biome)
	uv run ruff check backend
	cd frontend && bun run lint

format: ## Tự động định dạng mã nguồn (ruff format + biome format)
	uv run ruff format backend
	cd frontend && bunx biome check --write app.vue nuxt.config.ts pages components composables layouts data

check: ## Chạy kiểm tra toàn diện: ruff lint, ruff format check, type check, frontend lint
	@echo "$(YELLOW)Kiểm tra lint backend...$(RESET)"
	uv run ruff check backend
	@echo "$(YELLOW)Kiểm tra format backend...$(RESET)"
	uv run ruff format --check backend
	@echo "$(YELLOW)Kiểm tra types backend...$(RESET)"
	uv run ty check
	@echo "$(YELLOW)Kiểm tra frontend...$(RESET)"
	cd frontend && bun run lint
	@echo "$(GREEN)Tất cả các bước kiểm tra đều thành công!$(RESET)"

prek: ## Chạy toàn bộ Git pre-commit hooks bằng prek
	uv run prek run --all-files

##@ Kiểm thử (Tests)
test: ## Chạy bộ kiểm thử backend với pytest
	cd backend && uv run pytest

test-cov: ## Chạy kiểm thử kèm báo cáo độ phủ mã nguồn (coverage)
	cd backend && uv run coverage run -m pytest
	cd backend && uv run coverage report

##@ Dọn dẹp
clean: ## Xoá các thư mục cache, bytecode Python và tệp tin rác macOS
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name ".DS_Store" -delete 2>/dev/null || true
	find . -name "._*" -delete 2>/dev/null || true
	@echo "$(GREEN)Đã dọn dẹp sạch sẽ các tệp tin cache!$(RESET)"
