from fastapi import FastAPI, Request, Response, Depends, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List
from itsdangerous import TimestampSigner, BadSignature, SignatureExpired
from passlib.context import CryptContext
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, Float, DateTime, or_, and_
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, scoped_session
import os, secrets, smtplib, datetime, shutil, uuid

# ---------- Password hashing ----------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------- App & Secrets ----------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Production vs Development database handling
if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("DATABASE_URL"):
    # Production environment - use Railway's database or external database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./globridge.db")
    DB_PATH = "./globridge.db"
else:
    # Development environment
    DB_PATH = os.path.join(BASE_DIR, "globridge.db")
    DATABASE_URL = f"sqlite:///{DB_PATH}"

SECRET_KEY = os.getenv("GLOBRIDGE_SECRET_KEY", "dev-secret-change-me")
COOKIE_NAME = "globridge_session"
SIGNER = TimestampSigner(SECRET_KEY)

# ---------- File Upload Configuration ----------
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/mov", "video/avi", "video/webm"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Create upload directories if they don't exist
os.makedirs(f"{UPLOAD_DIR}/images", exist_ok=True)
os.makedirs(f"{UPLOAD_DIR}/videos", exist_ok=True)

# ---------- SMTP Optional ----------
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM", "Globridge <no-reply@globridge.app>")

def send_email(to_email: str, subject: str, body: str) -> bool:
    if not (SMTP_HOST and SMTP_USERNAME and SMTP_PASSWORD):
        return False
    try:
        msg = f"From: {SMTP_FROM}\r\nTo: {to_email}\r\nSubject: {subject}\r\n\r\n{body}"
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, [to_email], msg.encode('utf-8'))
        return True
    except Exception:
        return False

# ---------- DB ----------
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False))
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # 'business' or 'investor'
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    business = relationship("Business", back_populates="owner", uselist=False)

class SessionToken(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

class Business(Base):
    __tablename__ = "businesses"
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False)
    sector = Column(String(100), nullable=True)
    brand_story = Column(Text, nullable=True)
    investment_needs_min = Column(Float, nullable=True)
    investment_needs_max = Column(Float, nullable=True)
    expansion_potential = Column(Text, nullable=True)
    country = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)

    owner = relationship("User", back_populates="business")

class Requirement(Base):
    __tablename__ = "requirements"
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    sector = Column(String(100), nullable=True)
    main_brand = Column(String(200), nullable=True)
    sub_brand = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    country = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    partnership_type = Column(String(50), nullable=True)  # seek_local_partner | seek_investor | offer_franchise
    budget_min = Column(Float, nullable=True)
    budget_max = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    owner = relationship("User")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=False)
    message_type = Column(String, default="text")  # text, image, file, system
    attachment_url = Column(String, nullable=True)
    attachment_name = Column(String, nullable=True)
    attachment_size = Column(Integer, nullable=True)
    is_read = Column(Integer, default=0)  # 0 = unread, 1 = read
    read_at = Column(DateTime, nullable=True)
    is_deleted = Column(Integer, default=0)  # 0 = active, 1 = deleted
    reply_to_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    post_type = Column(String, default="text")  # text, image, video, article
    media_url = Column(String, nullable=True)
    media_thumbnail = Column(String, nullable=True)
    article_title = Column(String, nullable=True)
    article_summary = Column(Text, nullable=True)
    is_deleted = Column(Integer, default=0)  # 0 = active, 1 = deleted
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class PostReaction(Base):
    __tablename__ = "post_reactions"
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reaction_type = Column(String, default="like")  # like, love, celebrate, support, funny, insightful
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class PostComment(Base):
    __tablename__ = "post_comments"
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    parent_comment_id = Column(Integer, ForeignKey("post_comments.id"), nullable=True)
    is_deleted = Column(Integer, default=0)  # 0 = active, 1 = deleted
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Connection(Base):
    __tablename__ = "connections"
    id = Column(Integer, primary_key=True)
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="pending")  # pending, accepted, declined, blocked
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

Base.metadata.create_all(bind=engine)

# ---------- App init ----------
app = FastAPI(title="Globridge MVP", version="0.1.0")
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# ---------- Helpers ----------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_session(user_id: int, db):
    token_raw = secrets.token_urlsafe(24)
    signed = SIGNER.sign(token_raw.encode()).decode()
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=7)
    st = SessionToken(user_id=user_id, token=signed, expires_at=expires_at)
    db.add(st); db.commit()
    return signed, expires_at

def current_user(request: Request, db):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        unsigned = SIGNER.unsign(token, max_age=60*60*24*8)  # 8 days to align with DB expiry buffer
    except (BadSignature, SignatureExpired):
        return None
    sess = db.query(SessionToken).filter(SessionToken.token == token).first()
    if not sess or sess.expires_at < datetime.datetime.utcnow():
        return None
    return db.query(User).get(sess.user_id)

def require_auth(request: Request, db):
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

# ---------- Routes (web) ----------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# ---------- Schemas ----------
class RegisterForm(BaseModel):
    name: str
    email: str
    password: str
    role: str  # 'business' | 'investor'

class LoginForm(BaseModel):
    email: str
    password: str

class BusinessPayload(BaseModel):
    name: str
    sector: Optional[str] = None
    brand_story: Optional[str] = None
    investment_needs_min: Optional[float] = None
    investment_needs_max: Optional[float] = None
    expansion_potential: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None

class MessagePayload(BaseModel):
    to_user_id: int
    body: str
    message_type: str = "text"
    reply_to_id: Optional[int] = None
    attachment_name: Optional[str] = None

class PostPayload(BaseModel):
    content: str
    post_type: str = "text"  # text, image, video, article
    media_url: Optional[str] = None
    article_title: Optional[str] = None
    article_summary: Optional[str] = None

class ReactionPayload(BaseModel):
    reaction_type: str = "like"  # like, love, celebrate, support, funny, insightful, or empty string to remove

class CommentPayload(BaseModel):
    content: str
    parent_comment_id: Optional[int] = None

class ConnectionPayload(BaseModel):
    receiver_id: int

class RequirementPayload(BaseModel):
    title: str
    sector: Optional[str] = None
    main_brand: Optional[str] = None
    sub_brand: Optional[str] = None
    description: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    partnership_type: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None

# ---------- Auth APIs ----------
@app.post("/api/register")
def register(payload: RegisterForm, db=Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=pwd_context.hash(payload.password),
        role=payload.role
    )
    db.add(user); db.commit()
    return {"ok": True, "user_id": user.id}

@app.post("/api/login")
def login(payload: LoginForm, response: Response, db=Depends(get_db)):
    try:
        user = db.query(User).filter(User.email == payload.email).first()
        if not user or not pwd_context.verify(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token, expires = create_session(user.id, db)
        response.set_cookie(COOKIE_NAME, token, httponly=True, secure=False)
        return {"ok": True, "user": {"id": user.id, "name": user.name, "role": user.role, "email": user.email}}
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}

@app.get("/api/me")
def get_current_user(request: Request, db=Depends(get_db)):
    user = current_user(request, db)
    if user:
        return {"user": {"id": user.id, "name": user.name, "role": user.role, "email": user.email}}
    return {"user": None}

# ---------- Requirement APIs ----------
@app.post("/api/requirements")
def create_requirement(payload: RequirementPayload, request: Request, db=Depends(get_db)):
    user = require_auth(request, db)
    r = Requirement(owner_id=user.id, **payload.model_dump())
    db.add(r); db.commit()
    return {"ok": True, "requirement_id": r.id}

@app.get("/api/requirements")
def list_requirements(request: Request, sector: Optional[str] = None, country: Optional[str] = None,
                      q: Optional[str] = None, partnership_type: Optional[str] = None,
                      db=Depends(get_db)):
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    query = db.query(Requirement).join(User, Requirement.owner_id == User.id)
    if sector: query = query.filter(Requirement.sector.ilike(f"%{sector}%"))
    if country: query = query.filter(Requirement.country.ilike(f"%{country}%"))
    if partnership_type: query = query.filter(Requirement.partnership_type == partnership_type)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Requirement.title.ilike(like)) |
            (Requirement.description.ilike(like)) |
            (Requirement.main_brand.ilike(like)) |
            (Requirement.sub_brand.ilike(like))
        )
    rows = query.order_by(Requirement.id.desc()).all()
    items = []
    for r in rows:
        items.append({
            "id": r.id,
            "title": r.title,
            "sector": r.sector,
            "main_brand": r.main_brand,
            "sub_brand": r.sub_brand,
            "country": r.country,
            "city": r.city,
            "budget": [r.budget_min, r.budget_max],
            "partnership_type": r.partnership_type,
            "owner": {"id": r.owner.id, "name": r.owner.name}
        })
    return {"items": items}

# ---------- Business APIs ----------
@app.post("/api/business")
def create_or_update_business(payload: BusinessPayload, request: Request, db=Depends(get_db)):
    user = require_auth(request, db)
    if user.role != "business":
        raise HTTPException(status_code=403, detail="Only business owners can create a business profile.")
    biz = db.query(Business).filter(Business.owner_id == user.id).first()
    if not biz:
        biz = Business(owner_id=user.id, **payload.model_dump())
        db.add(biz)
    else:
        for k, v in payload.model_dump().items():
            setattr(biz, k, v)
    db.commit()
    return {"ok": True, "business_id": biz.id}

@app.get("/api/businesses")
def list_businesses(sector: Optional[str] = None, country: Optional[str] = None, q: Optional[str] = None, db=Depends(get_db)):
    query = db.query(Business).join(User, Business.owner_id == User.id)
    if sector: query = query.filter(Business.sector.ilike(f"%{sector}%"))
    if country: query = query.filter(Business.country.ilike(f"%{country}%"))
    if q:
        like = f"%{q}%"
        query = query.filter((Business.name.ilike(like)) | (Business.brand_story.ilike(like)) | (Business.expansion_potential.ilike(like)))
    rows = query.order_by(Business.id.desc()).all()
    results = []
    for b in rows:
        results.append({
            "id": b.id,
            "name": b.name,
            "sector": b.sector,
            "country": b.country,
            "city": b.city,
            "owner": {"id": b.owner.id, "name": b.owner.name, "email": b.owner.email},
            "investment_needs": [b.investment_needs_min, b.investment_needs_max],
            "expansion_potential": b.expansion_potential,
        })
    return {"items": results}

@app.get("/api/businesses/{biz_id}")
def get_business(biz_id: int, db=Depends(get_db)):
    b = db.query(Business).get(biz_id)
    if not b: raise HTTPException(status_code=404, detail="Not found")
    return {"id": b.id, "name": b.name, "sector": b.sector, "brand_story": b.brand_story,
            "investment_needs": [b.investment_needs_min, b.investment_needs_max],
            "expansion_potential": b.expansion_potential, "country": b.country, "city": b.city,
            "owner": {"id": b.owner.id, "name": b.owner.name, "email": b.owner.email}}

# ---------- Matching ----------
@app.get("/api/matches")
def get_matches(request: Request, db=Depends(get_db)):
    user = require_auth(request, db)
    # naive matching: sector keyword + investment range overlap
    if user.role == "business":
        biz = db.query(Business).filter(Business.owner_id == user.id).first()
        if not biz:
            return {"items": []}
        # find investors who messaged similar sectors before (proxy) or all investors
        investors = db.query(User).filter(User.role == "investor").all()
        items = [{"user_id": inv.id, "name": inv.name, "email": inv.email, "fit": 0.6} for inv in investors]
        return {"items": items}
    else:
        # user is investor -> show businesses that match simple heuristics
        businesses = db.query(Business).order_by(Business.id.desc()).all()
        items = []
        for b in businesses:
            fit = 0.5
            items.append({
                "business_id": b.id, "name": b.name, "sector": b.sector,
                "country": b.country, "city": b.city,
                "investment_needs": [b.investment_needs_min, b.investment_needs_max],
                "owner": {"id": b.owner.id, "name": b.owner.name, "email": b.owner.email},
                "fit": fit
            })
        return {"items": items}

# ---------- Messaging ----------
@app.post("/api/messages")
def send_message(payload: MessagePayload, request: Request, db=Depends(get_db)):
    sender = require_auth(request, db)
    receiver = db.query(User).get(payload.to_user_id)
    if not receiver: raise HTTPException(status_code=404, detail="Receiver not found")
    msg = Message(sender_id=sender.id, receiver_id=receiver.id, body=payload.body.strip())
    db.add(msg); db.commit()
    # email notify (best-effort)
    send_email(receiver.email, subject=f"New message from {sender.name} on Globridge", 
               body=f"You have a new message:\n\n{payload.body}\n\nLogin to reply.")
    return {"ok": True, "message_id": msg.id}

@app.get("/api/messages/thread/{other_user_id}")
def thread(other_user_id: int, request: Request, db=Depends(get_db)):
    user = require_auth(request, db)
    msgs = db.query(Message).filter(
        ((Message.sender_id==user.id) & (Message.receiver_id==other_user_id)) |
        ((Message.sender_id==other_user_id) & (Message.receiver_id==user.id))
    ).order_by(Message.created_at.asc()).all()
    out = [{"id": m.id, "from": m.sender_id, "to": m.receiver_id, "body": m.body, "created_at": m.created_at.isoformat()} for m in msgs]
    return {"items": out}

# ------------------------------------------------------

# ---------- Cost Comparison ----------
COUNTRY_MULTIPLIERS = {
    # North America
    "USA": {"rent": 1.0, "labor": 1.0, "utilities": 1.0, "logistics": 1.0, "tax": 0.25, "region": "North America"},
    "Canada": {"rent": 0.7, "labor": 0.8, "utilities": 0.9, "logistics": 0.8, "tax": 0.15, "region": "North America"},
    "Mexico": {"rent": 0.25, "labor": 0.12, "utilities": 0.4, "logistics": 0.3, "tax": 0.16, "region": "North America"},
    
    # Europe
    "UK": {"rent": 0.8, "labor": 0.7, "utilities": 1.2, "logistics": 0.9, "tax": 0.20, "region": "Europe"},
    "Germany": {"rent": 0.6, "labor": 0.8, "utilities": 1.1, "logistics": 0.8, "tax": 0.19, "region": "Europe"},
    "France": {"rent": 0.6, "labor": 0.7, "utilities": 1.0, "logistics": 0.8, "tax": 0.20, "region": "Europe"},
    "Italy": {"rent": 0.4, "labor": 0.5, "utilities": 0.9, "logistics": 0.7, "tax": 0.24, "region": "Europe"},
    "Spain": {"rent": 0.35, "labor": 0.4, "utilities": 0.8, "logistics": 0.6, "tax": 0.21, "region": "Europe"},
    "Netherlands": {"rent": 0.7, "labor": 0.8, "utilities": 1.1, "logistics": 0.9, "tax": 0.21, "region": "Europe"},
    "Sweden": {"rent": 0.6, "labor": 0.9, "utilities": 0.8, "logistics": 0.8, "tax": 0.25, "region": "Europe"},
    "Norway": {"rent": 0.8, "labor": 1.1, "utilities": 0.7, "logistics": 1.0, "tax": 0.22, "region": "Europe"},
    "Switzerland": {"rent": 1.2, "labor": 1.3, "utilities": 0.9, "logistics": 1.1, "tax": 0.18, "region": "Europe"},
    "Poland": {"rent": 0.2, "labor": 0.25, "utilities": 0.5, "logistics": 0.4, "tax": 0.19, "region": "Europe"},
    "Czech Republic": {"rent": 0.15, "labor": 0.2, "utilities": 0.4, "logistics": 0.3, "tax": 0.19, "region": "Europe"},
    "Hungary": {"rent": 0.1, "labor": 0.15, "utilities": 0.3, "logistics": 0.25, "tax": 0.15, "region": "Europe"},
    "Romania": {"rent": 0.08, "labor": 0.1, "utilities": 0.25, "logistics": 0.2, "tax": 0.10, "region": "Europe"},
    "Bulgaria": {"rent": 0.06, "labor": 0.08, "utilities": 0.2, "logistics": 0.15, "tax": 0.10, "region": "Europe"},
    "Russia": {"rent": 0.12, "labor": 0.15, "utilities": 0.3, "logistics": 0.25, "tax": 0.20, "region": "Europe"},
    "Turkey": {"rent": 0.15, "labor": 0.12, "utilities": 0.3, "logistics": 0.25, "tax": 0.20, "region": "Europe"},
    
    # Asia Pacific
    "Japan": {"rent": 0.7, "labor": 0.9, "utilities": 1.3, "logistics": 1.1, "tax": 0.30, "region": "Asia Pacific"},
    "China": {"rent": 0.4, "labor": 0.15, "utilities": 0.8, "logistics": 0.6, "tax": 0.13, "region": "Asia Pacific"},
    "India": {"rent": 0.35, "labor": 0.18, "utilities": 0.6, "logistics": 0.7, "tax": 0.18, "region": "Asia Pacific"},
    "South Korea": {"rent": 0.5, "labor": 0.6, "utilities": 0.9, "logistics": 0.8, "tax": 0.25, "region": "Asia Pacific"},
    "Singapore": {"rent": 0.9, "labor": 0.7, "utilities": 0.8, "logistics": 0.9, "tax": 0.17, "region": "Asia Pacific"},
    "Hong Kong": {"rent": 1.5, "labor": 0.6, "utilities": 0.9, "logistics": 0.8, "tax": 0.15, "region": "Asia Pacific"},
    "Taiwan": {"rent": 0.4, "labor": 0.4, "utilities": 0.7, "logistics": 0.6, "tax": 0.20, "region": "Asia Pacific"},
    "Thailand": {"rent": 0.2, "labor": 0.15, "utilities": 0.4, "logistics": 0.3, "tax": 0.20, "region": "Asia Pacific"},
    "Malaysia": {"rent": 0.25, "labor": 0.2, "utilities": 0.5, "logistics": 0.4, "tax": 0.24, "region": "Asia Pacific"},
    "Indonesia": {"rent": 0.15, "labor": 0.1, "utilities": 0.3, "logistics": 0.25, "tax": 0.22, "region": "Asia Pacific"},
    "Philippines": {"rent": 0.12, "labor": 0.08, "utilities": 0.25, "logistics": 0.2, "tax": 0.25, "region": "Asia Pacific"},
    "Vietnam": {"rent": 0.1, "labor": 0.06, "utilities": 0.2, "logistics": 0.15, "tax": 0.20, "region": "Asia Pacific"},
    "Australia": {"rent": 0.8, "labor": 0.9, "utilities": 1.0, "logistics": 1.2, "tax": 0.30, "region": "Asia Pacific"},
    "New Zealand": {"rent": 0.6, "labor": 0.7, "utilities": 0.8, "logistics": 0.9, "tax": 0.28, "region": "Asia Pacific"},
    "Bangladesh": {"rent": 0.08, "labor": 0.04, "utilities": 0.15, "logistics": 0.1, "tax": 0.25, "region": "Asia Pacific"},
    "Pakistan": {"rent": 0.06, "labor": 0.03, "utilities": 0.12, "logistics": 0.08, "tax": 0.29, "region": "Asia Pacific"},
    "Sri Lanka": {"rent": 0.05, "labor": 0.03, "utilities": 0.1, "logistics": 0.08, "tax": 0.14, "region": "Asia Pacific"},
    "Myanmar": {"rent": 0.04, "labor": 0.02, "utilities": 0.08, "logistics": 0.05, "tax": 0.25, "region": "Asia Pacific"},
    "Cambodia": {"rent": 0.03, "labor": 0.02, "utilities": 0.06, "logistics": 0.04, "tax": 0.20, "region": "Asia Pacific"},
    "Laos": {"rent": 0.03, "labor": 0.02, "utilities": 0.05, "logistics": 0.04, "tax": 0.20, "region": "Asia Pacific"},
    "Mongolia": {"rent": 0.08, "labor": 0.06, "utilities": 0.15, "logistics": 0.1, "tax": 0.10, "region": "Asia Pacific"},
    "Nepal": {"rent": 0.04, "labor": 0.02, "utilities": 0.08, "logistics": 0.05, "tax": 0.25, "region": "Asia Pacific"},
    "Bhutan": {"rent": 0.05, "labor": 0.03, "utilities": 0.1, "logistics": 0.06, "tax": 0.30, "region": "Asia Pacific"},
    "Maldives": {"rent": 0.2, "labor": 0.15, "utilities": 0.3, "logistics": 0.25, "tax": 0.15, "region": "Asia Pacific"},
    
    # South America
    "Brazil": {"rent": 0.3, "labor": 0.2, "utilities": 0.7, "logistics": 0.5, "tax": 0.15, "region": "South America"},
    "Argentina": {"rent": 0.2, "labor": 0.15, "utilities": 0.4, "logistics": 0.3, "tax": 0.25, "region": "South America"},
    "Chile": {"rent": 0.25, "labor": 0.18, "utilities": 0.5, "logistics": 0.4, "tax": 0.19, "region": "South America"},
    "Colombia": {"rent": 0.15, "labor": 0.12, "utilities": 0.3, "logistics": 0.25, "tax": 0.19, "region": "South America"},
    "Peru": {"rent": 0.12, "labor": 0.1, "utilities": 0.25, "logistics": 0.2, "tax": 0.18, "region": "South America"},
    "Uruguay": {"rent": 0.18, "labor": 0.15, "utilities": 0.4, "logistics": 0.3, "tax": 0.22, "region": "South America"},
    
    # Africa
    "South Africa": {"rent": 0.2, "labor": 0.15, "utilities": 0.4, "logistics": 0.3, "tax": 0.28, "region": "Africa"},
    "Nigeria": {"rent": 0.08, "labor": 0.05, "utilities": 0.15, "logistics": 0.1, "tax": 0.30, "region": "Africa"},
    "Kenya": {"rent": 0.06, "labor": 0.04, "utilities": 0.12, "logistics": 0.08, "tax": 0.30, "region": "Africa"},
    "Morocco": {"rent": 0.1, "labor": 0.08, "utilities": 0.2, "logistics": 0.15, "tax": 0.31, "region": "Africa"},
    "Egypt": {"rent": 0.05, "labor": 0.03, "utilities": 0.1, "logistics": 0.08, "tax": 0.22, "region": "Africa"},
    "Ghana": {"rent": 0.07, "labor": 0.05, "utilities": 0.15, "logistics": 0.1, "tax": 0.25, "region": "Africa"},
    "Tunisia": {"rent": 0.08, "labor": 0.06, "utilities": 0.15, "logistics": 0.12, "tax": 0.30, "region": "Africa"},
    
    # Middle East
    "UAE": {"rent": 0.6, "labor": 0.3, "utilities": 0.4, "logistics": 0.5, "tax": 0.05, "region": "Middle East"},
    "Saudi Arabia": {"rent": 0.3, "labor": 0.2, "utilities": 0.2, "logistics": 0.3, "tax": 0.20, "region": "Middle East"},
    "Israel": {"rent": 0.7, "labor": 0.8, "utilities": 0.9, "logistics": 0.8, "tax": 0.23, "region": "Middle East"},
    "Qatar": {"rent": 0.5, "labor": 0.25, "utilities": 0.3, "logistics": 0.4, "tax": 0.00, "region": "Middle East"},
    "Kuwait": {"rent": 0.4, "labor": 0.2, "utilities": 0.25, "logistics": 0.3, "tax": 0.00, "region": "Middle East"},
    "Jordan": {"rent": 0.15, "labor": 0.1, "utilities": 0.2, "logistics": 0.15, "tax": 0.20, "region": "Middle East"},
    "Lebanon": {"rent": 0.2, "labor": 0.12, "utilities": 0.25, "logistics": 0.2, "tax": 0.10, "region": "Middle East"},
}

class CostInput(BaseModel):
    base_rent: float = 5000
    base_labor: float = 12000
    base_utilities: float = 1500
    base_logistics: float = 2000
    base_tax: float = 0.0
    countries: List[str] = ["USA", "India"]

@app.get("/api/countries")
def get_countries():
    """Get all available countries for cost comparison"""
    countries = []
    for country, data in COUNTRY_MULTIPLIERS.items():
        countries.append({
            "name": country,
            "region": data["region"]
        })
    
    # Sort by region, then by name
    countries.sort(key=lambda x: (x["region"], x["name"]))
    return {"countries": countries}

@app.post("/api/costs")
def compare_costs(request: Request, payload: CostInput, db=Depends(get_db)):
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    results = []
    for c in payload.countries:
        if c not in COUNTRY_MULTIPLIERS:
            raise HTTPException(status_code=400, detail=f"Unsupported country: {c}")
        m = COUNTRY_MULTIPLIERS[c]
        rent = payload.base_rent * m["rent"]
        labor = payload.base_labor * m["labor"]
        utilities = payload.base_utilities * m["utilities"]
        logistics = payload.base_logistics * m["logistics"]
        tax = (rent + labor + utilities + logistics) * m["tax"]
        total = rent + labor + utilities + logistics + tax
        results.append({
            "country": c,
            "region": m["region"],
            "rent": round(rent, 2),
            "labor": round(labor, 2),
            "utilities": round(utilities, 2),
            "logistics": round(logistics, 2),
            "tax": round(tax, 2),
            "total_monthly": round(total, 2)
        })
    # normalized index
    min_total = min(r["total_monthly"] for r in results)
    for r in results:
        r["cost_index"] = round(r["total_monthly"] / min_total, 2) if min_total > 0 else 1.0
    return {"items": results}

# ------------------------------------------------------

# ---------- Enhanced Messaging APIs ----------
@app.get("/api/conversations")
def get_conversations(request: Request, db=Depends(get_db)):
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Use a single JOIN query to get conversations with partner info
        conversations = db.query(
            Message.sender_id,
            Message.receiver_id,
            Message.body,
            Message.created_at,
            User.name.label('partner_name'),
            User.role.label('partner_role')
        ).join(
            User, 
            or_(
                and_(Message.sender_id == user.id, User.id == Message.receiver_id),
                and_(Message.receiver_id == user.id, User.id == Message.sender_id)
            )
        ).filter(
            or_(Message.sender_id == user.id, Message.receiver_id == user.id)
        ).order_by(Message.created_at.desc()).all()
        
        # Group by conversation partner
        conv_dict = {}
        for conv in conversations:
            # Determine partner ID
            partner_id = conv.receiver_id if conv.sender_id == user.id else conv.sender_id
            
            if partner_id not in conv_dict:
                conv_dict[partner_id] = {
                    "partner_id": partner_id,
                    "partner_name": conv.partner_name,
                    "partner_role": conv.partner_role,
                    "last_message": conv.body,
                    "last_time": conv.created_at,
                    "unread_count": 0
                }
            else:
                # Update if this is a newer message
                if conv.created_at > conv_dict[partner_id]["last_time"]:
                    conv_dict[partner_id]["last_message"] = conv.body
                    conv_dict[partner_id]["last_time"] = conv.created_at
        
        return {"conversations": list(conv_dict.values())}
    except Exception as e:
        print(f"Error in get_conversations: {e}")
        # Return empty conversations on error
        return {"conversations": []}

@app.get("/api/messages/conversation/{partner_id}")
def get_conversation(partner_id: int, request: Request, db=Depends(get_db)):
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get messages between current user and partner (only active messages)
    messages = db.query(Message).filter(
        ((Message.sender_id == user.id) & (Message.receiver_id == partner_id)) |
        ((Message.sender_id == partner_id) & (Message.receiver_id == user.id)),
        Message.is_deleted == 0
    ).order_by(Message.created_at.asc()).all()
    
    # Mark messages as read when viewing conversation
    for msg in messages:
        if msg.receiver_id == user.id and msg.is_read == 0:
            msg.is_read = 1
            msg.read_at = datetime.datetime.utcnow()
    
    db.commit()
    
    partner = db.query(User).filter(User.id == partner_id).first()
    partner_name = partner.name if partner else f"User #{partner_id}"
    
    return {
        "partner_id": partner_id,
        "partner_name": partner_name,
        "messages": [
            {
                "id": msg.id,
                "content": msg.body,
                "from_user_id": msg.sender_id,
                "to_user_id": msg.receiver_id,
                "created_at": msg.created_at,
                "is_from_me": msg.sender_id == user.id,
                "message_type": msg.message_type,
                "is_read": msg.is_read,
                "reply_to_id": msg.reply_to_id,
                "attachment_name": msg.attachment_name
            }
            for msg in messages
        ]
    }

@app.get("/api/messages/unread-count")
def get_unread_count(request: Request, db=Depends(get_db)):
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    unread_count = db.query(Message).filter(
        Message.receiver_id == user.id,
        Message.is_read == 0,
        Message.is_deleted == 0
    ).count()
    
    return {"unread_count": unread_count}

@app.post("/api/messages/mark-read/{message_id}")
def mark_message_read(message_id: int, request: Request, db=Depends(get_db)):
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    message = db.query(Message).filter(
        Message.id == message_id,
        Message.receiver_id == user.id
    ).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    if message.is_read == 0:
        message.is_read = 1
        message.read_at = datetime.datetime.utcnow()
        db.commit()
    
    return {"ok": True}

@app.delete("/api/messages/{message_id}")
def delete_message(message_id: int, request: Request, db=Depends(get_db)):
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    message = db.query(Message).filter(
        Message.id == message_id,
        Message.sender_id == user.id
    ).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    message.is_deleted = 1
    db.commit()
    
    return {"ok": True}

# ---------- File Upload Helper Functions ----------

def save_uploaded_file(file: UploadFile, file_type: str) -> str:
    """Save uploaded file and return the relative URL"""
    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    
    # Determine subdirectory based on file type
    subdir = "images" if file_type == "image" else "videos"
    file_path = os.path.join(UPLOAD_DIR, subdir, unique_filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Return relative URL for serving
    return f"/uploads/{subdir}/{unique_filename}"

def validate_file(file: UploadFile, expected_type: str) -> bool:
    """Validate uploaded file"""
    # Check file size
    if file.size and file.size > MAX_FILE_SIZE:
        return False
    
    # Check file type
    if expected_type == "image" and file.content_type not in ALLOWED_IMAGE_TYPES:
        return False
    elif expected_type == "video" and file.content_type not in ALLOWED_VIDEO_TYPES:
        return False
    
    return True

# ---------- File Upload API Endpoints ----------

@app.post("/api/upload")
async def upload_file(request: Request, file: UploadFile = File(...), file_type: str = "image", db=Depends(get_db)):
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Validate file type parameter
    if file_type not in ["image", "video"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Must be 'image' or 'video'")
    
    # Validate file
    if not validate_file(file, file_type):
        raise HTTPException(status_code=400, detail="Invalid file type or size too large (max 50MB)")
    
    try:
        # Save file and get URL
        file_url = save_uploaded_file(file, file_type)
        
        return {
            "ok": True,
            "file_url": file_url,
            "filename": file.filename,
            "file_type": file_type
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

# ---------- Feed System API Endpoints ----------

@app.get("/api/feed")
def get_feed(request: Request, db=Depends(get_db), limit: int = 20, offset: int = 0):
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Use JOIN query to get posts with author info
        posts_query = db.query(
            Post.id,
            Post.content,
            Post.post_type,
            Post.media_url,
            Post.media_thumbnail,
            Post.article_title,
            Post.article_summary,
            Post.created_at,
            Post.user_id,
            User.name.label('author_name'),
            User.email.label('author_email'),
            User.role.label('author_role')
        ).join(
            User, Post.user_id == User.id
        ).filter(
            Post.is_deleted == 0
        ).order_by(Post.created_at.desc()).offset(offset).limit(limit)
        
        posts = posts_query.all()
        
        # Get reactions and comments for each post
        result_posts = []
        for post in posts:
            # Get reactions count
            reactions = db.query(PostReaction).filter(PostReaction.post_id == post.id).all()
            reaction_counts = {}
            for reaction in reactions:
                reaction_counts[reaction.reaction_type] = reaction_counts.get(reaction.reaction_type, 0) + 1
            
            # Get comments count
            comments_count = db.query(PostComment).filter(
                PostComment.post_id == post.id,
                PostComment.is_deleted == 0
            ).count()
            
            # Get user's reaction to this post
            user_reaction = db.query(PostReaction).filter(
                PostReaction.post_id == post.id,
                PostReaction.user_id == user.id
            ).first()
            
            result_posts.append({
                "id": post.id,
                "content": post.content,
                "post_type": post.post_type,
                "media_url": post.media_url,
                "media_thumbnail": post.media_thumbnail,
                "article_title": post.article_title,
                "article_summary": post.article_summary,
                "created_at": post.created_at,
                "author": {
                    "id": post.user_id,
                    "name": post.author_name,
                    "email": post.author_email,
                    "role": post.author_role
                },
                "reactions": reaction_counts,
                "user_reaction": user_reaction.reaction_type if user_reaction else None,
                "comments_count": comments_count
            })
        
        return {"posts": result_posts}
    except Exception as e:
        print(f"Error in get_feed: {e}")
        return {"posts": []}

@app.post("/api/posts")
def create_post(request: Request, payload: PostPayload, db=Depends(get_db)):
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    post = Post(
        user_id=user.id,
        content=payload.content,
        post_type=payload.post_type,
        media_url=payload.media_url,
        article_title=payload.article_title,
        article_summary=payload.article_summary
    )
    
    db.add(post)
    db.commit()
    db.refresh(post)
    
    return {"ok": True, "post_id": post.id}

@app.post("/api/posts/{post_id}/reactions")
def react_to_post(post_id: int, request: Request, payload: ReactionPayload, db=Depends(get_db)):
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check if post exists
    post = db.query(Post).filter(Post.id == post_id, Post.is_deleted == 0).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Remove existing reaction if any
    existing_reaction = db.query(PostReaction).filter(
        PostReaction.post_id == post_id,
        PostReaction.user_id == user.id
    ).first()
    
    # If reaction_type is empty string, remove existing reaction
    if not payload.reaction_type or payload.reaction_type == '':
        if existing_reaction:
            db.delete(existing_reaction)
    elif existing_reaction:
        if existing_reaction.reaction_type == payload.reaction_type:
            # Remove reaction if same type
            db.delete(existing_reaction)
        else:
            # Update reaction type
            existing_reaction.reaction_type = payload.reaction_type
    else:
        # Add new reaction
        reaction = PostReaction(
            post_id=post_id,
            user_id=user.id,
            reaction_type=payload.reaction_type
        )
        db.add(reaction)
    
    db.commit()
    return {"ok": True}

@app.get("/api/posts/{post_id}/comments")
def get_post_comments(post_id: int, request: Request, db=Depends(get_db)):
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    comments = db.query(PostComment).filter(
        PostComment.post_id == post_id,
        PostComment.is_deleted == 0,
        PostComment.parent_comment_id == None  # Top-level comments only
    ).order_by(PostComment.created_at.asc()).all()
    
    result_comments = []
    for comment in comments:
        comment_author = db.query(User).filter(User.id == comment.user_id).first()
        
        # Get replies
        replies = db.query(PostComment).filter(
            PostComment.parent_comment_id == comment.id,
            PostComment.is_deleted == 0
        ).order_by(PostComment.created_at.asc()).all()
        
        reply_data = []
        for reply in replies:
            reply_author = db.query(User).filter(User.id == reply.user_id).first()
            reply_data.append({
                "id": reply.id,
                "content": reply.content,
                "created_at": reply.created_at,
                "author": {
                    "id": reply_author.id,
                    "name": reply_author.name,
                    "email": reply_author.email
                }
            })
        
        result_comments.append({
            "id": comment.id,
            "content": comment.content,
            "created_at": comment.created_at,
            "author": {
                "id": comment_author.id,
                "name": comment_author.name,
                "email": comment_author.email
            },
            "replies": reply_data
        })
    
    return {"comments": result_comments}

@app.post("/api/posts/{post_id}/comments")
def add_post_comment(post_id: int, request: Request, payload: CommentPayload, db=Depends(get_db)):
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check if post exists
    post = db.query(Post).filter(Post.id == post_id, Post.is_deleted == 0).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    comment = PostComment(
        post_id=post_id,
        user_id=user.id,
        content=payload.content,
        parent_comment_id=payload.parent_comment_id
    )
    
    db.add(comment)
    db.commit()
    db.refresh(comment)
    
    return {"ok": True, "comment_id": comment.id}

# ---------- Personal Dashboard API Endpoints ----------

@app.get("/api/dashboard/stats")
def get_dashboard_stats(request: Request, db=Depends(get_db)):
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get user's posts
    user_posts = db.query(Post).filter(
        Post.user_id == user.id,
        Post.is_deleted == 0
    ).all()
    
    # Get follower count
    followers_count = db.query(Connection).filter(
        Connection.receiver_id == user.id,
        Connection.status == "accepted"
    ).count()
    
    # Get following count
    following_count = db.query(Connection).filter(
        Connection.requester_id == user.id,
        Connection.status == "accepted"
    ).count()
    
    # Calculate engagement metrics
    total_likes = 0
    total_comments = 0
    total_shares = 0
    
    for post in user_posts:
        # Get reactions for this post
        reactions = db.query(PostReaction).filter(PostReaction.post_id == post.id).all()
        total_likes += len(reactions)
        
        # Get comments for this post
        comments = db.query(PostComment).filter(PostComment.post_id == post.id).count()
        total_comments += comments
    
    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role
        },
        "stats": {
            "posts_count": len(user_posts),
            "followers_count": followers_count,
            "following_count": following_count,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "total_shares": total_shares
        },
        "recent_posts": [
            {
                "id": post.id,
                "content": post.content,
                "post_type": post.post_type,
                "media_url": post.media_url,
                "created_at": post.created_at.isoformat(),
                "likes_count": db.query(PostReaction).filter(PostReaction.post_id == post.id).count(),
                "comments_count": db.query(PostComment).filter(PostComment.post_id == post.id).count()
            }
            for post in user_posts[:5]  # Last 5 posts
        ]
    }

@app.get("/api/dashboard/posts")
def get_user_posts(request: Request, db=Depends(get_db), limit: int = 20, offset: int = 0):
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get user's posts with engagement metrics
    posts = db.query(Post).filter(
        Post.user_id == user.id,
        Post.is_deleted == 0
    ).order_by(Post.created_at.desc()).offset(offset).limit(limit).all()
    
    result_posts = []
    for post in posts:
        # Get reactions
        reactions = db.query(PostReaction).filter(PostReaction.post_id == post.id).all()
        reaction_counts = {}
        for reaction in reactions:
            reaction_counts[reaction.reaction_type] = reaction_counts.get(reaction.reaction_type, 0) + 1
        
        # Get comments
        comments = db.query(PostComment).filter(PostComment.post_id == post.id).all()
        
        result_posts.append({
            "id": post.id,
            "content": post.content,
            "post_type": post.post_type,
            "media_url": post.media_url,
            "article_title": post.article_title,
            "article_summary": post.article_summary,
            "created_at": post.created_at.isoformat(),
            "reactions": reaction_counts,
            "comments_count": len(comments),
            "total_engagement": len(reactions) + len(comments)
        })
    
    return {"posts": result_posts}

@app.get("/api/dashboard/followers")
def get_user_followers(request: Request, db=Depends(get_db)):
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get followers (people who follow this user)
    followers = db.query(Connection, User).join(
        User, Connection.requester_id == User.id
    ).filter(
        Connection.receiver_id == user.id,
        Connection.status == "accepted"
    ).all()
    
    return {
        "followers": [
            {
                "id": follower.id,
                "name": follower.name,
                "email": follower.email,
                "role": follower.role,
                "connected_at": connection.created_at.isoformat()
            }
            for connection, follower in followers
        ]
    }

@app.get("/api/dashboard/following")
def get_user_following(request: Request, db=Depends(get_db)):
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get following (people this user follows)
    following = db.query(Connection, User).join(
        User, Connection.receiver_id == User.id
    ).filter(
        Connection.requester_id == user.id,
        Connection.status == "accepted"
    ).all()
    
    return {
        "following": [
            {
                "id": followed.id,
                "name": followed.name,
                "email": followed.email,
                "role": followed.role,
                "connected_at": connection.created_at.isoformat()
            }
            for connection, followed in following
        ]
    }

# ---------- Connection System API Endpoints ----------

@app.get("/api/connections")
def get_connections(request: Request, db=Depends(get_db), status: Optional[str] = None):
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    query = db.query(Connection).filter(
        (Connection.requester_id == user.id) | (Connection.receiver_id == user.id)
    )
    
    if status:
        query = query.filter(Connection.status == status)
    
    connections = query.order_by(Connection.created_at.desc()).all()
    
    result_connections = []
    for conn in connections:
        if conn.requester_id == user.id:
            other_user_id = conn.receiver_id
            connection_type = "sent"
        else:
            other_user_id = conn.requester_id
            connection_type = "received"
        
        other_user = db.query(User).filter(User.id == other_user_id).first()
        
        result_connections.append({
            "id": conn.id,
            "status": conn.status,
            "connection_type": connection_type,
            "created_at": conn.created_at,
            "user": {
                "id": other_user.id,
                "name": other_user.name,
                "email": other_user.email,
                "role": other_user.role
            }
        })
    
    return {"connections": result_connections}

@app.post("/api/connections")
def send_connection_request(request: Request, payload: ConnectionPayload, db=Depends(get_db)):
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if payload.receiver_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot connect to yourself")
    
    # Check if connection already exists
    existing_connection = db.query(Connection).filter(
        (Connection.requester_id == user.id) & (Connection.receiver_id == payload.receiver_id)
    ).first()
    
    if existing_connection:
        raise HTTPException(status_code=400, detail="Connection request already sent")
    
    # Check if reverse connection exists
    reverse_connection = db.query(Connection).filter(
        (Connection.requester_id == payload.receiver_id) & (Connection.receiver_id == user.id)
    ).first()
    
    if reverse_connection:
        raise HTTPException(status_code=400, detail="Connection request already exists")
    
    connection = Connection(
        requester_id=user.id,
        receiver_id=payload.receiver_id,
        status="pending"
    )
    
    db.add(connection)
    db.commit()
    db.refresh(connection)
    
    return {"ok": True, "connection_id": connection.id}

@app.put("/api/connections/{connection_id}")
def update_connection_status(connection_id: int, request: Request, status: str, db=Depends(get_db)):
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    connection = db.query(Connection).filter(
        Connection.id == connection_id,
        Connection.receiver_id == user.id  # Only receiver can update status
    ).first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Connection request not found")
    
    if status not in ["accepted", "declined", "blocked"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    connection.status = status
    db.commit()
    
    return {"ok": True}

@app.get("/api/users/search")
def search_users(request: Request, db=Depends(get_db), q: Optional[str] = None, role: Optional[str] = None):
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    query = db.query(User).filter(User.id != user.id)  # Exclude current user
    
    if q:
        query = query.filter(
            (User.name.ilike(f"%{q}%")) | (User.email.ilike(f"%{q}%"))
        )
    
    if role:
        query = query.filter(User.role == role)
    
    users = query.limit(20).all()
    
    # Get connection status for each user
    result_users = []
    for u in users:
        # Check connection status
        connection = db.query(Connection).filter(
            ((Connection.requester_id == user.id) & (Connection.receiver_id == u.id)) |
            ((Connection.requester_id == u.id) & (Connection.receiver_id == user.id))
        ).first()
        
        connection_status = None
        if connection:
            connection_status = connection.status
        
        result_users.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "connection_status": connection_status
        })
    
    return {"users": result_users}

# ---------- Admin APIs ----------
@app.get("/api/admin/stats")
def get_admin_stats(request: Request, db=Depends(get_db)):
    user = current_user(request, db)
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    total_users = db.query(User).count()
    total_requirements = db.query(Requirement).count()
    total_messages = db.query(Message).count()
    total_businesses = db.query(Business).count()
    
    recent_users = db.query(User).order_by(User.created_at.desc()).limit(5).all()
    recent_requirements = db.query(Requirement).order_by(Requirement.created_at.desc()).limit(5).all()
    recent_messages = db.query(Message).order_by(Message.created_at.desc()).limit(5).all()
    
    return {
        "stats": {
            "total_users": total_users,
            "total_requirements": total_requirements,
            "total_messages": total_messages,
            "total_businesses": total_businesses
        },
        "recent_users": [
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "role": u.role,
                "created_at": u.created_at
            }
            for u in recent_users
        ],
        "recent_requirements": [
            {
            "id": r.id,
            "title": r.title,
            "sector": r.sector,
                "owner_id": r.owner_id,
                "created_at": r.created_at
            }
            for r in recent_requirements
        ],
        "recent_messages": [
            {
                "id": m.id,
                "content": m.body[:50] + "..." if len(m.body) > 50 else m.body,
                "from_user_id": m.sender_id,
                "to_user_id": m.receiver_id,
                "created_at": m.created_at
            }
            for m in recent_messages
        ]
    }

# ---------- Seed demo (optional) ----------
@app.post("/api/seed")
def seed(db=Depends(get_db)):
    if db.query(User).count() > 0:
        return {"skipped": True}

    # Users
    biz_user = User(
        name="HAE's Bakery",
        email="hae@bakery.example",
        password_hash=pwd_context.hash("demo1234"),
        role="business"
    )
    inv_user = User(
        name="BluePeak Investments",
        email="partner@bluepeak.example",
        password_hash=pwd_context.hash("demo1234"),
        role="investor"
    )
    admin_user = User(
        name="Admin User",
        email="admin@globridge.com",
        password_hash=pwd_context.hash("admin123"),
        role="admin"
    )
    db.add_all([biz_user, inv_user, admin_user])
    db.commit()
    db.refresh(biz_user)
    db.refresh(inv_user)
    db.refresh(admin_user)
    
    # Create sample posts
    sample_posts = [
        Post(user_id=biz_user.id, content="Just launched our new e-commerce platform! Looking for international partners to expand globally. #business #expansion", post_type="text"),
        Post(user_id=inv_user.id, content="Excited to announce our partnership with a tech startup in India! The future of global collaboration is here. 🌍", post_type="text"),
        Post(user_id=biz_user.id, content="Check out our latest product demo video showcasing our AI-powered business matching technology.", post_type="video", media_url="https://example.com/demo-video.mp4"),
        Post(user_id=inv_user.id, content="Great insights from today's global expansion webinar. The key takeaway: local partnerships are crucial for success.", post_type="article", article_title="Global Expansion Strategies", article_summary="Learn how to successfully expand your business internationally through strategic partnerships."),
        Post(user_id=admin_user.id, content="Looking for investors interested in sustainable technology solutions. Our green tech innovations are ready for global markets!", post_type="text")
    ]
    
    for post in sample_posts:
        db.add(post)
    
    # Create some connections
    connections = [
        Connection(requester_id=biz_user.id, receiver_id=inv_user.id, status="accepted"),
        Connection(requester_id=inv_user.id, receiver_id=admin_user.id, status="accepted"),
        Connection(requester_id=biz_user.id, receiver_id=admin_user.id, status="pending"),
    ]
    
    for conn in connections:
        db.add(conn)
    
    db.commit()

    # Businesses (many for Listings)
    businesses = [
        Business(owner_id=biz_user.id, name="HAE’s Bakery", sector="Food & Beverage",
                 brand_story="Artisan sourdough bakery with loyal local following.",
                 investment_needs_min=50000, investment_needs_max=150000,
                 expansion_potential="Open 2 outlets in 12 months with central kitchen.",
                 country="USA", city="Springfield, IL"),

        Business(owner_id=biz_user.id, name="Sunrise Breads", sector="Food & Beverage",
                 brand_story="Neighborhood favorite with strong breakfast traffic.",
                 investment_needs_min=30000, investment_needs_max=90000,
                 expansion_potential="Kiosk + cloud kitchen pilot then high-street outlet.",
                 country="Mexico", city="Mexico City"),

        Business(owner_id=biz_user.id, name="Desi Dough", sector="Food & Beverage",
                 brand_story="Modern Indian bakery combining millet & sourdough.",
                 investment_needs_min=40000, investment_needs_max=120000,
                 expansion_potential="Tie-up with US brand for sub-brand launch.",
                 country="India", city="Bengaluru, KA"),

        Business(owner_id=biz_user.id, name="Tea & Toast", sector="Cafe",
                 brand_story="Afternoon tea cafe with patisserie focus.",
                 investment_needs_min=60000, investment_needs_max=180000,
                 expansion_potential="Co-brand with established bakery for UK rollout.",
                 country="UK", city="London"),

        Business(owner_id=biz_user.id, name="Date Palm Pastry", sector="Food & Beverage",
                 brand_story="Gulf-inspired desserts, premium dates & coffee.",
                 investment_needs_min=70000, investment_needs_max=200000,
                 expansion_potential="Airport kiosk + mall flagship.",
                 country="UAE", city="Dubai"),

        Business(owner_id=biz_user.id, name="Nordic Crumbs", sector="Food & Beverage",
                 brand_story="Cinnamon rolls & rye breads with Scandi vibe.",
                 investment_needs_min=45000, investment_needs_max=120000,
                 expansion_potential="US East Coast with partner roastery.",
                 country="USA", city="Boston, MA"),

        Business(owner_id=biz_user.id, name="La Petite Fournée", sector="Food & Beverage",
                 brand_story="Parisian viennoiserie with buttery excellence.",
                 investment_needs_min=80000, investment_needs_max=220000,
                 expansion_potential="Co-brand launch in UAE luxury malls.",
                 country="France", city="Paris"),

        Business(owner_id=biz_user.id, name="Casa Pan", sector="Food & Beverage",
                 brand_story="Latin artisan breads; strong wholesale channel.",
                 investment_needs_min=50000, investment_needs_max=150000,
                 expansion_potential="Franchise partners across Texas border towns.",
                 country="Mexico", city="Monterrey"),

        Business(owner_id=biz_user.id, name="Biscotti & Co.", sector="Food & Beverage",
                 brand_story="Italian biscotti & espresso with retail packs.",
                 investment_needs_min=35000, investment_needs_max=100000,
                 expansion_potential="Grocery retail + cafe corners in India.",
                 country="Italy", city="Milan"),

        Business(owner_id=biz_user.id, name="Bakehouse Oz", sector="Food & Beverage",
                 brand_story="Lamingtons, ANZAC biscuits & sourdough.",
                 investment_needs_min=55000, investment_needs_max=140000,
                 expansion_potential="US West Coast pop-ups then permanent sites.",
                 country="Australia", city="Sydney"),
    ]
    db.add_all(businesses); db.commit()

    # Sample requirements (for the new Requirements section)
    reqs = [
        Requirement(owner_id=biz_user.id, title="Seeking Bangalore partner for HAE’s Bakery sub-brand",
                    sector="Food & Beverage", main_brand="HAE’s Bakery", sub_brand="HAE’s India",
                    description="Looking for a well-known Bangalore bakery to co-brand. Shared recipes, local sourcing, joint marketing.",
                    country="India", city="Bengaluru", partnership_type="seek_local_partner",
                    budget_min=50000, budget_max=150000),

        Requirement(owner_id=inv_user.id, title="Investor seeking bakery chain for UAE malls",
                    sector="Food & Beverage", main_brand="(Open)", sub_brand=None,
                    description="Back a premium bakery brand to enter Dubai & Abu Dhabi luxury malls.",
                    country="UAE", city="Dubai", partnership_type="seek_investor",
                    budget_min=120000, budget_max=300000),
    ]
    db.add_all(reqs); db.commit()

    return {"ok": True}

# ---------- Connection Management API Endpoints ----------

@app.get("/api/users/search")
def search_users(request: Request, db=Depends(get_db), q: str = "", role: str = ""):
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Build query
    query = db.query(User).filter(User.id != user.id)  # Exclude current user
    
    if q:
        query = query.filter(
            (User.name.ilike(f"%{q}%")) |
            (User.email.ilike(f"%{q}%"))
        )
    
    if role:
        query = query.filter(User.role == role)
    
    users = query.limit(20).all()
    
    # Get connection status for each user
    result_users = []
    for u in users:
        # Check if there's a connection between current user and this user
        connection = db.query(Connection).filter(
            ((Connection.requester_id == user.id) & (Connection.receiver_id == u.id)) |
            ((Connection.requester_id == u.id) & (Connection.receiver_id == user.id))
        ).first()
        
        connection_status = "none"
        if connection:
            if connection.status == "accepted":
                connection_status = "connected"
            elif connection.requester_id == user.id:
                connection_status = "sent"
            else:
                connection_status = "received"
        
        result_users.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "connection_status": connection_status
        })
    
    return {"users": result_users}

@app.post("/api/connections/send")
def send_connection_request(request: Request, payload: ConnectionPayload, db=Depends(get_db)):
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if payload.receiver_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot connect to yourself")
    
    # Check if receiver exists
    receiver = db.query(User).get(payload.receiver_id)
    if not receiver:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if connection already exists
    existing_connection = db.query(Connection).filter(
        ((Connection.requester_id == user.id) & (Connection.receiver_id == payload.receiver_id)) |
        ((Connection.requester_id == payload.receiver_id) & (Connection.receiver_id == user.id))
    ).first()
    
    if existing_connection:
        if existing_connection.status == "accepted":
            raise HTTPException(status_code=400, detail="Already connected")
        elif existing_connection.requester_id == user.id:
            raise HTTPException(status_code=400, detail="Connection request already sent")
        else:
            raise HTTPException(status_code=400, detail="Connection request already received")
    
    # Create new connection request
    connection = Connection(
        requester_id=user.id,
        receiver_id=payload.receiver_id,
        status="pending"
    )
    db.add(connection)
    db.commit()
    
    return {"message": "Connection request sent", "connection_id": connection.id}

@app.post("/api/connections/respond")
def respond_to_connection_request(request: Request, connection_id: int, action: str, db=Depends(get_db)):
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    connection = db.query(Connection).get(connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Connection request not found")
    
    if connection.receiver_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to respond to this request")
    
    if connection.status != "pending":
        raise HTTPException(status_code=400, detail="Connection request already processed")
    
    if action == "accept":
        connection.status = "accepted"
        db.commit()
        return {"message": "Connection request accepted"}
    elif action == "decline":
        db.delete(connection)
        db.commit()
        return {"message": "Connection request declined"}
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'accept' or 'decline'")

@app.get("/api/connections/requests")
def get_connection_requests(request: Request, db=Depends(get_db)):
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get pending requests received by current user
    pending_requests = db.query(Connection, User).join(
        User, Connection.requester_id == User.id
    ).filter(
        Connection.receiver_id == user.id,
        Connection.status == "pending"
    ).all()
    
    # Get sent requests by current user
    sent_requests = db.query(Connection, User).join(
        User, Connection.receiver_id == User.id
    ).filter(
        Connection.requester_id == user.id,
        Connection.status == "pending"
    ).all()
    
    return {
        "received_requests": [
            {
                "connection_id": conn.id,
                "user": {
                    "id": u.id,
                    "name": u.name,
                    "email": u.email,
                    "role": u.role
                },
                "sent_at": conn.created_at.isoformat()
            }
            for conn, u in pending_requests
        ],
        "sent_requests": [
            {
                "connection_id": conn.id,
                "user": {
                    "id": u.id,
                    "name": u.name,
                    "email": u.email,
                    "role": u.role
                },
                "sent_at": conn.created_at.isoformat()
            }
            for conn, u in sent_requests
        ]
    }
