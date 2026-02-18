import logging
import os
import tempfile
from uuid import UUID
from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.models.file import File as FileModel
from app.models.transaction import Transaction
from app.models.party import Party
from app.models.inspection import InspectionAnalysis, InspectionItem
from app.schemas.file import FileResponse
from app.services.storage_service import upload_file, get_file_url
from app.agents.contract_parser import parse_contract
from app.agents.inspection_parser import parse_inspection_report
from app.agents.addendum_parser import parse_addendum
from app.services.template_service import apply_template, list_templates
from app.schemas.milestone_template import ApplyTemplateRequest
from app.services.health_score_service import compute_health_score

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/transactions/{transaction_id}/files", response_model=List[FileResponse])
async def list_files(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    stmt = select(FileModel).where(FileModel.transaction_id == transaction_id)
    result = await db.execute(stmt)
    files = result.scalars().all()
    return [FileResponse.model_validate(f) for f in files]


@router.post("/transactions/{transaction_id}/files", response_model=FileResponse)
async def upload_transaction_file(
    transaction_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_session),
):
    file_id = await upload_file(file, db)
    file_record = await db.get(FileModel, file_id)
    if file_record:
        file_record.transaction_id = transaction_id
        await db.commit()
        await db.refresh(file_record)
    return FileResponse.model_validate(file_record)


@router.post("/transactions/{transaction_id}/files/upload-contract")
async def upload_and_parse_contract(
    transaction_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Upload a contract PDF, parse it via Claude AI, and update the existing
    transaction with extracted data including parties and milestone templates.
    """
    transaction = await db.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Upload the file to storage and link it
    file_id = await upload_file(file, db)
    file_record = await db.get(FileModel, file_id)
    if file_record:
        file_record.transaction_id = transaction_id
        await db.commit()
        await db.refresh(file_record)

    # Write to temp file for PDF parsing
    await file.seek(0)
    contents = await file.read()
    suffix = "." + (file.filename.split(".")[-1] if file.filename else "pdf")
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        parsed_data = await parse_contract(tmp_path)
    finally:
        os.unlink(tmp_path)

    # === Update transaction with parsed fields ===
    prop = parsed_data.get("property_details", {})
    fin = parsed_data.get("financial_terms", {})
    dates = parsed_data.get("dates", {})
    additional = parsed_data.get("additional_provisions", {})

    # Property details
    if prop.get("address"):
        transaction.property_address = prop["address"]
    if prop.get("city"):
        transaction.property_city = prop["city"]
    if prop.get("state"):
        transaction.property_state = prop["state"]
    if prop.get("zip_code"):
        transaction.property_zip = prop["zip_code"]
    if prop.get("county"):
        transaction.property_county = prop["county"]

    # Financial terms
    if fin.get("purchase_price"):
        transaction.purchase_price = {"amount": fin["purchase_price"], "currency": "USD"}
    if fin.get("financing_type"):
        transaction.financing_type = fin["financing_type"]
    if fin.get("earnest_money"):
        transaction.earnest_money_amount = {"amount": fin["earnest_money"], "currency": "USD"}

    # Representation side (from agency section of contract)
    rep_side = parsed_data.get("representation_side")
    if rep_side and rep_side in ("buyer", "seller"):
        transaction.representation_side = rep_side

    # Special stipulations — merge financial extras + provisions
    stipulations = {}
    if fin.get("seller_concessions"):
        stipulations["seller_concessions"] = fin["seller_concessions"]
    if fin.get("original_list_price"):
        stipulations["original_list_price"] = fin["original_list_price"]
    if fin.get("earnest_money_holder"):
        stipulations["earnest_money_holder"] = fin["earnest_money_holder"]
    if fin.get("home_warranty_amount"):
        stipulations["home_warranty"] = True
        stipulations["home_warranty_amount"] = fin["home_warranty_amount"]
        stipulations["home_warranty_paid_by"] = fin.get("home_warranty_paid_by")
    if additional.get("provisions"):
        stipulations["additional_provisions"] = additional["provisions"]
    if additional.get("contingencies"):
        stipulations["contingencies"] = additional["contingencies"]
    if additional.get("home_warranty"):
        stipulations["home_warranty"] = True
    if additional.get("wood_infestation_report"):
        stipulations["wood_infestation_report"] = True
    if additional.get("fha_va_agreement"):
        stipulations["fha_va_agreement"] = True
    if additional.get("lead_based_paint"):
        stipulations["lead_based_paint"] = True
    if additional.get("property_sale_contingency"):
        stipulations["property_sale_contingency"] = True
    # Contract type
    contract_type = parsed_data.get("contract_type")
    if contract_type:
        stipulations["contract_type"] = contract_type
    if stipulations:
        transaction.special_stipulations = stipulations

    # Dates
    if isinstance(dates, dict):
        closing_date_str = dates.get("closing_date")
        if closing_date_str:
            try:
                parsed_closing = datetime.fromisoformat(closing_date_str)
                if parsed_closing.tzinfo is None:
                    parsed_closing = parsed_closing.replace(tzinfo=timezone.utc)
                transaction.closing_date = parsed_closing
            except (ValueError, TypeError):
                logger.warning("Could not parse closing date: %s", closing_date_str)

        contract_date_str = dates.get("contract_date")
        if contract_date_str:
            try:
                parsed_contract = datetime.fromisoformat(contract_date_str)
                if parsed_contract.tzinfo is None:
                    parsed_contract = parsed_contract.replace(tzinfo=timezone.utc)
                transaction.contract_execution_date = parsed_contract
            except (ValueError, TypeError):
                logger.warning("Could not parse contract date: %s", contract_date_str)

    if file_record:
        transaction.contract_document_url = file_record.url
    transaction.ai_extraction_confidence = parsed_data.get("confidence_scores")

    await db.commit()
    await db.refresh(transaction)

    # === Auto-create parties from parsed data ===
    parties_created = []
    for party_data in parsed_data.get("parties", []):
        # Handle both old format (contact_info dict) and new format (flat fields)
        if "contact_info" in party_data:
            contact = party_data["contact_info"]
            email = contact.get("email")
            phone = contact.get("phone")
            company = contact.get("company")
        else:
            email = party_data.get("email")
            phone = party_data.get("phone")
            company = party_data.get("company")

        role = party_data.get("role", "unknown")
        name = party_data.get("name", "Unknown")

        # Skip empty / placeholder names
        if not name or name.strip() in ("", "Unknown", "N/A"):
            continue

        new_party = Party(
            name=name,
            role=role,
            email=email,
            phone=phone,
            company=company,
            transaction_id=transaction_id,
            is_primary=(role in ("buyer", "seller")),
        )

        # Store license_number in notes if present
        license_num = party_data.get("license_number")
        if license_num:
            new_party.notes = {"license_number": license_num}

        db.add(new_party)
        parties_created.append({"name": new_party.name, "role": new_party.role, "email": new_party.email})
    await db.commit()

    # === Auto-apply milestone template based on state + financing ===
    template_applied = None
    if transaction.property_state:
        templates = await list_templates(
            db,
            state_code=transaction.property_state,
            financing_type=transaction.financing_type,
        )
        # Also filter by representation_side if we have it
        if transaction.representation_side and templates:
            side_match = [t for t in templates if t.representation_side == transaction.representation_side]
            if side_match:
                templates = side_match

        if templates:
            selected = templates[0]
            for t in templates:
                if t.is_default:
                    selected = t
                    break
            apply_request = ApplyTemplateRequest(
                template_id=selected.id,
                contract_execution_date=transaction.contract_execution_date or datetime.now(timezone.utc),
                closing_date=transaction.closing_date,
            )
            template_result = await apply_template(transaction_id, apply_request, db)
            template_applied = {
                "template_id": str(selected.id),
                "template_name": selected.name,
                "milestones_created": template_result.milestones_created,
                "milestones_skipped": template_result.milestones_skipped,
            }

    # === Auto-create commission (3% rate, 20/80 broker/agent split) ===
    commission_created = None
    if transaction.purchase_price:
        try:
            from decimal import Decimal
            from app.models.commission import CommissionConfig, TransactionCommission, CommissionSplit

            # Check if commission already exists
            from sqlalchemy import select as sel
            existing = (await db.execute(
                sel(TransactionCommission).where(TransactionCommission.transaction_id == transaction_id)
            )).scalar_one_or_none()

            if not existing:
                # Load agent's config, or use defaults
                config = (await db.execute(
                    sel(CommissionConfig).where(CommissionConfig.agent_id == transaction.agent_id)
                )).scalar_one_or_none()

                rate = Decimal(str(config.default_rate)) if config and config.default_rate else Decimal("0.0300")
                broker_pct = Decimal(str(config.broker_split_percentage)) if config and config.broker_split_percentage else Decimal("0.2000")

                price_val = transaction.purchase_price.get("amount") if isinstance(transaction.purchase_price, dict) else None
                if price_val:
                    purchase = Decimal(str(price_val))
                    gross = purchase * rate
                    broker_amount = gross * broker_pct
                    agent_net = gross - broker_amount

                    comm = TransactionCommission(
                        transaction_id=transaction_id,
                        agent_id=transaction.agent_id,
                        commission_type="percentage",
                        rate=rate,
                        gross_commission=gross,
                        projected_net=agent_net,
                        status="projected",
                    )
                    db.add(comm)
                    await db.flush()

                    split = CommissionSplit(
                        transaction_commission_id=comm.id,
                        split_type="broker",
                        recipient_name="Brokerage",
                        is_percentage=True,
                        percentage=broker_pct,
                        calculated_amount=broker_amount,
                    )
                    db.add(split)
                    await db.commit()

                    commission_created = {
                        "gross_commission": float(gross),
                        "broker_split": float(broker_amount),
                        "agent_net": float(agent_net),
                        "rate": float(rate),
                    }
        except Exception as e:
            logger.warning("Failed to auto-create commission for transaction %s: %s", transaction_id, e)

    # Compute health score
    health_result = await compute_health_score(transaction_id, db)

    return {
        "status": "success",
        "transaction_id": str(transaction_id),
        "file_id": str(file_id),
        "parsed_data": parsed_data,
        "parties_created": parties_created,
        "template_applied": template_applied,
        "commission_created": commission_created,
        "health_score": health_result.score,
        "confidence_scores": parsed_data.get("confidence_scores", {}),
        "detected_features": parsed_data.get("detected_features", []),
    }


@router.post("/transactions/{transaction_id}/files/upload-inspection")
async def upload_and_parse_inspection(
    transaction_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Upload a home inspection report PDF, parse it via Claude AI, and create
    an InspectionAnalysis with individual InspectionItems.
    """
    transaction = await db.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Upload the file to storage and link it
    file_id = await upload_file(file, db)
    file_record = await db.get(FileModel, file_id)
    if file_record:
        file_record.transaction_id = transaction_id
        await db.commit()
        await db.refresh(file_record)

    # Write to temp file for parsing
    await file.seek(0)
    contents = await file.read()
    suffix = "." + (file.filename.split(".")[-1] if file.filename else "pdf")
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        parsed_data = await parse_inspection_report(tmp_path)
    except Exception as e:
        logger.error("Inspection parsing failed for transaction %s: %s", transaction_id, e)
        raise HTTPException(status_code=500, detail=f"Inspection parsing failed: {str(e)}")
    finally:
        os.unlink(tmp_path)

    # Create InspectionAnalysis record
    analysis = InspectionAnalysis(
        transaction_id=transaction_id,
        report_document_url=file_record.url if file_record else "",
        executive_summary=parsed_data.get("executive_summary", ""),
        total_estimated_cost_low={"amount": parsed_data.get("total_estimated_cost_low", 0), "currency": "USD"},
        total_estimated_cost_high={"amount": parsed_data.get("total_estimated_cost_high", 0), "currency": "USD"},
        overall_risk_level=parsed_data.get("overall_risk_level", "medium"),
    )
    db.add(analysis)
    await db.flush()  # Get the analysis ID

    # Create InspectionItem records
    severity_order = {"critical": 0, "major": 1, "moderate": 2, "minor": 3}
    items_created = 0
    for i, item_data in enumerate(parsed_data.get("items", [])):
        severity = item_data.get("severity", "minor")
        cost_low = item_data.get("estimated_cost_low", 0)
        cost_high = item_data.get("estimated_cost_high", 0)

        inspection_item = InspectionItem(
            analysis_id=analysis.id,
            description=item_data.get("description", ""),
            location=item_data.get("location", ""),
            severity=severity,
            estimated_cost_low={"amount": cost_low, "currency": "USD"},
            estimated_cost_high={"amount": cost_high, "currency": "USD"},
            risk_assessment=item_data.get("risk_assessment", ""),
            recommendation=item_data.get("recommendation", ""),
            repair_status="pending",
            sort_order=severity_order.get(severity, 99) * 100 + i,
            report_reference=item_data.get("report_reference"),
        )
        db.add(inspection_item)
        items_created += 1

    await db.commit()

    return {
        "status": "success",
        "transaction_id": str(transaction_id),
        "file_id": str(file_id),
        "analysis_id": str(analysis.id),
        "items_created": items_created,
        "overall_risk_level": analysis.overall_risk_level,
        "executive_summary": analysis.executive_summary,
        "total_estimated_cost_low": parsed_data.get("total_estimated_cost_low", 0),
        "total_estimated_cost_high": parsed_data.get("total_estimated_cost_high", 0),
        "confidence": parsed_data.get("confidence", 0),
    }


@router.post("/transactions/{transaction_id}/files/upload-addendum")
async def upload_and_parse_addendum(
    transaction_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Upload a contract addendum/amendment PDF (e.g., repair request),
    parse it via Claude AI, and update inspection items' repair status.
    """
    transaction = await db.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Upload the file to storage and link it
    file_id = await upload_file(file, db)
    file_record = await db.get(FileModel, file_id)
    if file_record:
        file_record.transaction_id = transaction_id
        await db.commit()
        await db.refresh(file_record)

    # Write to temp file for parsing
    await file.seek(0)
    contents = await file.read()
    suffix = "." + (file.filename.split(".")[-1] if file.filename else "pdf")
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        parsed_data = await parse_addendum(tmp_path)
    except Exception as e:
        logger.error("Addendum parsing failed for transaction %s: %s", transaction_id, e)
        raise HTTPException(status_code=500, detail=f"Addendum parsing failed: {str(e)}")
    finally:
        os.unlink(tmp_path)

    addendum_type = parsed_data.get("addendum_type", "unknown")
    items_parsed = parsed_data.get("items", [])

    # For repair requests, try to match addendum items to existing inspection items
    # and update their repair_status to "in_progress"
    items_matched = 0
    if addendum_type == "repair_request":
        # Load existing inspection items for this transaction
        from sqlalchemy.orm import selectinload
        stmt = (
            select(InspectionAnalysis)
            .where(InspectionAnalysis.transaction_id == transaction_id)
            .options(selectinload(InspectionAnalysis.items))
        )
        result = await db.execute(stmt)
        analyses = result.scalars().all()

        all_inspection_items = []
        for a in analyses:
            all_inspection_items.extend(a.items)

        # Try to match each addendum repair item to an inspection item by report_reference
        for addendum_item in items_parsed:
            ref = addendum_item.get("inspection_reference", "")
            if ref and all_inspection_items:
                # Normalize reference for matching (e.g., "Page 6, Item 3" -> "page 6" + "item 3")
                ref_lower = ref.lower()
                for insp_item in all_inspection_items:
                    if insp_item.report_reference and insp_item.report_reference.lower() in ref_lower:
                        insp_item.repair_status = "in_progress"
                        items_matched += 1
                        break

        await db.commit()

    # Store addendum data as an amendment record
    from app.models.amendment import Amendment
    amendment = Amendment(
        transaction_id=transaction_id,
        field_changed=f"addendum_{addendum_type}",
        old_value={"document_url": file_record.url if file_record else ""},
        new_value={"addendum_type": addendum_type, "items": items_parsed, "signed_date": parsed_data.get("signed_date")},
        reason=f"{addendum_type.replace('_', ' ').title()}: {len(items_parsed)} items",
        changed_by_id=transaction.agent_id,
        notification_sent=False,
    )
    db.add(amendment)
    await db.commit()

    return {
        "status": "success",
        "transaction_id": str(transaction_id),
        "file_id": str(file_id),
        "addendum_type": addendum_type,
        "items_parsed": len(items_parsed),
        "items_matched_to_inspection": items_matched,
        "parsed_data": parsed_data,
    }
