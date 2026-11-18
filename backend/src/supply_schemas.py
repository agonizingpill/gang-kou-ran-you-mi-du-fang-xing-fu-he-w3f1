from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel,Field,ConfigDict
class Clean(BaseModel):model_config=ConfigDict(str_strip_whitespace=True)
class SessionIn(Clean):transfer_id:int=Field(gt=0)
class ReadingIn(Clean):
    meter_total:Decimal=Field(ge=0,le=100000000,max_digits=14,decimal_places=3)
    taken_at:datetime
class SupplySampleIn(Clean):
    code:str=Field(min_length=2,max_length=70)
    kind:Literal['outlet','resample']
    density_15:Decimal=Field(gt=0,le=1500,max_digits=10,decimal_places=3)
    viscosity:Decimal=Field(gt=0,le=1000,max_digits=10,decimal_places=3)
    sulfur:Decimal=Field(ge=0,le=5,max_digits=7,decimal_places=4)
