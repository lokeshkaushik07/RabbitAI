from __future__ import annotations

import io
import smtplib
from email.message import EmailMessage

import httpx
import pandas as pd

from .config import settings

REQUIRED_COLUMNS = {'Date', 'Product_Category', 'Region', 'Units_Sold', 'Unit_Price', 'Revenue', 'Status'}
ALLOWED_SUFFIXES = ('.csv', '.xlsx')


def parse_sales_file(contents: bytes, filename: str) -> pd.DataFrame:
    stream = io.BytesIO(contents)
    lower = filename.lower()

    if not lower.endswith(ALLOWED_SUFFIXES):
        raise ValueError('Only .csv and .xlsx files are supported.')

    if lower.endswith('.csv'):
        df = pd.read_csv(stream)
    else:
        df = pd.read_excel(stream)

    if df.empty:
        raise ValueError('Uploaded file contains no data.')

    if len(df) > settings.max_rows:
        raise ValueError(f'Uploaded file has too many rows. Limit is {settings.max_rows}.')

    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(f'Missing required columns: {", ".join(sorted(missing))}')

    return df


def build_data_snapshot(df: pd.DataFrame) -> str:
    normalized = df.copy()
    normalized['Revenue'] = pd.to_numeric(normalized['Revenue'], errors='coerce').fillna(0)
    normalized['Units_Sold'] = pd.to_numeric(normalized['Units_Sold'], errors='coerce').fillna(0)

    revenue = normalized['Revenue'].sum()
    units = normalized['Units_Sold'].sum()
    top_regions = normalized.groupby('Region')['Revenue'].sum().sort_values(ascending=False).head(3).to_dict()
    top_categories = normalized.groupby('Product_Category')['Revenue'].sum().sort_values(ascending=False).to_dict()
    status_split = normalized['Status'].value_counts(dropna=False).to_dict()

    cancelled = status_split.get('Cancelled', 0)
    cancel_rate = (cancelled / len(normalized)) * 100

    return (
        f"Rows: {len(normalized)}\n"
        f"Total Revenue: {revenue:.2f}\n"
        f"Total Units Sold: {units:.0f}\n"
        f"Top Regions by Revenue: {top_regions}\n"
        f"Top Categories by Revenue: {top_categories}\n"
        f"Status Breakdown: {status_split}\n"
        f"Cancellation Rate: {cancel_rate:.2f}%"
    )


async def generate_summary(snapshot: str) -> str:
    prompt = (
        'You are a sales strategy analyst. Write a concise executive summary with key trends, risks, and action items '
        'based on this quarterly sales data snapshot:\n\n'
        f'{snapshot[:5000]}\n\n'
        'Format with headings: Overview, Key Trends, Risks, Recommended Actions. '
        'Return clean text only (no markdown bullets beyond section prose).'
    )

    if not settings.groq_api_key:
        return (
            'Overview\n'
            'A complete automated summary could not call the configured LLM provider, so this is a fallback summary.\n\n'
            'Key Trends\n'
            f'{snapshot}\n\n'
            'Risks\n'
            'Potential data quality issues or missing provider credentials can reduce insight depth.\n\n'
            'Recommended Actions\n'
            'Configure GROQ_API_KEY and rerun for richer narrative analysis.'
        )

    headers = {'Authorization': f'Bearer {settings.groq_api_key}', 'Content-Type': 'application/json'}
    payload = {
        'model': settings.groq_model,
        'messages': [
            {'role': 'system', 'content': 'You are an executive sales analyst.'},
            {'role': 'user', 'content': prompt},
        ],
        'temperature': 0.2,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post('https://api.groq.com/openai/v1/chat/completions', headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    return data['choices'][0]['message']['content'].strip()


def send_email_summary(to_email: str, summary: str) -> None:
    if not all([settings.smtp_host, settings.smtp_username, settings.smtp_password]):
        return

    message = EmailMessage()
    message['Subject'] = 'Automated Quarterly Sales Insight'
    message['From'] = settings.smtp_from_email
    message['To'] = to_email
    message.set_content(summary)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
        if settings.smtp_use_tls:
            server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)
