from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime
import os

# Define database file path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'panel.db')}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    cloudflare_token = Column(String, nullable=True)

class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    command = Column(String)
    port = Column(Integer, nullable=True)
    autostart = Column(Boolean, default=False)
    log_file = Column(String, nullable=True)
    type = Column(String, default="system") # system OR custom
    config_file = Column(String, nullable=True)

class InstalledApp(Base):
    __tablename__ = "installed_apps"
    id = Column(Integer, primary_key=True, index=True)
    app_key = Column(String, unique=True, index=True) # e.g. 'pihole', 'nginx'
    installed_at = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default="installed")

def init_db():
    Base.metadata.create_all(bind=engine)
    
    # Auto-migration for new schema
    try:
        with engine.begin() as conn:
            from sqlalchemy import text
            conn.execute(text("ALTER TABLE services ADD COLUMN config_file VARCHAR"))
    except Exception:
        pass # Ignore if column already exists
        
    # Create default user if not exists
    db = SessionLocal()
    if not db.query(User).filter(User.username == "admin").first():
        import bcrypt
        hashed_pw = bcrypt.hashpw("admin".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        default_user = User(username="admin", hashed_password=hashed_pw)
        db.add(default_user)
        db.commit()
    db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
