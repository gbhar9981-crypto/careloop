from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Use MySQL with pymysql
# Password contains an @ symbol, so it must be URL encoded as %40
DEFAULT_DATABASE_URL = "mysql+pymysql://admin:Prasant2457@careloop-db.c8ru6qqwilnm.us-east-1.rds.amazonaws.com:3306/careloop"
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
