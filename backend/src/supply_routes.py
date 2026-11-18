import os
from fastapi import APIRouter,Depends
from redis import Redis
from sqlalchemy import select
from .database import Session
from .security import current,allow
from .supply_models import SupplySession,SupplyReading,SupplySample
from .supply_schemas import SessionIn,ReadingIn,SupplySampleIn
from .transfer_service import obj
from . import supply_service as svc
router=APIRouter()
r=Redis.from_url(os.getenv('REDIS_URL','redis://redis:6379/0'),decode_responses=True)
@router.get('/supply-sessions')
def sessions(u=Depends(current)):
    with Session() as s:return [svc.session_view(s,x)for x in s.scalars(select(SupplySession).order_by(SupplySession.id.desc()))]
@router.post('/supply-sessions')
def open(p:SessionIn,u=Depends(current)):
    allow(u,'admin','chemist')
    with Session.begin() as s:return svc.open_session(s,p,u)
@router.get('/supply-readings')
def readings(u=Depends(current)):
    with Session() as s:return [obj(x)for x in s.scalars(select(SupplyReading).order_by(SupplyReading.id.desc()))]
@router.post('/supply-sessions/{id}/readings')
def reading(id:int,p:ReadingIn,u=Depends(current)):
    allow(u,'admin','chemist')
    with Session.begin() as s:return svc.register_reading(s,id,p,u)
@router.get('/supply-samples')
def samples(u=Depends(current)):
    with Session() as s:return [obj(x)for x in s.scalars(select(SupplySample).order_by(SupplySample.id.desc()))]
@router.post('/supply-sessions/{id}/samples')
def sample(id:int,p:SupplySampleIn,u=Depends(current)):
    allow(u,'admin','chemist')
    with Session.begin() as s:x=svc.register_sample(s,id,p,u)
    r.rpush('supply-sample-check',x.id);return obj(x)
@router.post('/supply-sessions/{id}/resume')
def resume(id:int,u=Depends(current)):
    allow(u,'admin')
    with Session.begin() as s:return svc.resume(s,id,u)
@router.post('/supply-sessions/{id}/terminate')
def terminate(id:int,u=Depends(current)):
    allow(u,'admin')
    with Session.begin() as s:return svc.terminate(s,id,u)
