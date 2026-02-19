import asyncio
import logging
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    DIALING = "dialing"
    IN_CONVERSATION = "in_conversation"
    SUMMARIZING = "summarizing"
    COMPLETED = "completed"
    FAILED = "failed"


class VerificationJob:
    def __init__(self, job_id: str, prompt: str):
        self.job_id = job_id
        self.prompt = prompt
        self.status = JobStatus.DIALING
        self.created_at = datetime.now()
        self.result = None
        self.error = None


# In-memory job storage
jobs: Dict[str, VerificationJob] = {}

app = FastAPI(title="Insurance Verification Dashboard")

# Set up templates
template_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(template_dir))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main dashboard HTML page."""
    return templates.TemplateResponse(request, "index.html")


@app.post("/api/verify", response_class=HTMLResponse)
async def start_verification(prompt: str = Form(...)):
    """Start a new insurance verification job."""
    job_id = str(uuid.uuid4())
    job = VerificationJob(job_id, prompt)
    jobs[job_id] = job

    logger.info(f"Created job {job_id} with prompt: {prompt[:50]}...")

    # Start background simulation
    asyncio.create_task(simulate_verification_lifecycle(job_id))

    # Return initial status card
    return get_status_html(job_id)


@app.get("/api/status/{job_id}", response_class=HTMLResponse)
async def get_status(job_id: str):
    """Get the current status of a verification job."""
    return get_status_html(job_id)


@app.post("/api/done/{job_id}", response_class=HTMLResponse)
async def mark_done(job_id: str):
    """Mark a job as done and return to the initial form."""
    if job_id in jobs:
        logger.info(f"Marking job {job_id} as done")
        # Keep the job in memory but return the form
        jobs[job_id].status = JobStatus.COMPLETED

    # Return the initial form HTML
    return """
    <div class="card">
        <form hx-post="/api/verify" hx-target="#main-content" hx-swap="innerHTML" x-data="{ prompt: '' }">
            <div class="input-section">
                <label for="prompt">Verification Request</label>
                <textarea 
                    id="prompt" 
                    name="prompt" 
                    x-model="prompt"
                    placeholder="Call Metlife customer service to validate the following patient's insurance. Patient Name: 'John Doe', Patient Insurance Number: '123'"
                    required
                ></textarea>
            </div>
            <div class="button-group">
                <button 
                    type="button" 
                    class="btn-secondary"
                    @click="prompt = 'Call [insurance company] to verify coverage for [patient name], DOB [date], member ID [number]'"
                >
                    📞 Quick Template
                </button>
                <button type="submit" class="btn-primary">
                    <span>Start Call</span>
                    <span class="htmx-indicator spinner"></span>
                </button>
            </div>
        </form>
    </div>
    """


def get_status_html(job_id: str) -> str:
    """Generate HTML fragment for the current job status."""
    job = jobs.get(job_id)
    if not job:
        return "<div class='card'><p>Job not found.</p></div>"

    if job.status == JobStatus.DIALING:
        return f"""
        <div class="card">
            <div class="status-card" hx-get="/api/status/{job_id}" hx-trigger="every 3s" hx-swap="outerHTML">
                <div class="status-indicator status-dialing pulsing"></div>
                <div class="status-content">
                    <div class="status-title">Dialing...</div>
                    <div class="status-message">Connecting to insurance provider</div>
                </div>
            </div>
        </div>
        """

    elif job.status == JobStatus.IN_CONVERSATION:
        return f"""
        <div class="card">
            <div class="status-card" hx-get="/api/status/{job_id}" hx-trigger="every 3s" hx-swap="outerHTML">
                <div class="status-indicator status-active pulsing"></div>
                <div class="status-content">
                    <div class="status-title">
                        <span class="live-badge">Live</span>
                    </div>
                    <div class="status-message">In conversation with representative</div>
                </div>
            </div>
        </div>
        """

    elif job.status == JobStatus.SUMMARIZING:
        return f"""
        <div class="card">
            <div class="status-card" hx-get="/api/status/{job_id}" hx-trigger="every 3s" hx-swap="outerHTML">
                <div class="status-indicator status-processing pulsing"></div>
                <div class="status-content">
                    <div class="status-title">Summarizing...</div>
                    <div class="status-message">Analyzing call results</div>
                </div>
            </div>
        </div>
        """

    elif job.status == JobStatus.COMPLETED and job.result:
        return f"""
        <div class="card">
            <div class="status-card">
                <div class="status-indicator status-complete"></div>
                <div class="status-content">
                    <div class="status-title">Completed ✓</div>
                    <div class="status-message">Verification finished successfully</div>
                </div>
            </div>
            
            <div class="result-section">
                <div class="result-outcome">{job.result['key_outcome']}</div>
                
                <div class="result-label">Details</div>
                <dl>
                    <dt>Copay</dt>
                    <dd>{job.result['details']['copay']}</dd>
                    
                    <dt>Deductible</dt>
                    <dd>{job.result['details']['deductible']}</dd>
                    
                    <dt>Coinsurance</dt>
                    <dd>{job.result['details']['coinsurance']}</dd>
                    
                    <dt>Out-of-Pocket Max</dt>
                    <dd>{job.result['details']['out_of_pocket_max']}</dd>
                </dl>
                
                <div style="margin-top: 16px;">
                    <div class="result-label">Follow-up Needed</div>
                    <div class="result-value">{job.result['follow_up']}</div>
                </div>
            </div>
            
            <div style="margin-top: 20px;">
                <button 
                    class="btn-done" 
                    hx-post="/api/done/{job_id}" 
                    hx-target="#main-content" 
                    hx-swap="innerHTML"
                    style="width: 100%;"
                >
                    Done ✓
                </button>
            </div>
        </div>
        """

    elif job.status == JobStatus.FAILED:
        return f"""
        <div class="card">
            <div class="status-card">
                <div class="status-indicator status-failed"></div>
                <div class="status-content">
                    <div class="status-title">Failed</div>
                    <div class="status-message">{job.error or 'Call could not be completed'}</div>
                </div>
            </div>
            
            <div style="margin-top: 20px; display: flex; gap: 12px;">
                <button 
                    class="btn-retry" 
                    hx-post="/api/verify" 
                    hx-vals='{{"prompt": "{job.prompt}"}}'
                    hx-target="#main-content" 
                    hx-swap="innerHTML"
                    style="flex: 1;"
                >
                    🔄 Retry
                </button>
                <button 
                    class="btn-secondary" 
                    hx-post="/api/done/{job_id}" 
                    hx-target="#main-content" 
                    hx-swap="innerHTML"
                    style="flex: 1;"
                >
                    Cancel
                </button>
            </div>
        </div>
        """

    return "<div class='card'><p>Unknown status.</p></div>"


async def simulate_verification_lifecycle(job_id: str):
    """Simulate the verification call lifecycle with status transitions."""
    job = jobs.get(job_id)
    if not job:
        return

    try:
        # Dialing phase (3 seconds)
        await asyncio.sleep(3)
        job.status = JobStatus.IN_CONVERSATION
        logger.info(f"Job {job_id}: In conversation")

        # Conversation phase (10 seconds)
        await asyncio.sleep(10)
        job.status = JobStatus.SUMMARIZING
        logger.info(f"Job {job_id}: Summarizing")

        # Summarizing phase (3 seconds)
        await asyncio.sleep(3)
        job.status = JobStatus.COMPLETED
        job.result = {
            "key_outcome": "Coverage Verified — Patient Eligible",
            "details": {
                "copay": "$30",
                "deductible": "$500 ($350 met)",
                "coinsurance": "80/20",
                "out_of_pocket_max": "$3,000",
            },
            "follow_up": "Pre-authorization required for specialist visits",
        }
        logger.info(f"Job {job_id}: Completed successfully")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        job.status = JobStatus.FAILED
        job.error = str(e)
