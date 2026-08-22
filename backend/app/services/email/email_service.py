"""Email delivery service — sends pipeline results via Resend."""

import base64
import csv
import io
import json
import logging
from typing import Any

import resend

from app.config import settings
from app.models.domain.email import EmailDeliveryError, EmailRequest, EmailResult

logger = logging.getLogger("email")


def _rows_to_html_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p>No data extracted.</p>"

    headers = [k for k in rows[0].keys() if k not in {"flags", "document_id"}]

    html = (
        '<table style="border-collapse:collapse;width:100%;'
        'font-family:Arial,sans-serif;font-size:14px;">\n'
        '<thead><tr style="background-color:#0D9488;color:#fff;">\n'
    )
    for header in headers:
        label = header.replace("_", " ").title()
        html += (
            f'<th style="padding:10px 14px;text-align:left;'
            f'border:1px solid #ddd;">{label}</th>\n'
        )
    html += "</tr></thead>\n<tbody>\n"

    for index, row in enumerate(rows):
        bg = "#f0f0f0" if index % 2 == 0 else "#ffffff"
        html += f'<tr style="background-color:{bg};">\n'
        for header in headers:
            value = row.get(header, "")
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            html += (
                f'<td style="padding:8px 14px;border:1px solid #ddd;">{value}</td>\n'
            )
        html += "</tr>\n"

    html += "</tbody></table>"
    return html


def _rows_to_csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""

    skip = {"flags"}
    headers = [key for key in rows[0].keys() if key not in skip]

    flag_keys: list[str] = []
    for row in rows:
        for flag in row.get("flags", {}):
            if flag not in flag_keys:
                flag_keys.append(flag)
    all_headers = headers + flag_keys

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=all_headers, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        flat: dict[str, Any] = {}
        for key in headers:
            value = row.get(key)
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            flat[key] = value
        flat.update(row.get("flags", {}))
        writer.writerow(flat)

    return output.getvalue().encode("utf-8")


async def send_results_email(request: EmailRequest) -> EmailResult:
    if not settings.resend_api_key:
        raise EmailDeliveryError("RESEND_API_KEY is not configured. Add it to .env")

    resend.api_key = settings.resend_api_key

    html_table = _rows_to_html_table(request.rows)
    csv_bytes = _rows_to_csv_bytes(request.rows)

    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:800px;margin:0 auto;">
      <h2 style="color:#1C1917;">
        {request.pipeline_name or "Nexora"} — Results
      </h2>
      <p style="color:#78716C;">
        Processed <strong>{request.doc_count}</strong> document(s) —
        Extracted <strong>{len(request.rows)}</strong> row(s)
      </p>
      <hr style="border:none;border-top:1px solid #E7E5E4;margin:16px 0;">
      {html_table}
      <hr style="border:none;border-top:1px solid #E7E5E4;margin:16px 0;">
      <p style="color:#A8A29E;font-size:12px;">
        CSV file attached · Sent by Nexora
      </p>
    </div>
    """

    try:
        logger.info("Sending results email")
        response = resend.Emails.send(
            {
                "from": settings.resend_from_email,
                "to": [request.to_email],
                "subject": request.subject,
                "html": html_body,
                "attachments": [
                    {
                        "filename": "results.csv",
                        "content": base64.b64encode(csv_bytes).decode("utf-8"),
                        "content_type": "text/csv",
                    }
                ],
            }
        )
        email_id = response.get("id", "unknown")
        logger.info("Email sent — id=%s", email_id)
        return EmailResult(email_id=email_id, status="sent")
    except Exception as exc:
        logger.error("Email delivery failed: %s", str(exc))
        raise EmailDeliveryError(f"Failed to send email: {exc}") from exc
