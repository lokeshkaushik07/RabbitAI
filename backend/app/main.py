from __future__ import annotations

from fastapi import BackgroundTasks, Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request

from .config import settings
from .services import build_data_snapshot, generate_summary, parse_sales_file, send_email_summary

app = FastAPI(title=settings.app_name, version='1.1.0')

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

origins = [origin.strip() for origin in settings.allowed_origins.split(',') if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['POST', 'GET'],
    allow_headers=['*'],
)


class SummaryResponse(BaseModel):
    recipient: EmailStr
    summary: str
    emailed: bool


def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail='Invalid API key')


@app.get('/health')
async def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.post('/api/summarize', response_model=SummaryResponse)
@limiter.limit('10/minute')
async def summarize_sales_data(
    request: Request,
    background_tasks: BackgroundTasks,
    recipient_email: EmailStr,
    file: UploadFile = File(...),
    _: None = Depends(verify_api_key),
):
    _ = request
    file_bytes = await file.read()
    size_limit = settings.max_file_size_mb * 1024 * 1024
    if len(file_bytes) > size_limit:
        raise HTTPException(status_code=413, detail=f'File exceeds {settings.max_file_size_mb}MB limit.')

    try:
        df = parse_sales_file(file_bytes, file.filename or 'uploaded_file')
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    snapshot = build_data_snapshot(df)

    try:
        summary = await generate_summary(snapshot)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f'LLM provider error: {exc}') from exc

    emailed = bool(settings.smtp_host and settings.smtp_username and settings.smtp_password)
    if emailed:
        background_tasks.add_task(send_email_summary, str(recipient_email), summary)

    return SummaryResponse(recipient=recipient_email, summary=summary, emailed=emailed)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={'detail': exc.detail})
