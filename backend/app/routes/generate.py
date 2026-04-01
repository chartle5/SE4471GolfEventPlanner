from fastapi import APIRouter
from app.models import GenerateRequest, GenerateResponse, SendEmailDirectRequest, SendEmailDirectResponse, SendInviteRequest, SendInviteResponse
from app.services.document_generator import generate_schedule, generate_brochure, generate_invite_email, generate_brochure_html, generate_invite_html
from app.services.email_service import send_email_direct

router = APIRouter()


@router.post("/generate", response_model=GenerateResponse)
async def generate_endpoint(payload: GenerateRequest) -> GenerateResponse:
    schedule = generate_schedule(payload.tournament)
    brochure = generate_brochure(payload.tournament)
    return GenerateResponse(schedule=schedule, brochure=brochure)


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

