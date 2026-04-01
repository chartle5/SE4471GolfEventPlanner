from fastapi import APIRouter
from app.models import GenerateRequest, GenerateResponse, SendEmailDirectRequest, SendEmailDirectResponse
from app.services.document_generator import generate_schedule, generate_brochure
from app.services.email_service import send_email_direct

router = APIRouter()


@router.post("/generate", response_model=GenerateResponse)
async def generate_endpoint(payload: GenerateRequest) -> GenerateResponse:
    schedule = generate_schedule(payload.tournament)
    brochure = generate_brochure(payload.tournament)
    return GenerateResponse(schedule=schedule, brochure=brochure)


@router.post("/email/send", response_model=SendEmailDirectResponse)
async def send_email_endpoint(payload: SendEmailDirectRequest) -> SendEmailDirectResponse:
    """Send a brochure email to an arbitrary list of recipients."""
    try:
        await send_email_direct(
            to_emails=payload.recipients,
            subject=payload.subject,
            body=payload.body,
        )
        count = len(payload.recipients)
        return SendEmailDirectResponse(
            success=True,
            message=f"Email sent to {count} recipient{'s' if count != 1 else ''}.",
        )
    except Exception as exc:
        return SendEmailDirectResponse(success=False, message=str(exc))
