# Rule: No Frontend Build During Development

## 1. Nguyên Tắc Cốt Lõi (Core Directive)
Trong quá trình phát triển (development), hệ thống sử dụng môi trường đồng bộ nóng:
- Lệnh nền `make docker-watch` (`docker compose watch`) và Nuxt Vite HMR (Hot Module Replacement) tự động phản ánh mọi thay đổi trong mã nguồn Vue/TS/CSS tức thì mà không cần biên dịch lại toàn bộ.

**TUYỆT ĐỐI KHÔNG CHẠY `bun run build`** (hoặc `npm run build`, `yarn build`) sau mỗi lượt chỉnh sửa frontend trừ khi người dùng có chỉ định rõ ràng.

## 2. Quy Trình Kiểm Thử Chuẩn (Dev Verification)
Khi chỉnh sửa mã nguồn Frontend, chỉ thực hiện 2 bước kiểm tra chất lượng mã:
1. `bun run lint` (Biome linter & formatter kiểm tra cú pháp).
2. `bun run typecheck` (Nuxt vue-tsc kiểm tra type safety).

## 3. Khi Nào Mới Chạy `bun run build`?
Chỉ chạy lệnh build production trong các trường hợp sau:
1. Người dùng yêu cầu trực tiếp bằng lời (ví dụ: "hãy build frontend", "build dự án", "chuẩn bị deploy").
2. Đóng gói bản phát hành (release / deployment staging / production).
