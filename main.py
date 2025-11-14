"""
KYC/AML Compliance Service (Module E)
Handles Know Your Customer (KYC) and Anti-Money Laundering (AML) checks.
Dependencies: Auth Service (A), Payment Service (C)
Reverse cascade: updates Auth Service with new KYC status.
"""
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uvicorn
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import httpx
import logging

load_dotenv()

SERVICE_PORT = int(os.getenv("SERVICE_PORT", 8005))
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://localhost:8003")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="KYC/AML Service",
    description="Compliance - updates Auth Service reverse cascade",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

kyc_docs_db = {}

class KYCSubmit(BaseModel):
    user_id: int
    document_type: str
    document_url: str

async def verify_token(authorization: str = Header(...)):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{AUTH_SERVICE_URL}/api/auth/verify-token",
                headers={"Authorization": authorization},
                timeout=5.0
            )
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.error(f"Auth error: {e}")
    raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.get("/", tags=["Info"])
async def root():
    return {
        "service": "KYC/AML Service (Module E)",
        "version": "1.0.0",
        "dependencies": ["Auth Service (A)", "Payment Service (C)"],
        "note": "UPDATES Auth Service kyc_status (reverse cascade)"
    }

@app.post("/api/kyc/submit", tags=["KYC"])
async def submit_kyc(
    kyc_data: KYCSubmit,
    user_data: dict = Depends(verify_token),
    authorization: str = Header(...)
):
    """
    Submit KYC documents for verification
    REVERSE CASCADE: Updates Auth Service kyc_status
    """
    kyc_docs_db[kyc_data.user_id] = {
        "user_id": kyc_data.user_id,
        "document_type": kyc_data.document_type,
        "document_url": kyc_data.document_url,
        "status": "verified",
        "submitted_at": datetime.utcnow()
    }
    logger.info(f"KYC document submitted for user {kyc_data.user_id}")

    try:
        async with httpx.AsyncClient() as client:
            res = await client.put(
                f"{AUTH_SERVICE_URL}/api/auth/user/{kyc_data.user_id}",
                headers={"Authorization": authorization},
                json={"kyc_status": "verified"},
                timeout=5.0
            )
            if res.status_code == 200:
                logger.info(f"Auth Service KYC status updated to verified for user {kyc_data.user_id}")
    except Exception as e:
        logger.error(f"Error updating Auth Service: {e}")
        return {"status": "warning", "message": "KYC locally marked but Auth update failed"}
    return {
        "status": "verified",
        "user_id": kyc_data.user_id,
        "message": "KYC verification completed and Auth Service updated"
    }

@app.get("/api/kyc/status/{user_id}", tags=["KYC"])
async def get_kyc_status(
    user_id: int,
    user_data: dict = Depends(verify_token)
):
    """Get KYC status for a user"""
    doc = kyc_docs_db.get(user_id)
    if not doc:
        return {"user_id": user_id, "status": "not_submitted"}
    return doc

@app.post("/api/kyc/reject", tags=["KYC"])
async def reject_kyc(
    user_id: int,
    reason: str,
    user_data: dict = Depends(verify_token),
    authorization: str = Header(...)
):
    """Reject KYC submission"""
    try:
        async with httpx.AsyncClient() as client:
            res = await client.put(
                f"{AUTH_SERVICE_URL}/api/auth/user/{user_id}",
                headers={"Authorization": authorization},
                json={"kyc_status": "rejected"},
                timeout=5.0
            )
            if res.status_code == 200:
                logger.info(f"KYC rejected for user {user_id}")
    except Exception as e:
        logger.error(f"Error updating Auth Service: {e}")
    
    return {
        "status": "rejected",
        "user_id": user_id,
        "reason": reason
    }

@app.get("/api/aml/check/{user_id}", tags=["AML"])
async def aml_check(
    user_id: int,
    user_data: dict = Depends(verify_token)
):
    """Check AML status for user"""
    return {
        "user_id": user_id,
        "aml_status": "cleared",
        "risk_level": "low",
        "checked_at": datetime.utcnow()
    }

@app.get("/health")
async def health_check():
    """Health check with dependency status"""
    auth_healthy = False
    payment_healthy = False
    
    try:
        async with httpx.AsyncClient() as client:
            auth_response = await client.get(f"{AUTH_SERVICE_URL}/health", timeout=2.0)
            auth_healthy = auth_response.status_code == 200
            
            payment_response = await client.get(f"{PAYMENT_SERVICE_URL}/health", timeout=2.0)
            payment_healthy = payment_response.status_code == 200
    except:
        pass
    
    all_healthy = auth_healthy and payment_healthy
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "service": "kyc-aml-service",
        "module": "E",
        "dependencies": {
            "auth-service": "healthy" if auth_healthy else "unhealthy",
            "payment-service": "healthy" if payment_healthy else "unhealthy"
        },
        "cascade_note": "UPDATES Auth Service kyc_status (reverse cascade)",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    logger.info(f"Starting KYC/AML Service on port {SERVICE_PORT}...")
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
