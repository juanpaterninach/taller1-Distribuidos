# schemas/proceso_schema.py

from pydantic import BaseModel, HttpUrl, Field
from typing import List


class WorkersConfig(BaseModel):
    descarga: int = Field(..., gt=0)
    redimension: int = Field(..., gt=0)
    formato: int = Field(..., gt=0)
    marca_agua: int = Field(..., gt=0)


class ProcesoCreate(BaseModel):
    urls: List[HttpUrl]
    workers: WorkersConfig