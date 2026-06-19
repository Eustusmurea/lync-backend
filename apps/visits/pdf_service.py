"""Generate patient visit PDF from HTML template."""

from io import BytesIO
from django.template.loader import render_to_string
from django.utils import timezone
from xhtml2pdf import pisa

from .serializers import VisitReportSerializer


def build_visit_report_context(visit) -> dict:
    """Serialize visit and enrich with display-friendly values."""
    data = VisitReportSerializer(visit).data
    gender_map = {'M': 'Male', 'F': 'Female', 'O': 'Other'}
    status_map = dict(visit.STATUS_CHOICES)

    data['patient_gender_display'] = gender_map.get(data.get('patient_gender', ''), '—')
    data['status_display'] = status_map.get(data.get('status', ''), data.get('status', ''))
    data['generated_at'] = timezone.localtime(timezone.now()).strftime('%d %b %Y, %H:%M')
    return data


def render_visit_pdf(visit) -> bytes:
    context = build_visit_report_context(visit)
    html = render_to_string('visits/patient_file_pdf.html', context)
    buffer = BytesIO()
    pdf = pisa.CreatePDF(html, dest=buffer, encoding='utf-8')
    if pdf.err:
        raise ValueError('PDF generation failed')
    return buffer.getvalue()
