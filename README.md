# Sales Insight Automator

A containerized full-stack prototype that lets sales teams upload CSV/XLSX files, generate AI executive summaries, and deliver the brief by email.

## Stack
- **Frontend**: React (Vite SPA)
- **Backend**: FastAPI with automatic Swagger docs
- **AI**: Groq Chat Completions API (with safe local fallback)
- **Email**: SMTP
- **DevOps**: Docker, Docker Compose, GitHub Actions CI

## Quick Start (Docker Compose)
1. Copy env file:
   ```bash
   cp .env.example .env
   ```
2. Fill in at least `GROQ_API_KEY` and SMTP settings in `.env` for end-to-end email delivery.
3. Build and run:
   ```bash
   docker compose up --build
   ```
4. Open:
   - Frontend: `http://localhost:5173`
   - Backend health: `http://localhost:8000/health`
   - Swagger docs: `http://localhost:8000/docs`

## Security Notes (Secured Endpoints)
- Upload endpoint validates file extension (`.csv`/`.xlsx`), required sales schema columns, and blocks oversized files (`MAX_FILE_SIZE_MB`).
- Row-level abuse guard: dataset rows are capped via `MAX_ROWS`.
- API supports optional shared-key protection via `API_KEY` + `X-API-Key` header.
- Email input is validated using `EmailStr`.
- Rate limiting enabled (`10 requests/minute` per IP).
- CORS is restricted through `ALLOWED_ORIGINS`.
- SMTP delivery is queued as a background task after summary generation.

## API
### `POST /api/summarize`
**Inputs**
- `recipient_email` (query)
- `file` (multipart form-data)

**Output**
- `recipient`
- `summary`
- `emailed` (`true` when SMTP config is present and the mail task is queued)

## CI/CD
PRs targeting `main` trigger `.github/workflows/ci.yml`, which:
- Installs backend dependencies and validates FastAPI app import
- Installs frontend dependencies
- Runs frontend lint
- Builds frontend production bundle

## Deployment Targets
- Frontend: Vercel/Netlify (recommended)
- Backend: Render/Fly.io/Railway (recommended)

> Add your live URLs here once deployed:
- Frontend URL: `TBD`
- Swagger URL: `TBD`

## Test Data
Use `data/sales_q1_2026.csv` for quick validation.


## Publish to GitHub
If your GitHub repository does not show these files yet, this local repository likely has no remote configured.

```bash
git remote -v
# if empty, add your repo
git remote add origin https://github.com/<your-org-or-user>/<repo>.git
git branch -M main
git push -u origin main
```

After that, every new change can be published with:

```bash
git push
```
