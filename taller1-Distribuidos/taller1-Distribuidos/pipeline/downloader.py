import threading
import queue
import requests
import time
import os
from PIL import Image, ImageDraw
from datetime import datetime
from urllib.parse import urlparse

from database.connection import SessionLocal
from database.models import Imagen, Procesamiento

MEDIA_FOLDER = "media"
os.makedirs(MEDIA_FOLDER, exist_ok=True)



def download_worker(download_queue, resize_queue):
    while True:
        item = download_queue.get()

        if item is None:
            download_queue.task_done()
            break

        imagen_id, url = item
        db = SessionLocal()
        imagen = None

        try:
            imagen = db.query(Imagen).filter(Imagen.id == imagen_id).first()

            if not imagen:
                download_queue.task_done()
                db.close()
                continue

            imagen.estado = "DESCARGANDO"
            db.commit()

            inicio = time.time()

            response = requests.get(url, timeout=10)
            response.raise_for_status()

            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)

            if not filename or "." not in filename:
                filename = f"{imagen_id}_imagen.jpg"
            else:
                filename = f"{imagen_id}_{filename}"

            file_path = os.path.join(MEDIA_FOLDER, filename)

            with open(file_path, "wb") as f:
                f.write(response.content)

            fin = time.time()

            imagen.nombre_archivo = filename
            imagen.ruta_original = file_path
            imagen.tamaño_mb = round(len(response.content) / (1024 * 1024), 4)
            imagen.estado = "DESCARGADO"

            imagen.tiempo_descarga = round(fin - inicio, 4)
            imagen.worker_descarga = threading.current_thread().name

            db.commit()

            resize_queue.put(imagen.id)

        except Exception as e:
            print(" ERROR DESCARGA:", str(e))
            if imagen:
                imagen.estado = "ERROR"
                db.commit()

        finally:
            db.close()
            download_queue.task_done()



def resize_worker(resize_queue, convert_queue):
    while True:
        item = resize_queue.get()

        if item is None:
            resize_queue.task_done()
            break

        imagen_id = item
        db = SessionLocal()
        imagen = None

        try:
            imagen = db.query(Imagen).filter(Imagen.id == imagen_id).first()

            if not imagen:
                resize_queue.task_done()
                db.close()
                continue

            imagen.estado = "REDIMENSIONANDO"
            db.commit()

            inicio = time.time()

            ruta_original = imagen.ruta_original
            nombre_base = os.path.splitext(imagen.nombre_archivo)[0]

            nueva_ruta = os.path.join(
                MEDIA_FOLDER,
                f"{nombre_base}_redimensionada.jpg"
            )

            with Image.open(ruta_original) as img:

                ancho_original, alto_original = img.size
                max_size = 800
    
                if ancho_original <= max_size and alto_original <= max_size:
                    nuevo_ancho = ancho_original
                    nuevo_alto = alto_original
                else:
                    if ancho_original > alto_original:
                        nuevo_ancho = max_size
                        nuevo_alto = int(alto_original * (max_size / ancho_original))
                    else:
                        nuevo_alto = max_size
                        nuevo_ancho = int(ancho_original * (max_size / alto_original))
    
                imagen_redimensionada = img.resize(
                    (nuevo_ancho, nuevo_alto),
                    Image.LANCZOS
            )

            
            imagen_redimensionada.save(nueva_ruta)

            fin = time.time()

            imagen.estado = "REDIMENSIONADO"
            imagen.tiempo_redimension = round(fin - inicio, 4)
            imagen.worker_redimension = threading.current_thread().name

            
            imagen.ruta_original = nueva_ruta

            db.commit()

            convert_queue.put(imagen.id)

        except Exception as e:
            print("🔥 ERROR REDIMENSION:", str(e))
            if imagen:
                imagen.estado = "ERROR"
                db.commit()

        finally:
            db.close()
            resize_queue.task_done()


def convert_worker(convert_queue, watermark_queue):
    while True:
        item = convert_queue.get()

        if item is None:
            convert_queue.task_done()
            break

        imagen_id = item
        db = SessionLocal()
        imagen = None

        try:
            imagen = db.query(Imagen).filter(Imagen.id == imagen_id).first()

            if not imagen:
                convert_queue.task_done()
                db.close()
                continue

            imagen.estado = "CONVIRTIENDO"
            db.commit()

            inicio = time.time()

            ruta_original = imagen.ruta_original
            nombre_base = os.path.splitext(imagen.nombre_archivo)[0]

            nueva_ruta = os.path.join(
                MEDIA_FOLDER,
                f"{nombre_base}_formato_cambiado.png"
            )

            with Image.open(ruta_original) as img:
                img.convert("RGB").save(nueva_ruta, "PNG")
            fin = time.time()
            imagen.ruta_original = nueva_ruta

            imagen.estado = "CONVERTIDO"
            imagen.tiempo_formato = round(fin - inicio, 4)
            imagen.worker_formato = threading.current_thread().name

            db.commit()

            watermark_queue.put(imagen.id)

        except Exception as e:
            print(" ERROR CONVERSION:", str(e))
            if imagen:
                imagen.estado = "ERROR"
                db.commit()

        finally:
            db.close()
            convert_queue.task_done()



def watermark_worker(watermark_queue):
    while True:
        item = watermark_queue.get()

        if item is None:
            watermark_queue.task_done()
            break

        imagen_id = item
        db = SessionLocal()
        imagen = None

        try:
            imagen = db.query(Imagen).filter(Imagen.id == imagen_id).first()

            if not imagen:
                watermark_queue.task_done()
                db.close()
                continue

            imagen.estado = "APLICANDO_MARCA"
            db.commit()

            inicio = time.time()

            nombre_base = os.path.splitext(imagen.nombre_archivo)[0]

            ruta_convertida = os.path.join(
                MEDIA_FOLDER,
                f"{nombre_base}_formato_cambiado.png"
            )

            nueva_ruta = os.path.join(
                MEDIA_FOLDER,
                f"{nombre_base}_marca_agua.png"
            )

            with Image.open(ruta_convertida).convert("RGBA") as base:
                watermark = Image.new("RGBA", base.size, (0, 0, 0, 0))
                draw = ImageDraw.Draw(watermark)

                texto = "MARCA DE AGUA"
                ancho, alto = base.size

                draw.text(
                    (ancho - 250, alto - 50),
                    texto,
                    fill=(255, 0, 0, 120)
                )

                combinado = Image.alpha_composite(base, watermark)
                combinado.convert("RGB").save(nueva_ruta, "PNG")
                imagen.ruta_original = nueva_ruta

            fin = time.time()

            imagen.estado = "COMPLETADO"
            imagen.tiempo_marca = round(fin - inicio, 4)
            imagen.worker_marca = threading.current_thread().name

            db.commit()

        except Exception as e:
            print("ERROR MARCA:", str(e))
            if imagen:
                imagen.estado = "ERROR"
                db.commit()

        finally:
            db.close()
            watermark_queue.task_done()



def iniciar_pipeline(proceso_id, workers_config):

    db = SessionLocal()
    imagenes = db.query(Imagen).filter(
        Imagen.proceso_id == proceso_id
    ).all()
    db.close()

    num_download_workers = workers_config.get("descarga", 3)
    num_resize_workers = workers_config.get("redimension", 2)
    num_convert_workers = workers_config.get("formato", 2)
    num_watermark_workers = workers_config.get("marca_agua", 2)

    download_queue = queue.Queue()
    resize_queue = queue.Queue()
    convert_queue = queue.Queue()
    watermark_queue = queue.Queue()

    download_threads = []
    resize_threads = []
    convert_threads = []
    watermark_threads = []

    for i in range(num_download_workers):
        t = threading.Thread(
            target=download_worker,
            args=(download_queue, resize_queue),
            name=f"download_worker_{i+1}"
        )
        t.start()
        download_threads.append(t)

    for i in range(num_resize_workers):
        t = threading.Thread(
            target=resize_worker,
            args=(resize_queue, convert_queue),
            name=f"resize_worker_{i+1}"
        )
        t.start()
        resize_threads.append(t)

    for i in range(num_convert_workers):
        t = threading.Thread(
            target=convert_worker,
            args=(convert_queue, watermark_queue),
            name=f"convert_worker_{i+1}"
        )
        t.start()
        convert_threads.append(t)

    for i in range(num_watermark_workers):
        t = threading.Thread(
            target=watermark_worker,
            args=(watermark_queue,),
            name=f"watermark_worker_{i+1}"
        )
        t.start()
        watermark_threads.append(t)

    for img in imagenes:
        download_queue.put((img.id, img.url))

    download_queue.join()
    resize_queue.join()
    convert_queue.join()
    watermark_queue.join()

    for q, threads in [
        (download_queue, download_threads),
        (resize_queue, resize_threads),
        (convert_queue, convert_threads),
        (watermark_queue, watermark_threads),
    ]:
        for _ in threads:
            q.put(None)
        for t in threads:
            t.join()

    db = SessionLocal()
    proceso = db.query(Procesamiento).filter(
        Procesamiento.id == proceso_id
    ).first()

    if proceso:
        imagenes = db.query(Imagen).filter(
            Imagen.proceso_id == proceso_id
        ).all()

        total = len(imagenes)
        errores = len([img for img in imagenes if img.estado == "ERROR"])

        if errores == total and total > 0:
            proceso.estado = "FALLIDO"
        elif errores > 0:
            proceso.estado = "COMPLETADO_CON_ERRORES"
        else:
            proceso.estado = "COMPLETADO"

        proceso.fecha_fin = datetime.utcnow()

        if proceso.fecha_inicio:
            proceso.tiempo_total = round(
                (proceso.fecha_fin - proceso.fecha_inicio).total_seconds(),
                2
            )

        db.commit()

    db.close()