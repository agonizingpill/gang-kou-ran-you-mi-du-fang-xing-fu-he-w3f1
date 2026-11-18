from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import select
from .models import Tank,FuelSample,Transfer
from .supply_models import SupplySession,SupplyReading,SupplySample
from .transfer_service import obj,get,audit
from .harbor_service import stamp,now,complete_resources

def session_view(s,x):
    tr=get(s,Transfer,x.transfer_id);sample=s.get(FuelSample,tr.sample_id);tank=s.get(Tank,sample.tank_id)
    halt=s.get(SupplySample,x.halt_sample_id)if x.halt_sample_id else None
    return {**obj(x),'transfer_code':tr.code,'vessel':tr.vessel,'grade':tr.grade_snapshot,'transfer_liters':float(tr.liters),'tank_code':tank.code,'remaining_liters':float(tr.liters-x.supplied_liters),'halt_sample_code':halt.code if halt else None}
def open_session(s,p,u):
    tr=get(s,Transfer,p.transfer_id,True)
    if tr.status!='released':raise HTTPException(409,'仅已放行调拨可建立供油会话')
    if s.scalar(select(SupplySession.id).where(SupplySession.transfer_id==tr.id)):raise HTTPException(409,'该调拨已有供油会话，不能重复建立')
    x=SupplySession(transfer_id=tr.id,state='supplying',supplied_liters=0);s.add(x);s.flush();audit(s,u,'supply_session_opened',tr.code);return session_view(s,x)
def editable(s,id):
    x=get(s,SupplySession,id,True)
    if x.state=='terminated':raise HTTPException(409,'供油会话已终止结算，读数与油样不再登记')
    return x
def register_reading(s,id,p,u):
    x=editable(s,id);taken=stamp(p.taken_at)
    last=datetime.fromisoformat(x.last_reading_at)if x.last_reading_at else None
    applied=not(last and taken<=last)
    if applied:x.supplied_liters=p.meter_total;x.last_reading_at=taken.isoformat()
    r=SupplyReading(session_id=x.id,meter_total=p.meter_total,taken_at=taken.isoformat(),applied=applied,recorded_by=u['email'],created_at=now());s.add(r);s.flush()
    tr=get(s,Transfer,x.transfer_id);audit(s,u,'supply_reading'if applied else'supply_reading_late',f'{tr.code}:{p.meter_total}L');return obj(r)
def register_sample(s,id,p,u):
    x=editable(s,id)
    if p.kind=='outlet'and x.state!='supplying':raise HTTPException(409,'停供期间仅可登记停供复样')
    if p.kind=='resample'and x.state!='halted':raise HTTPException(409,'仅停供待处置时可登记停供复样')
    sm=SupplySample(session_id=x.id,**p.model_dump(),status='queued',evidence='');s.add(sm);s.flush()
    tr=get(s,Transfer,x.transfer_id);audit(s,u,'supply_sample_registered',tr.code+':'+sm.code);return sm
def resume(s,id,u):
    x=get(s,SupplySession,id,True)
    if x.state!='halted':raise HTTPException(409,'仅停供待处置的会话可续供，终止已完成或未曾停供')
    last=s.scalar(select(SupplySample).where(SupplySample.session_id==x.id,SupplySample.kind=='resample').order_by(SupplySample.id.desc()).limit(1))
    if not last:raise HTTPException(409,'尚无停供复样，不能续供')
    if last.status in('queued','received'):raise HTTPException(409,'最新复样仍在判定中，待结果再办理')
    if last.status!='qualified':raise HTTPException(409,'最新复样未合格，须重新取样或终止结算')
    x.state='supplying';x.resume_snapshot={'resample_code':last.code,'density_15':float(last.density_15),'log_density':last.log_density,'threshold':last.threshold,'resumed_by':u['email'],'at':now()}
    tr=get(s,Transfer,x.transfer_id);audit(s,u,'supply_resumed',tr.code+':'+last.code);return session_view(s,x)
def terminate(s,id,u):
    x=get(s,SupplySession,id,True)
    if x.state=='terminated':return session_view(s,x)
    if x.state!='halted':raise HTTPException(409,'仅停供待处置的会话可终止结算')
    tr=get(s,Transfer,x.transfer_id,True);supplied=x.supplied_liters
    if supplied>tr.liters:raise HTTPException(409,'累计实供量超过调拨量，拒绝结算，请核对表量读数')
    returned=tr.liters-supplied
    sample=get(s,FuelSample,tr.sample_id);tank=get(s,Tank,sample.tank_id,True)
    tank.liters+=returned
    complete_resources(s,tr.id,u,'停供终止结算，按实供量交接并释放管线泊位')
    x.state='terminated';x.terminated_by=u['email'];x.settled_supplied=supplied;x.settled_returned=returned
    x.settlement_snapshot={'transfer_code':tr.code,'vessel':tr.vessel,'tank_code':tank.code,'grade':tr.grade_snapshot,'transfer_liters':float(tr.liters),'settled_supplied':float(supplied),'settled_returned':float(returned),'tank_liters_after':float(tank.liters),'terminated_by':u['email'],'at':now()}
    audit(s,u,'supply_terminated',f'{tr.code}:{supplied}L实供/{returned}L返罐');return session_view(s,x)
