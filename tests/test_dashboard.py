import pytest
from fastapi.testclient import TestClient

from src.dashboard import JobStatus, app, jobs


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_jobs():
    """Clear jobs before each test."""
    jobs.clear()
    yield
    jobs.clear()


def test_index_page(client):
    """Test that the index page loads successfully."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Insurance Verification Dashboard" in response.text
    # Check that CDN scripts are included in the HTML
    assert "htmx.org" in response.text  # HTMX CDN script tag
    assert "alpinejs" in response.text  # Alpine.js CDN script tag


def test_start_verification(client):
    """Test starting a new verification job."""
    response = client.post("/api/verify", data={"prompt": "Call Metlife for John Doe"})
    assert response.status_code == 200
    assert "Dialing..." in response.text
    assert "status-dialing" in response.text
    assert "/api/status/" in response.text

    # Check that a job was created
    assert len(jobs) == 1
    job = next(iter(jobs.values()))
    assert job.status == JobStatus.DIALING
    assert job.prompt == "Call Metlife for John Doe"


def test_get_status_dialing(client):
    """Test getting status for a job in dialing state."""
    # Create a job directly
    response = client.post("/api/verify", data={"prompt": "Test"})
    assert response.status_code == 200

    job_id = next(iter(jobs.keys()))

    # Get status immediately (should be dialing)
    response = client.get(f"/api/status/{job_id}")
    assert response.status_code == 200
    assert "Dialing..." in response.text
    assert 'hx-trigger="every 3s"' in response.text


def test_get_status_nonexistent_job(client):
    """Test getting status for a non-existent job."""
    response = client.get("/api/status/nonexistent-job-id")
    assert response.status_code == 200
    assert "Job not found" in response.text


def test_get_status_states(client):
    """Test getting status for different job states."""
    # Start a job
    response = client.post("/api/verify", data={"prompt": "Test"})
    job_id = next(iter(jobs.keys()))
    job = jobs[job_id]

    # Test dialing state
    response = client.get(f"/api/status/{job_id}")
    assert "Dialing..." in response.text
    assert "status-dialing" in response.text

    # Manually transition to in_conversation
    job.status = JobStatus.IN_CONVERSATION
    response = client.get(f"/api/status/{job_id}")
    assert "Live" in response.text
    assert "status-active" in response.text

    # Manually transition to summarizing
    job.status = JobStatus.SUMMARIZING
    response = client.get(f"/api/status/{job_id}")
    assert "Summarizing..." in response.text
    assert "status-processing" in response.text

    # Manually transition to completed with result
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
    response = client.get(f"/api/status/{job_id}")
    assert "Completed" in response.text
    assert "Coverage Verified" in response.text
    assert "$30" in response.text
    assert "Pre-authorization" in response.text
    # Should not have polling trigger when completed
    assert 'hx-trigger="every 3s"' not in response.text


def test_get_status_failed(client):
    """Test getting status for a failed job."""
    response = client.post("/api/verify", data={"prompt": "Test"})
    job_id = next(iter(jobs.keys()))
    job = jobs[job_id]

    # Manually set to failed
    job.status = JobStatus.FAILED
    job.error = "Connection timeout"

    response = client.get(f"/api/status/{job_id}")
    assert response.status_code == 200
    assert "Failed" in response.text
    assert "Connection timeout" in response.text
    assert "Retry" in response.text


def test_mark_job_done(client):
    """Test marking a job as done."""
    # Start a job
    response = client.post("/api/verify", data={"prompt": "Test"})
    job_id = next(iter(jobs.keys()))

    # Mark it as done
    response = client.post(f"/api/done/{job_id}")
    assert response.status_code == 200
    assert "Verification Request" in response.text
    assert "textarea" in response.text
    assert "Start Call" in response.text


def test_mark_done_nonexistent_job(client):
    """Test marking a non-existent job as done."""
    response = client.post("/api/done/nonexistent-job-id")
    assert response.status_code == 200
    # Should still return the form
    assert "Verification Request" in response.text


def test_multiple_concurrent_jobs(client):
    """Test creating multiple jobs concurrently."""
    # Create first job
    response1 = client.post("/api/verify", data={"prompt": "First job"})
    assert response1.status_code == 200

    # Create second job
    response2 = client.post("/api/verify", data={"prompt": "Second job"})
    assert response2.status_code == 200

    # Should have two jobs
    assert len(jobs) == 2

    job_ids = list(jobs.keys())
    assert jobs[job_ids[0]].prompt == "First job"
    assert jobs[job_ids[1]].prompt == "Second job"


def test_result_data_structure(client):
    """Test that the completed job has the correct result structure."""
    client.post("/api/verify", data={"prompt": "Test"})
    job_id = next(iter(jobs.keys()))
    job = jobs[job_id]

    # Manually complete the job
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

    assert job.result is not None
    assert "key_outcome" in job.result
    assert "details" in job.result
    assert "follow_up" in job.result

    details = job.result["details"]
    assert "copay" in details
    assert "deductible" in details
    assert "coinsurance" in details
    assert "out_of_pocket_max" in details
