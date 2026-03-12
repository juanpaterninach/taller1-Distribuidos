const API_BASE = "https://taller-1-distribuidos--juanpaterninach.replit.app";

async function crearProceso() {
    try {

        const texto = document.getElementById("urls").value.trim();
        const urls = texto.split("\n").map(u => u.trim()).filter(u => u !== "");

        if (urls.length === 0) {
            alert("Debes ingresar al menos una URL");
            return;
        }

        const payload = {
            urls: urls,
            workers: {
                descarga: 2,
                redimension: 2,
                formato: 2,
                marca_agua: 2
            }
        };

        const response = await fetch(`${API_BASE}/procesamientos`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Error al crear el proceso");
        }

        const procesoId = data.proceso_id;

        document.getElementById("resultado").innerHTML = `
            <h3> Proceso creado</h3>
            <p><strong>ID del proceso:</strong> ${procesoId}</p>
            <p>Procesando imágenes...</p>
        `;

        
        autoActualizar(procesoId);

    } catch (error) {
        console.error("ERROR:", error);
        alert("Error al crear proceso: " + error.message);
    }
}


async function consultarMetricas(id) {

    try {

        const response = await fetch(`${API_BASE}/procesos/${id}/metricas`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Error al consultar métricas");
        }

        const info = data.informacion_general;
        const resumen = data.resumen_global;
        const etapas = data.metricas_por_etapa;

        document.getElementById("resultado").innerHTML = `

        <h2> Métricas del Proceso</h2>

        <h3>Información General</h3>
        <p><b>ID:</b> ${info.id_proceso}</p>
        <p><b>Estado:</b> ${info.estado}</p>
        <p><b>Inicio:</b> ${info.fecha_inicio}</p>
        <p><b>Fin:</b> ${info.fecha_fin ?? "En proceso"}</p>

        <h3>Resumen Global</h3>
        <p>Total archivos: ${resumen.total_archivos_recibidos}</p>
        <p>Errores: ${resumen.total_archivos_con_error}</p>
        <p>Éxito: ${resumen.porcentaje_exito}%</p>
        <p>Fallo: ${resumen.porcentaje_fallo}%</p>

        <h3>Métricas por Etapa</h3>

        <pre>${JSON.stringify(etapas, null, 2)}</pre>
        `;

        return info.estado;

    } catch (error) {

        console.error("ERROR:", error);
        return null;

    }
}


function autoActualizar(id) {

    const intervalo = setInterval(async () => {

        const estado = await consultarMetricas(id);

        if (!estado) return;

        if (
            estado === "COMPLETADO" ||
            estado === "COMPLETADO_CON_ERRORES" ||
            estado === "FALLIDO"
        ) {

            clearInterval(intervalo);

            alert("Procesamiento terminado. Descargando imágenes...");

            descargarImagenes(id);

        }

    }, 3000);

}


function descargarImagenes(id){

    const url = `${API_BASE}/procesos/${id}/descargar`;

    const link = document.createElement("a");

    link.href = url;
    link.download = "";

    document.body.appendChild(link);

    link.click();

    document.body.removeChild(link);

}