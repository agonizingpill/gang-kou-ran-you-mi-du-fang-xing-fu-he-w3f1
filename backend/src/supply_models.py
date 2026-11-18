"""Mid-supply stoppage disposal: cumulative meter readings, outlet samples, settlement."""
from decimal import Decimal
from sqlalchemy import String,Numeric,Float,Boolean,ForeignKey,JSON,Integer,Text,CheckConstraint
from sqlalchemy.orm import Mapped,mapped_column
from .database import Base
class SupplySession(Base):
    __tablename__='supply_sessions'
    __table_args__=(CheckConstraint('supplied_liters >= 0'),CheckConstraint("state IN ('supplying','halted','terminated')"))
    id:Mapped[int]=mapped_column(primary_key=True)
    transfer_id:Mapped[int]=mapped_column(ForeignKey('transfers.id'),unique=True)
    state:Mapped[str]=mapped_column(String(20),default='supplying')
    supplied_liters:Mapped[Decimal]=mapped_column(Numeric(14,3),default=0)
    last_reading_at:Mapped[str|None]=mapped_column(String(40),nullable=True)
    halt_sample_id:Mapped[int|None]=mapped_column(Integer,nullable=True)
    halted_at:Mapped[str|None]=mapped_column(String(40),nullable=True)
    resume_snapshot:Mapped[dict|None]=mapped_column(JSON,nullable=True)
    settled_supplied:Mapped[Decimal|None]=mapped_column(Numeric(14,3),nullable=True)
    settled_returned:Mapped[Decimal|None]=mapped_column(Numeric(14,3),nullable=True)
    settlement_snapshot:Mapped[dict|None]=mapped_column(JSON,nullable=True)
    terminated_by:Mapped[str|None]=mapped_column(String(120),nullable=True)
class SupplyReading(Base):
    __tablename__='supply_readings'
    __table_args__=(CheckConstraint('meter_total >= 0'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    session_id:Mapped[int]=mapped_column(ForeignKey('supply_sessions.id'))
    meter_total:Mapped[Decimal]=mapped_column(Numeric(14,3))
    taken_at:Mapped[str]=mapped_column(String(40))
    applied:Mapped[bool]=mapped_column(Boolean,default=True)
    recorded_by:Mapped[str]=mapped_column(String(120))
    created_at:Mapped[str]=mapped_column(String(40))
class SupplySample(Base):
    __tablename__='supply_samples'
    __table_args__=(CheckConstraint('density_15 > 0 AND viscosity > 0 AND sulfur >= 0'),CheckConstraint("kind IN ('outlet','resample')"))
    id:Mapped[int]=mapped_column(primary_key=True)
    session_id:Mapped[int]=mapped_column(ForeignKey('supply_sessions.id'))
    code:Mapped[str]=mapped_column(String(70),unique=True)
    kind:Mapped[str]=mapped_column(String(10))
    density_15:Mapped[Decimal]=mapped_column(Numeric(10,3))
    viscosity:Mapped[Decimal]=mapped_column(Numeric(10,3))
    sulfur:Mapped[Decimal]=mapped_column(Numeric(7,4))
    log_density:Mapped[float|None]=mapped_column(Float,nullable=True)
    threshold:Mapped[float|None]=mapped_column(Float,nullable=True)
    status:Mapped[str]=mapped_column(String(20),default='queued')
    evidence:Mapped[str]=mapped_column(Text,default='')
