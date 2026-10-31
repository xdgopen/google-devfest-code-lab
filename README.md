# Blogger Agent · Google ADK codelab (mở rộng)

Hệ thống multi-agent **lập dàn ý → viết → tự kiểm duyệt** bài blog kỹ thuật, xây dựng theo codelab
[Build an AI Agent with Google ADK](https://codelabs.developers.google.com/build-ai-agent-google-adk)
(`google-adk==2.2.0`, Gemini), được mở rộng thành một ứng dụng có thể chạy production.

| | |
|---|---|
| 🤖 Agent | `Blogger` → `RobustBlogPlanner` / `RobustBlogWriter` (LoopAgent, **thoát sớm** khi checker trả "ok"), Researcher (Google Search), GitHub context, SEO, thống kê |
| 🧠 Memory | Profile memory (`user:` state: sở thích, lịch sử bài) và long-term memory (ADK MemoryService / Vertex AI Memory Bank) |
| 🛡 Guardrails | Prompt injection (EN/VI), chủ đề cấm, chặn secret, redact PII ở cả hai chiều, tool budget và allow-list host, Gemini safety settings |
| 🎨 UI | React + Vite + TS theo design system `main-design`; stream tiến trình qua SSE; responsive; đạt chuẩn a11y (axe) |
| 🗄 Lưu trữ | Postgres / Cloud SQL (session), GCS (artifact) |
| 🐳 Docker | Image multi-stage, docker-compose (app + Postgres + Vite dev + ADK Web UI) |
| ✅ Test | 92 test backend (coverage 98%, offline với FakeLlm) và 28 test frontend (Vitest + axe) |
| ☁️ Deploy | Cloud Run + Cloud SQL + Secret Manager + GCS, SA riêng; hoặc `adk deploy cloud_run` như codelab |

## Quick start

```bash
cp .env.example .env                 # điền GOOGLE_API_KEY (AI Studio)
docker compose up --build -d db app  # http://localhost:8080
```

Hoặc chạy đúng như codelab:

```bash
make venv && cd backend && cp ../.env.example .env && .venv/bin/adk web   # http://127.0.0.1:8000
```

Test: `make test` · Deploy GCP: `PROJECT_ID=<id> make gcp-setup gcp-deploy`

📘 **Hướng dẫn đầy đủ (ENV, local, test, deploy GCP, chi phí, troubleshooting):** [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
