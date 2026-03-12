import os
import threading
import uvicorn
import zipfile


from fastapi import APIRouter
from uuid import UUID
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse

from database.connection import SessionLocal, engine
from database.models import Base, Procesamiento, Imagen
from schemas.proceso_schema import ProcesoCreate
from pipeline.downloader import iniciar_pipeline
from fastapi.middleware.cors import CORSMiddleware  

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


Base.metadata.create_all(bind=engine)



@app.get("/")
def health_check():
    return {"status": "ok"}



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



@app.post("/procesamientos")
def crear_procesamiento(data: ProcesoCreate, db: Session = Depends(get_db)):

    nuevo_proceso = Procesamiento(
        estado="EN_PROCESO"
    )

    db.add(nuevo_proceso)
    db.commit()
    db.refresh(nuevo_proceso)

    for url in data.urls:
        nueva_imagen = Imagen(
            proceso_id=nuevo_proceso.id,
            url=str(url),
            estado="PENDIENTE"
        )
        db.add(nueva_imagen)

    db.commit()

   
    hilo = threading.Thread(
        target=iniciar_pipeline,
        args=(nuevo_proceso.id, data.workers.dict())
    )
    hilo.start()

    return {
        "mensaje": "Proceso creado correctamente",
        "proceso_id": nuevo_proceso.id
    }

@app.get("/procesamientos/{proceso_id}")
def obtener_procesamiento(proceso_id: str, db: Session = Depends(get_db)):

    proceso = db.query(Procesamiento).filter(
        Procesamiento.id == proceso_id
    ).first()

    if not proceso:
        return {"error": "Proceso no encontrado"}

    imagenes = db.query(Imagen).filter(
        Imagen.proceso_id == proceso_id
    ).all()

    return {
        "id": proceso.id,
        "estado": proceso.estado,
        "fecha_inicio": proceso.fecha_inicio,
        "fecha_fin": proceso.fecha_fin,
        "tiempo_total": proceso.tiempo_total,
        "total_imagenes": len(imagenes),
        "imagenes": [
            {
                "id": img.id,
                "url": img.url,
                "estado": img.estado,
                "tiempo_formato": img.tiempo_formato,
                "worker_formato": img.worker_formato,
                "tiempo_marca": img.tiempo_marca,
                "worker_marca": img.worker_marca
            }
            for img in imagenes
        ]
    }

@app.get("/procesos/{proceso_id}/metricas")
def obtener_metricas(proceso_id: str):

    db = SessionLocal()

    proceso = db.query(Procesamiento).filter(
        Procesamiento.id == proceso_id
    ).first()

    if not proceso:
        db.close()
        raise HTTPException(status_code=404, detail="Proceso no encontrado")

    imagenes = db.query(Imagen).filter(
        Imagen.proceso_id == proceso_id
    ).all()

    total_archivos = len(imagenes)
    total_errores = len([img for img in imagenes if img.estado == "ERROR"])

   
    def metricas_etapa(tiempo_attr):
        procesados = [img for img in imagenes if getattr(img, tiempo_attr)]
        fallidos = len([img for img in imagenes if img.estado == "ERROR"])
        tiempo_total = sum(getattr(img, tiempo_attr) or 0 for img in procesados)

        promedio = round(tiempo_total / len(procesados), 4) if procesados else 0

        return {
            "total_procesados": len(procesados),
            "total_fallidos": fallidos,
            "tiempo_total_acumulado": round(tiempo_total, 4),
            "tiempo_promedio": promedio
        }

    metricas = {
        "descarga": metricas_etapa("tiempo_descarga"),
        "redimension": metricas_etapa("tiempo_redimension"),
        "formato": metricas_etapa("tiempo_formato"),
        "marca_agua": metricas_etapa("tiempo_marca")
    }

    porcentaje_exito = round(
        ((total_archivos - total_errores) / total_archivos) * 100,
        2
    ) if total_archivos else 0

    porcentaje_fallo = round(
        (total_errores / total_archivos) * 100,
        2
    ) if total_archivos else 0

    respuesta = {
        "informacion_general": {
            "id_proceso": proceso.id,
            "estado": proceso.estado,
            "fecha_inicio": proceso.fecha_inicio,
            "fecha_fin": proceso.fecha_fin,
            "tiempo_total": proceso.tiempo_total
        },
        "metricas_por_etapa": metricas,
        "resumen_global": {
            "total_archivos_recibidos": total_archivos,
            "total_archivos_con_error": total_errores,
            "porcentaje_exito": porcentaje_exito,
            "porcentaje_fallo": porcentaje_fallo
        }
    }

    db.close()
    return respuesta

@app.get("/procesos/{proceso_id}/descargar")
def descargar_imagenes(proceso_id: str, db: Session = Depends(get_db)):

    imagenes = db.query(Imagen).filter(
        Imagen.proceso_id == proceso_id,
        Imagen.estado == "COMPLETADO"
    ).all()

    if not imagenes:
        raise HTTPException(status_code=404, detail="No hay imágenes completadas")

    os.makedirs("media", exist_ok=True)

    zip_path = f"media/proceso_{proceso_id}.zip"

    with zipfile.ZipFile(zip_path, "w") as zipf:

        for img in imagenes:

            if img.ruta_original and os.path.exists(img.ruta_original):

                zipf.write(
                    img.ruta_original,
                    os.path.basename(img.ruta_original)
                )

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"imagenes_proceso_{proceso_id}.zip"
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)