import logging
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import DocumentTemplate, GeneratedDocument
from app.models.transaction import Transaction
from app.models.milestone import Milestone
from app.models.party import Party
from app.models.commission import TransactionCommission
from app.schemas.document import (
    DocumentTemplateResponse, GenerateDocumentRequest,
    GeneratedDocumentResponse, DocumentPreviewResponse,
)

logger = logging.getLogger(__name__)


async def list_templates(
    db: AsyncSession, agent_id: Optional[UUID] = None
) -> List[DocumentTemplateResponse]:
    stmt = select(DocumentTemplate)
    if agent_id:
        stmt = stmt.where(
            (DocumentTemplate.is_system == "system") |
            (DocumentTemplate.agent_id == agent_id)
        )
    result = await db.execute(stmt)
    templates = result.scalars().all()
    return [DocumentTemplateResponse.model_validate(t) for t in templates]


async def generate_document(
    transaction_id: UUID,
    request: GenerateDocumentRequest,
    db: AsyncSession,
    agent_id: Optional[UUID] = None,
) -> GeneratedDocumentResponse:
    """Generate a document (HTML) from transaction data."""
    transaction = await db.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Gather data
    data = await _gather_document_data(transaction_id, request.document_type, db)
    if request.custom_data:
        data.update(request.custom_data)

    # Get template
    template = None
    if request.template_id:
        template = await db.get(DocumentTemplate, request.template_id)
    else:
        # Use default system template for this type
        stmt = select(DocumentTemplate).where(
            DocumentTemplate.document_type == request.document_type,
            DocumentTemplate.is_system == "system",
        )
        result = await db.execute(stmt)
        template = result.scalar_one_or_none()

    # Render HTML
    html_content = _render_template(request.document_type, data, template)

    # Determine version
    version_stmt = select(GeneratedDocument).where(
        GeneratedDocument.transaction_id == transaction_id,
        GeneratedDocument.document_type == request.document_type,
    )
    version_result = await db.execute(version_stmt)
    existing = version_result.scalars().all()
    version = len(existing) + 1

    title = _document_title(request.document_type, transaction)

    doc = GeneratedDocument(
        transaction_id=transaction_id,
        template_id=request.template_id,
        document_type=request.document_type,
        title=title,
        html_content=html_content,
        generation_data=data,
        version=version,
        generated_by=agent_id,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return GeneratedDocumentResponse.model_validate(doc)


async def preview_document(
    transaction_id: UUID,
    request: GenerateDocumentRequest,
    db: AsyncSession,
) -> DocumentPreviewResponse:
    """Generate a preview without saving."""
    transaction = await db.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    data = await _gather_document_data(transaction_id, request.document_type, db)
    if request.custom_data:
        data.update(request.custom_data)

    template = None
    if request.template_id:
        template = await db.get(DocumentTemplate, request.template_id)

    html_content = _render_template(request.document_type, data, template)
    title = _document_title(request.document_type, transaction)

    return DocumentPreviewResponse(
        html_content=html_content,
        document_type=request.document_type,
        title=title,
    )


async def list_generated_documents(
    transaction_id: UUID, db: AsyncSession,
    document_type: Optional[str] = None,
) -> List[GeneratedDocumentResponse]:
    stmt = select(GeneratedDocument).where(
        GeneratedDocument.transaction_id == transaction_id
    )
    if document_type:
        stmt = stmt.where(GeneratedDocument.document_type == document_type)
    stmt = stmt.order_by(GeneratedDocument.created_at.desc())
    result = await db.execute(stmt)
    docs = result.scalars().all()
    return [GeneratedDocumentResponse.model_validate(d) for d in docs]


async def _gather_document_data(
    transaction_id: UUID, document_type: str, db: AsyncSession
) -> dict:
    """Gather all relevant transaction data for document generation."""
    transaction = await db.get(Transaction, transaction_id)

    ms_stmt = select(Milestone).where(Milestone.transaction_id == transaction_id).order_by(Milestone.sort_order)
    ms_result = await db.execute(ms_stmt)
    milestones = ms_result.scalars().all()

    p_stmt = select(Party).where(Party.transaction_id == transaction_id)
    p_result = await db.execute(p_stmt)
    parties = p_result.scalars().all()

    data = {
        "transaction": {
            "id": str(transaction.id),
            "property_address": transaction.property_address or "TBD",
            "property_city": transaction.property_city or "",
            "property_state": transaction.property_state or "",
            "property_zip": transaction.property_zip or "",
            "status": transaction.status,
            "closing_date": str(transaction.closing_date) if transaction.closing_date else "TBD",
            "purchase_price": transaction.purchase_price,
            "earnest_money_amount": transaction.earnest_money_amount,
            "representation_side": transaction.representation_side,
            "financing_type": transaction.financing_type or "N/A",
        },
        "milestones": [
            {
                "title": m.title,
                "status": m.status,
                "due_date": str(m.due_date) if m.due_date else "TBD",
                "responsible_party_role": m.responsible_party_role,
                "completed_at": str(m.completed_at) if m.completed_at else None,
            }
            for m in milestones
        ],
        "parties": [
            {"name": p.name, "role": p.role, "email": p.email, "phone": p.phone or "", "company": p.company or ""}
            for p in parties
        ],
    }

    # Add commission data if relevant
    if document_type in ("commission_summary", "net_sheet"):
        from sqlalchemy.orm import selectinload
        c_stmt = (
            select(TransactionCommission)
            .options(selectinload(TransactionCommission.splits))
            .where(TransactionCommission.transaction_id == transaction_id)
        )
        c_result = await db.execute(c_stmt)
        commission = c_result.scalar_one_or_none()
        if commission:
            data["commission"] = {
                "type": commission.commission_type,
                "rate": str(commission.rate) if commission.rate else None,
                "gross": str(commission.gross_commission) if commission.gross_commission else None,
                "projected_net": str(commission.projected_net) if commission.projected_net else None,
                "splits": [
                    {"type": s.split_type, "recipient": s.recipient_name, "amount": str(s.calculated_amount) if s.calculated_amount else "TBD"}
                    for s in commission.splits
                ],
            }

    return data


def _render_template(document_type: str, data: dict, template: Optional[DocumentTemplate] = None) -> str:
    """Render a document template with Jinja2."""
    from jinja2 import Environment, BaseLoader

    if template and template.template_content:
        template_str = template.template_content
    else:
        template_str = _get_default_template(document_type)

    env = Environment(loader=BaseLoader())
    tmpl = env.from_string(template_str)
    return tmpl.render(**data)


def _get_default_template(document_type: str) -> str:
    """Return a default HTML template for each document type."""
    templates = {
        "closing_checklist": """
<html><head><style>
body{font-family:Arial,sans-serif;margin:40px}
h1{color:#1a365d}table{width:100%;border-collapse:collapse;margin:20px 0}
th,td{border:1px solid #ddd;padding:8px;text-align:left}
th{background:#f0f4f8}.completed{color:green}.pending{color:orange}.overdue{color:red}
</style></head><body>
<h1>Closing Checklist</h1>
<p><strong>Property:</strong> {{ transaction.property_address }}</p>
<p><strong>Closing Date:</strong> {{ transaction.closing_date }}</p>
<table>
<tr><th>Item</th><th>Status</th><th>Due Date</th><th>Responsible</th></tr>
{% for m in milestones %}
<tr><td>{{ m.title }}</td><td class="{{ m.status }}">{{ m.status }}</td>
<td>{{ m.due_date }}</td><td>{{ m.responsible_party_role }}</td></tr>
{% endfor %}
</table>
<h2>Parties</h2>
<table><tr><th>Name</th><th>Role</th><th>Email</th><th>Phone</th></tr>
{% for p in parties %}
<tr><td>{{ p.name }}</td><td>{{ p.role }}</td><td>{{ p.email }}</td><td>{{ p.phone }}</td></tr>
{% endfor %}
</table>
</body></html>""",

        "timeline": """
<html><head><style>
body{font-family:Arial,sans-serif;margin:40px}
h1{color:#1a365d}.timeline{position:relative;padding:20px 0}
.event{padding:10px 20px;margin:10px 0;border-left:3px solid #3182ce;background:#f7fafc}
.event.completed{border-left-color:#38a169}.event.overdue{border-left-color:#e53e3e}
</style></head><body>
<h1>Transaction Timeline</h1>
<p><strong>Property:</strong> {{ transaction.property_address }}</p>
<div class="timeline">
{% for m in milestones %}
<div class="event {{ m.status }}">
<strong>{{ m.title }}</strong><br/>
Due: {{ m.due_date }} | Status: {{ m.status }}
{% if m.completed_at %}<br/>Completed: {{ m.completed_at }}{% endif %}
</div>
{% endfor %}
</div>
</body></html>""",

        "net_sheet": """
<html><head><style>
body{font-family:Arial,sans-serif;margin:40px}
h1{color:#1a365d}table{width:100%;border-collapse:collapse;margin:20px 0}
th,td{border:1px solid #ddd;padding:8px}th{background:#f0f4f8}
.total{font-weight:bold;background:#e2e8f0}
</style></head><body>
<h1>Net Sheet</h1>
<p><strong>Property:</strong> {{ transaction.property_address }}</p>
<p><strong>Purchase Price:</strong> {{ transaction.purchase_price }}</p>
{% if commission %}
<table>
<tr><th>Description</th><th>Amount</th></tr>
<tr><td>Gross Commission ({{ commission.type }}{% if commission.rate %} @ {{ commission.rate }}{% endif %})</td><td>{{ commission.gross or 'TBD' }}</td></tr>
{% for s in commission.splits %}
<tr><td>{{ s.type }}: {{ s.recipient }}</td><td>-{{ s.amount }}</td></tr>
{% endfor %}
<tr class="total"><td>Projected Net</td><td>{{ commission.projected_net or 'TBD' }}</td></tr>
</table>
{% endif %}
</body></html>""",

        "commission_summary": """
<html><head><style>
body{font-family:Arial,sans-serif;margin:40px}
h1{color:#1a365d}table{width:100%;border-collapse:collapse;margin:20px 0}
th,td{border:1px solid #ddd;padding:8px}th{background:#f0f4f8}
</style></head><body>
<h1>Commission Summary</h1>
<p><strong>Property:</strong> {{ transaction.property_address }}</p>
{% if commission %}
<p><strong>Commission Type:</strong> {{ commission.type }}</p>
<p><strong>Gross Commission:</strong> {{ commission.gross or 'TBD' }}</p>
<h2>Splits</h2>
<table><tr><th>Type</th><th>Recipient</th><th>Amount</th></tr>
{% for s in commission.splits %}
<tr><td>{{ s.type }}</td><td>{{ s.recipient }}</td><td>{{ s.amount }}</td></tr>
{% endfor %}
</table>
<p><strong>Projected Net:</strong> {{ commission.projected_net or 'TBD' }}</p>
{% endif %}
</body></html>""",

        "cover_letter": """
<html><head><style>
body{font-family:Arial,sans-serif;margin:40px;line-height:1.6}
h1{color:#1a365d}
</style></head><body>
<h1>Cover Letter</h1>
<p>RE: {{ transaction.property_address }}, {{ transaction.property_city }}, {{ transaction.property_state }} {{ transaction.property_zip }}</p>
<p>Dear Parties,</p>
<p>Please find enclosed the transaction details for the above-referenced property.</p>
<p><strong>Purchase Price:</strong> {{ transaction.purchase_price }}</p>
<p><strong>Closing Date:</strong> {{ transaction.closing_date }}</p>
<p><strong>Financing:</strong> {{ transaction.financing_type }}</p>
<h2>Parties Involved</h2>
<ul>
{% for p in parties %}
<li>{{ p.role }}: {{ p.name }} ({{ p.email }})</li>
{% endfor %}
</ul>
<p>Please do not hesitate to reach out with any questions.</p>
</body></html>""",
    }
    return templates.get(document_type, "<html><body><p>Template not found for type: {{ document_type }}</p></body></html>")


def _document_title(document_type: str, transaction) -> str:
    addr = transaction.property_address or "Unknown Property"
    type_labels = {
        "closing_checklist": "Closing Checklist",
        "net_sheet": "Net Sheet",
        "timeline": "Transaction Timeline",
        "commission_summary": "Commission Summary",
        "cover_letter": "Cover Letter",
    }
    label = type_labels.get(document_type, document_type.replace("_", " ").title())
    return f"{label} - {addr}"
