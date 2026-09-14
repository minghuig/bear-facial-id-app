from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import settings
from fastapi import Request
from . import tenancy
engine = create_engine(settings().database_url, pool_pre_ping=True)
Session = sessionmaker(engine, expire_on_commit=False)
def session(request: Request):
    with Session() as db:
        if request.url.path.startswith('/api/'):
            db.info['org_id'] = request.state.org_id
        yield db
