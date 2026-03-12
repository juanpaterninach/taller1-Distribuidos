# database/models.py

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from .connection import Base



class Procesamiento(Base):
    __tablename__ = "procesamientos"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    estado = Column(String, nullable=False, default="EN_PROCESO")
    fecha_inicio = Column(DateTime, default=datetime.utcnow)
    fecha_fin = Column(DateTime, nullable=True)
    tiempo_total = Column(Float, nullable=True)
    

    # Relaciones
    imagenes = relationship("Imagen", back_populates="proceso", cascade="all, delete")
    metricas = relationship("MetricaEtapa", back_populates="proceso", cascade="all, delete")



class Imagen(Base):
    __tablename__ = "imagenes"

    id = Column(Integer, primary_key=True, index=True)
    proceso_id = Column(String, ForeignKey("procesamientos.id"))

    url = Column(String, nullable=False)
    nombre_archivo = Column(String, nullable=True)
    tamaño_mb = Column(Float, nullable=True)
    ruta_original = Column(String, nullable=True)
    tiempo_descarga = Column(Float, nullable=True)
    worker_descarga = Column(String, nullable=True)
    tiempo_redimension = Column(Float, nullable=True)
    worker_redimension = Column(String, nullable=True)
    tiempo_formato = Column(Float, nullable=True)
    worker_formato = Column(String, nullable=True)
    tiempo_marca = Column(Float, nullable=True)
    worker_marca = Column(String, nullable=True)
    estado = Column(String, default="PENDIENTE")
    

    
    proceso = relationship("Procesamiento", back_populates="imagenes")



class MetricaEtapa(Base):
    __tablename__ = "metricas_etapa"

    id = Column(Integer, primary_key=True, index=True)
    proceso_id = Column(String, ForeignKey("procesamientos.id"))

    etapa = Column(String, nullable=False)  
    total_exitosos = Column(Integer, default=0)
    total_fallidos = Column(Integer, default=0)
    tiempo_total = Column(Float, default=0.0)
    tiempo_promedio = Column(Float, default=0.0)

    
    proceso = relationship("Procesamiento", back_populates="metricas")