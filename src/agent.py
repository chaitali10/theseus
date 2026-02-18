import logging
from dataclasses import dataclass, field
from enum import Enum

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    function_tool,
    inference,
    room_io,
)
from livekit.plugins import noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")

load_dotenv(".env.local")


class VerificationStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VERIFIED = "verified"
    DENIED = "denied"
    ERROR = "error"


@dataclass
class PatientInfo:
    patient_name: str = ""
    date_of_birth: str = ""
    member_id: str = ""
    insurance_provider: str = ""
    group_number: str = ""
    plan_type: str = ""


@dataclass
class VerificationResult:
    status: VerificationStatus = VerificationStatus.PENDING
    eligible: bool = False
    copay: str = ""
    deductible: str = ""
    deductible_met: str = ""
    coinsurance: str = ""
    out_of_pocket_max: str = ""
    coverage_details: str = ""
    effective_date: str = ""
    termination_date: str = ""
    notes: str = ""


@dataclass
class VerificationSession:
    patient: PatientInfo = field(default_factory=PatientInfo)
    result: VerificationResult = field(default_factory=VerificationResult)


class InsuranceVerificationAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a voice AI agent that assists clinic front-desk staff "
                "with insurance verification. The user is interacting with you via "
                "voice, even if you perceive the conversation as text.\n\n"
                "Your workflow:\n"
                "1. Greet the user and ask for the patient information needed for "
                "insurance verification: patient name, date of birth, insurance "
                "provider, member ID, and group number.\n"
                "2. Once you have the required patient details, use the "
                "verify_insurance tool to check the patient's insurance coverage.\n"
                "3. After verification completes, clearly communicate the results "
                "to the user including eligibility status, copay, deductible, and "
                "coverage details.\n\n"
                "Important guidelines:\n"
                "- Confirm each piece of information before proceeding.\n"
                "- If the user has already provided patient info (via the system), "
                "acknowledge it and proceed with verification.\n"
                "- Be concise, professional, and clear in your responses.\n"
                "- Do not use complex formatting, emojis, or special symbols.\n"
                "- If verification fails, explain the issue and suggest next steps."
            ),
        )

    @function_tool
    async def verify_insurance(
        self,
        context: RunContext[VerificationSession],
        patient_name: str,
        date_of_birth: str,
        insurance_provider: str,
        member_id: str,
        group_number: str,
    ) -> str:
        """Verify a patient's insurance coverage by contacting the insurance carrier.

        Use this tool when the user has provided all the required patient
        information and you are ready to verify their insurance coverage.

        Args:
            patient_name: Full name of the patient
            date_of_birth: Patient's date of birth (MM/DD/YYYY)
            insurance_provider: Name of the insurance company
            member_id: Patient's insurance member ID
            group_number: Patient's insurance group number
        """
        session_data = context.userdata
        session_data.patient = PatientInfo(
            patient_name=patient_name,
            date_of_birth=date_of_birth,
            insurance_provider=insurance_provider,
            member_id=member_id,
            group_number=group_number,
        )
        session_data.result.status = VerificationStatus.IN_PROGRESS

        logger.info(
            "Verifying insurance for patient %s with %s (member: %s)",
            patient_name,
            insurance_provider,
            member_id,
        )

        # Update participant attributes so the frontend can show progress
        await _publish_verification_update(context.session, session_data)

        # In production, this would make an actual API call to the insurance
        # carrier. For now, we return a simulated successful verification.
        session_data.result = VerificationResult(
            status=VerificationStatus.VERIFIED,
            eligible=True,
            copay="$30",
            deductible="$500",
            deductible_met="$350 of $500",
            coinsurance="80/20",
            out_of_pocket_max="$3,000",
            coverage_details="In-network coverage active",
            effective_date="01/01/2025",
            termination_date="12/31/2025",
            notes="Pre-authorization required for specialist visits",
        )

        await _publish_verification_update(context.session, session_data)

        return (
            f"Insurance verification complete for {patient_name}. "
            f"Status: Eligible. "
            f"Copay: $30. "
            f"Deductible: $500 ($350 met so far). "
            f"Coinsurance: 80/20 in-network. "
            f"Out-of-pocket max: $3,000. "
            f"Note: Pre-authorization required for specialist visits."
        )


async def _publish_verification_update(
    session: AgentSession,
    data: VerificationSession,
) -> None:
    """Publish verification status and results as participant attributes.

    The frontend can listen for attribute changes to update the UI in real time.
    """
    room = session.room
    if room is None or room.local_participant is None:
        return

    attributes = {
        "verification.status": data.result.status.value,
        "verification.patient_name": data.patient.patient_name,
        "verification.date_of_birth": data.patient.date_of_birth,
        "verification.insurance_provider": data.patient.insurance_provider,
        "verification.member_id": data.patient.member_id,
        "verification.group_number": data.patient.group_number,
        "verification.eligible": str(data.result.eligible).lower(),
        "verification.copay": data.result.copay,
        "verification.deductible": data.result.deductible,
        "verification.deductible_met": data.result.deductible_met,
        "verification.coinsurance": data.result.coinsurance,
        "verification.out_of_pocket_max": data.result.out_of_pocket_max,
        "verification.coverage_details": data.result.coverage_details,
        "verification.effective_date": data.result.effective_date,
        "verification.termination_date": data.result.termination_date,
        "verification.notes": data.result.notes,
    }

    await room.local_participant.set_attributes(attributes)
    logger.info("Published verification update: status=%s", data.result.status.value)


def _read_patient_from_attributes(
    participant: rtc.RemoteParticipant,
) -> PatientInfo | None:
    """Read patient information from the frontend participant's attributes.

    The frontend sets these attributes before connecting to the room so the
    agent can pick them up automatically.
    """
    attrs = participant.attributes
    if not attrs or not attrs.get("patient.name"):
        return None

    return PatientInfo(
        patient_name=attrs.get("patient.name", ""),
        date_of_birth=attrs.get("patient.date_of_birth", ""),
        member_id=attrs.get("patient.member_id", ""),
        insurance_provider=attrs.get("patient.insurance_provider", ""),
        group_number=attrs.get("patient.group_number", ""),
    )


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def my_agent(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    session = AgentSession(
        stt=inference.STT(model="assemblyai/universal-streaming", language="en"),
        llm=inference.LLM(model="openai/gpt-4.1-mini"),
        tts=inference.TTS(
            model="cartesia/sonic-3", voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
        userdata=VerificationSession(),
    )

    agent = InsuranceVerificationAgent()

    await session.start(
        agent=agent,
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: (
                    noise_cancellation.BVCTelephony()
                    if params.participant.kind
                    == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                    else noise_cancellation.BVC()
                ),
            ),
        ),
    )

    await ctx.connect()

    # Check if the frontend participant has already provided patient info
    # via participant attributes — if so, inject it into the conversation
    for participant in ctx.room.remote_participants.values():
        patient = _read_patient_from_attributes(participant)
        if patient:
            session_data = session.userdata
            session_data.patient = patient
            patient_summary = (
                f"Patient information has been provided: "
                f"Name: {patient.patient_name}, "
                f"DOB: {patient.date_of_birth}, "
                f"Insurance: {patient.insurance_provider}, "
                f"Member ID: {patient.member_id}, "
                f"Group: {patient.group_number}. "
                f"Please confirm the details and proceed with verification."
            )
            await session.generate_reply(
                instructions=patient_summary,
            )
            break


if __name__ == "__main__":
    cli.run_app(server)
