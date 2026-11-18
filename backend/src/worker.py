import os,time,json
from datetime import datetime,timezone
from pathlib import Path
from redis import Redis
from sqlalchemy import select
from .database import Session
from .models import FuelSample,Transfer
from .supply_models import SupplySession,SupplySample
from .density_model import compare,compare_values
from .transfer_service import audit
r=Redis.from_url(os.getenv('REDIS_URL','redis://redis:6379/0'),decode_responses=True)
while True:
    Path('/artifacts/bunker-heartbeat').write_text(str(time.time()))
    item=r.blpop(['density-check','supply-sample-check'],timeout=2)
    if not item:continue
    queue,id=item[0],int(item[1])
    if queue=='density-check':
        try:
            with Session.begin() as s:
                x=s.scalar(select(FuelSample).where(FuelSample.id==id).with_for_update())
                if not x or x.status!='queued':continue
                x.log_density,x.threshold,passed,ev=compare(s,x);x.status='qualified'if passed else'anomaly';x.evidence=json.dumps(ev,ensure_ascii=False)
                Path(f'/artifacts/sample-{id}-evidence.json').write_text(x.evidence)
        except Exception as e:
            with Session.begin() as s:
                x=s.get(FuelSample,id)
                if x:x.status='failed';x.evidence=str(e)
    else:
        try:
            with Session.begin() as s:
                x=s.scalar(select(SupplySample).where(SupplySample.id==id).with_for_update())
                if not x or x.status!='queued':continue
                ss=s.scalar(select(SupplySession).where(SupplySession.id==x.session_id).with_for_update())
                tr=s.get(Transfer,ss.transfer_id)
                x.log_density,x.threshold,passed,ev=compare_values(s,tr.grade_snapshot,x.density_15,x.viscosity,x.sulfur)
                x.status='qualified'if passed else'anomaly';x.evidence=json.dumps(ev,ensure_ascii=False)
                Path(f'/artifacts/supply-sample-{id}-evidence.json').write_text(x.evidence)
                if not passed and x.kind=='outlet' and ss.state=='supplying':
                    ss.state='halted';ss.halt_sample_id=x.id;ss.halted_at=datetime.now(timezone.utc).isoformat()
                    audit(s,{'email':'density-worker'},'supply_halted',f'{tr.code}:{x.code}')
        except Exception as e:
            with Session.begin() as s:
                x=s.get(SupplySample,id)
                if x:x.status='failed';x.evidence=str(e)
