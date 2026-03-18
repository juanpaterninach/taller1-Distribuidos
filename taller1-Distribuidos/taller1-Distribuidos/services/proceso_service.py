

import time
from datetime import datetime
from database.connection import SessionLocal
from database.models import Procesamiento


def iniciar_pipeline(proceso_id: str, workers_config: dict):
    

    db = SessionLocal()

    try:
        print(f"[PIPELINE] Iniciando proceso {proceso_id}")
        print(f"[PIPELINE] Configuración workers: {workers_config}")

        
        time.sleep(5)

        proceso = db.query(Procesamiento).filter(
            Procesamiento.id == proceso_id
        ).first()

        if proceso:
            proceso.estado = "COMPLETADO"
            proceso.fecha_fin = datetime.utcnow()
            proceso.tiempo_total = 5
            db.commit()

        print(f"[PIPELINE] Proceso {proceso_id} finalizado")

    except Exception as e:
        print(f"[ERROR] {e}")

    finally:
        db.close()
