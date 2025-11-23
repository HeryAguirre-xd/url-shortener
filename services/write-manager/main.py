from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os
import datetime
import random
import string

app = FastAPI(title="Write Service (URL Manager)")

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/url_shortener")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Model
class URLItem(Base):
    __tablename__ = "urls"
    id = Column(Integer, primary_key=True, index=True)
    short_code = Column(String, unique=True, index=True)
    long_url = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# Create tables with retry logic
import time
from sqlalchemy.exc import OperationalError

def init_db(retries=5, delay=2):
    for i in range(retries):
        try:
            Base.metadata.create_all(bind=engine)
            print("Database connected and tables created.")
            return
        except OperationalError as e:
            if i == retries - 1:
                raise e
            print(f"Database not ready, retrying in {delay} seconds... ({i+1}/{retries})")
            time.sleep(delay)

init_db()

# Pydantic Models
class URLCreate(BaseModel):
    long_url: str

class URLResponse(BaseModel):
    short_code: str
    long_url: str

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper to generate short code
def generate_short_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "write-manager"}

@app.post("/shorten", response_model=URLResponse)
def create_short_url(url: URLCreate, db: Session = Depends(get_db)):
    # Simple logic: generate random code, check collision (naive), save
    # In a real senior system, we'd use a Key Generation Service (KGS) or Zookeeper
    
    short_code = generate_short_code()
    # TODO: Add collision check loop here
    
    db_url = URLItem(short_code=short_code, long_url=url.long_url)
    db.add(db_url)
    db.commit()
    db.refresh(db_url)
    
    return URLResponse(short_code=short_code, long_url=url.long_url)
