from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
import jwt
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Settings
JWT_SECRET = "check_payment_app_secret_key_2025"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Email Settings
GMAIL_EMAIL = "checknotification01@gmail.com"
GMAIL_PASSWORD = "GeenaJo55!"
NOTIFICATION_EMAIL = "rob@nwtacticalclean.com"

# Pre-defined users
USERS = {
    "Rob": "GeenaJolee55!",
    "Geena": "Elijah6810!",
    "Eric": "Tactical1"
}

# Create the main app
app = FastAPI(title="Check Payment Logger API")
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# Models
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    user_id: str
    username: str

class CheckPaymentCreate(BaseModel):
    businessName: str
    quantitySold: int
    checkImageBase64: str

class CheckPayment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str
    businessName: str
    quantitySold: int
    checkImageBase64: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class CheckPaymentResponse(BaseModel):
    id: str
    userId: str
    businessName: str
    quantitySold: int
    timestamp: datetime

# Authentication functions
def create_access_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None or username not in USERS:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Email function
async def send_email_notification(payment: CheckPayment, username: str):
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = GMAIL_EMAIL
        msg['To'] = NOTIFICATION_EMAIL
        msg['Subject'] = f"New Check Payment Entry - {payment.businessName}"
        
        # Email body
        body = f"""
New check payment entry received:

Timestamp: {payment.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
Submitted by: {username}
Business Name: {payment.businessName}
Quantity Sold: {payment.quantitySold}
Entry ID: {payment.id}

Check image is attached as base64 data (view in image viewer that supports base64).
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_EMAIL, GMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        logging.info(f"Email notification sent for payment {payment.id}")
        
    except Exception as e:
        logging.error(f"Failed to send email notification: {str(e)}")
        # Don't raise exception - email failure shouldn't block payment creation

# API Routes
@api_router.post("/login", response_model=LoginResponse)
async def login(login_request: LoginRequest):
    username = login_request.username
    password = login_request.password
    
    if username not in USERS or USERS[username] != password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    access_token = create_access_token(username)
    
    return LoginResponse(
        access_token=access_token,
        user_id=username,
        username=username
    )

@api_router.post("/payments", response_model=CheckPaymentResponse)
async def create_payment(
    payment_data: CheckPaymentCreate,
    current_user: str = Depends(get_current_user)
):
    # Create payment object
    payment = CheckPayment(
        userId=current_user,
        businessName=payment_data.businessName,
        quantitySold=payment_data.quantitySold,
        checkImageBase64=payment_data.checkImageBase64
    )
    
    # Save to database
    result = await db.check_payments.insert_one(payment.dict())
    
    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="Failed to save payment")
    
    # Send email notification (async, don't wait for completion)
    try:
        await send_email_notification(payment, current_user)
    except Exception as e:
        logging.error(f"Email notification failed: {str(e)}")
    
    return CheckPaymentResponse(
        id=payment.id,
        userId=payment.userId,
        businessName=payment.businessName,
        quantitySold=payment.quantitySold,
        timestamp=payment.timestamp
    )

@api_router.get("/payments", response_model=List[CheckPaymentResponse])
async def get_payments(
    current_user: str = Depends(get_current_user),
    limit: int = 50
):
    payments = await db.check_payments.find(
        {"userId": current_user}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return [
        CheckPaymentResponse(
            id=payment["id"],
            userId=payment["userId"],
            businessName=payment["businessName"],
            quantitySold=payment["quantitySold"],
            timestamp=payment["timestamp"]
        ) for payment in payments
    ]

@api_router.get("/")
async def root():
    return {"message": "Check Payment Logger API", "status": "running"}

# Health check
@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

# Include router
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()