from fastapi import APIRouter, HTTPException
from app.models import (
    GenerateRequest, GenerateResponse,
    SendEmailDirectRequest, SendEmailDirectResponse,
    SendInviteRequest, SendInviteResponse,
    SendRuleSheetRequest, SendRuleSheetResponse,
    SendFnBSummaryRequest, SendFnBSummaryResponse,
)
from app.services.document_generator import (
    generate_schedule, generate_brochure,
    generate_invite_email, generate_brochure_html, generate_invite_html,
    generate_rule_sheet, generate_fnb_summary, wrap_plain_text_html,
)
from app.services.email_service import send_email_direct

router = APIRouter()


@router.post("/generate", response_model=GenerateResponse)
async def generate_endpoint(payload: GenerateRequest) -> GenerateResponse:
    schedule    = generate_schedule(payload.tournament)
    brochure    = generate_brochure(payload.tournament)
    rule_sheet  = generate_rule_sheet(payload.tournament)
    fnb_summary = generate_fnb_summary(payload.tournament)
    return GenerateResponse(
        schedule=schedule,
        brochure=brochure,
        rule_sheet=rule_sheet,
        fnb_summary=fnb_summary,
    )


@router.post("/email/send", response_model=SendEmailDirectResponse)
async def send_email_endpoint(payload: SendEmailDirectRequest) -> SendEmailDirectResponse:
    """
    Send an email to a list of recipients.
    When schedule data is provided, the backend generates a fully styled
    HTML email with the tee-time table rendered inline.
    """
    try:
        html_body = None
        if payload.schedule:
            html_body = generate_brochure_html(
                brochure_body=payload.body,
                schedule=payload.schedule,
                tournament_name=payload.tournament_name or "",
                tournament_date=payload.tournament_date or "",
                tournament_venue=payload.tournament_venue or "",
                tournament_format=payload.tournament_format or "",
            )
        await send_email_direct(
            to_emails=payload.recipients,
            subject=payload.subject,
            body=payload.body,
            html_body=html_body,
        )
        count = len(payload.recipients)
        return SendEmailDirectResponse(
            success=True,
            message=f"Email sent to {count} recipient{'s' if count != 1 else ''}.",
        )
    except Exception as exc:
        return SendEmailDirectResponse(success=False, message=str(exc))


@router.post("/email/send-invite", response_model=SendInviteResponse)
async def send_invite_endpoint(payload: SendInviteRequest) -> SendInviteResponse:
    """
    Compose and send a player invitation email with a Register Now button.
    """
    try:
        invite = generate_invite_email(
            tournament_meta=payload.tournament_meta,
            registration_link=payload.registration_link or "",
        )
        html_body = generate_invite_html(
            tournament_meta=payload.tournament_meta,
            registration_link=payload.registration_link or "",
        )
        await send_email_direct(
            to_emails=payload.recipients,
            subject=invite["subject"],
            body=invite["body"],
            html_body=html_body,
        )
        count = len(payload.recipients)
        return SendInviteResponse(
            success=True,
            message=f"Invite sent to {count} recipient{'s' if count != 1 else ''}.",
        )
    except Exception as exc:
        return SendInviteResponse(success=False, message=str(exc))


@router.post("/email/send-rule-sheet", response_model=SendRuleSheetResponse)
async def send_rule_sheet_endpoint(payload: SendRuleSheetRequest) -> SendRuleSheetResponse:
    """
    Generate and email the Player Information Guide / Rule Sheet.
    """
    try:
        # Honor an organizer-edited guide when supplied; otherwise regenerate.
        if payload.body and payload.body.strip():
            subject = payload.subject or "Player Information Guide"
            body = payload.body
            html_body = wrap_plain_text_html(subject, body)
        else:
            doc = generate_rule_sheet(payload.tournament_meta)
            subject, body, html_body = doc["subject"], doc["body"], doc["html"]
        await send_email_direct(
            to_emails=payload.recipients,
            subject=subject,
            body=body,
            html_body=html_body,
        )
        count = len(payload.recipients)
        return SendRuleSheetResponse(
            success=True,
            message=f"Player guide sent to {count} recipient{'s' if count != 1 else ''}.",
        )
    except Exception as exc:
        return SendRuleSheetResponse(success=False, message=str(exc))


@router.post("/email/send-fnb-summary", response_model=SendFnBSummaryResponse)
async def send_fnb_summary_endpoint(payload: SendFnBSummaryRequest) -> SendFnBSummaryResponse:
    """
    Generate and email the Food & Beverage Summary / Banquet Order Sheet.
    Returns 400 when catering is not enabled for the tournament.
    """
    if not payload.tournament_meta.get("cateringEnabled"):
        raise HTTPException(
            status_code=400,
            detail="Catering is not enabled for this tournament.",
        )
    try:
        # Honor an organizer-edited summary when one is supplied; otherwise
        # regenerate the default summary from the tournament data.
        if payload.body and payload.body.strip():
            subject = payload.subject or "Food & Beverage Summary"
            body = payload.body
            html_body = wrap_plain_text_html(subject, body)
        else:
            doc = generate_fnb_summary(payload.tournament_meta)
            if doc is None:
                raise HTTPException(status_code=400, detail="Catering is not enabled for this tournament.")
            subject, body, html_body = doc["subject"], doc["body"], doc["html"]
        await send_email_direct(
            to_emails=payload.recipients,
            subject=subject,
            body=body,
            html_body=html_body,
        )
        count = len(payload.recipients)
        return SendFnBSummaryResponse(
            success=True,
            message=f"F&B summary sent to {count} recipient{'s' if count != 1 else ''}.",
        )
    except HTTPException:
        raise
    except Exception as exc:
        return SendFnBSummaryResponse(success=False, message=str(exc))

