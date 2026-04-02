# OpenNews — Agent Onboarding & Project Handover

> Mục tiêu: bất kỳ agent nào mới vào dự án đều có thể đọc file này và biết **bắt đầu từ đâu**, **chạy thế nào**, **kiểm tra gì trước**, và **đang có gì đã chỉnh local**.

---

## 1) Project snapshot

- **Repo path (local):** `/home/quyt/clawd-dao/tmp_opennews_check/opennews`
- **Remote:** `https://github.com/IUnlimit/opennews.git`
- **Branch:** `main`
- **Observed upstream commit:** `d93f604` (`docs(screenshot): update homepage preview image`)

### Current local (uncommitted) changes

Các file local đã thêm/chỉnh (chưa commit):

1. `.env`
2. `.hfprep/` (thư mục phục vụ chuẩn bị cache/model)
3. `docker/Dockerfile.runtime`
4. `docker/docker-compose.override.yml`

---

## 2) What has been implemented locally

### A) Local runtime/env bootstrap

- File `.env` đã set:
  - `WEB_PORT=8080`
- Ghi chú trong `.env`:
  - nếu dùng LLM topic refinement cần set thêm:
    - `LLM_API_KEY`
    - `LLM_BASE_URL`
    - `LLM_MODEL`

### B) Runtime Docker image for backend/web

- Thêm `docker/Dockerfile.runtime` để chuẩn hóa runtime:
  - base: `python:3.12-slim`
  - tạo venv tại `/app/.venv`
  - cài `torch==2.2.2+cpu` từ CPU wheel index
  - cài dependencies từ `requirements.txt`
  - pin `numpy<2`
  - entrypoint: `python -m opennews.main`

### C) Compose override for runtime + HF cache

- Thêm `docker/docker-compose.override.yml`:
  - override build cho `backend` và `web` dùng `docker/Dockerfile.runtime`
  - bật online model download lần đầu:
    - `HF_HUB_OFFLINE=0`
    - `TRANSFORMERS_OFFLINE=0`
  - mount HuggingFace cache để tái sử dụng model:
    - `${HF_HOME:-/home/quyt/.cache/huggingface}:/root/.cache/huggingface`

---

## 3) Operational context from previous monitoring

Ghi nhận đã theo dõi pipeline OpenNews (run gần nhất):

- `run_id`: `5439cd62-faac-4815-a0ee-f14053226b58`
- Stage observed: `topics` → `refine_topics` → `market_impact` → `report`
- Topic refine qua LLM có log thành công (ví dụ: `after LLM refine: 36 clustered, 39 solo`)
- Có hiện tượng lệch trạng thái:
  - `job_runs.current_stage=report`
  - nhưng nhiều `job_items.current_node` vẫn `market_impact`

### Ý nghĩa cho agent mới

- Đừng chỉ nhìn 1 bảng trạng thái.
- Luôn đối chiếu song song:
  1. `job_runs`
  2. `job_items`
  3. logs backend
  4. batches/inserted_count

---

## 4) First 15-minute startup checklist (for any new agent)

1. **Vào đúng repo path**
   ```bash
   cd /home/quyt/clawd-dao/tmp_opennews_check/opennews
   ```

2. **Xác nhận trạng thái local**
   ```bash
   git status --short
   git remote -v
   ```

3. **Kiểm tra env quan trọng**
   - `.env` có `WEB_PORT`
   - Nếu cần refine bằng LLM: set `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`

4. **Xác nhận HF cache path**
   - host có quyền ghi `${HF_HOME:-/home/quyt/.cache/huggingface}`

5. **Khởi chạy bằng docker compose (với override)**
   - đảm bảo compose đang đọc `docker/docker-compose.override.yml`

6. **Theo dõi logs khi chạy pipeline**
   - chú ý transitions: `topics/refine_topics/market_impact/report`
   - check lỗi model download, timeout, DB connectivity

7. **Xác minh kết quả thật sự ghi DB/output**
   - không chỉ dựa vào `current_stage`
   - phải check `inserted_count`, `batch_id`, record count

---

## 5) Suggested workflow when debugging stuck pipeline

Nếu pipeline có dấu hiệu “đứng”:

1. Chụp snapshot trạng thái hiện tại (run_id, stage, inserted_count, batch_id)
2. So sánh số lượng items theo status/node
3. Kiểm tra log backend có còn gọi LLM/API 200 OK hay không
4. Nếu stage lên `report` nhưng items chưa thoát `market_impact`:
   - đánh dấu là **stage/item state drift**
   - tiếp tục monitor thêm một vòng timeout hợp lý trước khi kết luận fail

---

## 6) Commit discipline (recommended)

Vì hiện có local changes chưa commit, agent mới nên:

1. Tạo branch làm việc riêng
2. Commit theo nhóm rõ mục đích:
   - `chore(runtime): add docker runtime image`
   - `chore(compose): add hf cache + runtime override`
   - `docs(onboarding): add AGENT_ONBOARDING`
3. Mỗi commit có note impact và rollback nhanh

---

## 7) Quick commands (reference)

```bash
# repo context
cd /home/quyt/clawd-dao/tmp_opennews_check/opennews

git status --short
git log --oneline -n 10
git remote -v

# inspect key files
cat .env
cat docker/Dockerfile.runtime
cat docker/docker-compose.override.yml
```

---

## 8) Handover note for next agent

Khi nhận việc OpenNews, hãy đọc theo thứ tự:
1. `README.md`
2. `AGENT_ONBOARDING.md` (file này)
3. `.env`
4. `docker/Dockerfile.runtime`
5. `docker/docker-compose.override.yml`

Sau đó mới bắt đầu chạy/pipeline để tránh mất thời gian vì thiếu env hoặc thiếu cache model.

---

_Last updated: 2026-04-02 (Asia/Bangkok)_
