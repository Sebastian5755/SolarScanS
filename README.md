# SolarScan · Sistema de apoyo a la decisión para O&M de plantas solares

Proyecto final del curso IA Generativa para la Gestión Industrial (UDD, 2026-2).
Integrantes: Miguel González · Sebastián Muñoz · Renato Valdés. Profesor: Danilo Gómez.

SolarScan ayuda al supervisor de operación y mantenimiento (O&M) de una planta fotovoltaica a decidir
qué inversor o panel atender primero. Un inspector sube la foto de un panel en un formulario; el flujo
de n8n consulta tres modelos, Gemini redacta una recomendación integrada que cita el manual de O&M, el
supervisor aprueba por Telegram antes de crear una orden de trabajo y el resultado llega por Gmail y
Telegram y queda registrado en Google Sheets, que alimenta el tablero.

| Recurso | Enlace |
|---|---|
| Aplicación y API | https://solarscans.onrender.com |
| Tablero publicado | https://solarscans.onrender.com/tablero |
| Documentación de la API | https://solarscans.onrender.com/docs |

## Requisitos de la pauta y dónde se cumplen

| Requisito | Dónde está |
|---|---|
| R1 LLM con salida JSON | `recomendacion_integrada.py`, nodo "LLM · Recomendación integrada (Gemini)" |
| R2 Código Python | Servicio FastAPI (`api_solar.py`) llamado desde n8n con nodos HTTP |
| R3 Serie temporal | `serie_temporal/`, `notebooks/02_serie_temporal.ipynb` |
| R4 Reconocimiento de imágenes | `inferencia_solar.py`, `notebooks/03_imagenes_comparacion.ipynb` |
| R5 Transformer / NLP | `rag/` (embeddings `gemini-embedding-001` sobre el manual de NREL) |
| R6 Automatización | `n8n/SolarScan_Flujo_Principal_Hito2.json` y flujos de apoyo |
| R7 Contexto industrial | Informe final, sección 1 |
| R8 Datos | Informe final, sección 2; tabla de datos más abajo |
| R9 Tablero | `tablero/`, publicado en `/tablero` |
| R10 Negocio y ética | `negocio/SolarScan_ROI.xlsx`; informe, secciones 8 y 9 |
| R11 Notificaciones | Nodos Gmail y Telegram del flujo principal |

## Arquitectura

```
Formulario n8n (foto + inversor + fecha)
   |
   |-> Modelo 1 · Imágenes       POST /predict               EfficientNet-B0 (CNN preentrenada)
   |-> Modelo 2 · Serie temporal GET  /serie/estado          Regresión física (decide) + LSTM (segunda opinión)
   |-> Modelo 3 · Transformer    POST /rag/buscar            Embeddings sobre el manual de O&M de NREL
   |
   |-> Resumen único (n8n) -> POST /recomendacion-integrada  Reglas + Gemini + 4 controles de alucinación
   |-> ¿Requiere orden de trabajo? -> Aprobación humana por Telegram (máx. 2 h)
   '-> Google Sheets (historial) -> Gmail + Telegram -> Tablero /tablero
```

Flujos de n8n (carpeta `n8n/`, exportados sin credenciales):

| Archivo | Función |
|---|---|
| `SolarScan_Flujo_Principal_Hito2.json` | Flujo principal: formulario, tres modelos, LLM, aprobación humana, registro y avisos |
| `SolarScan_Flujo_Monitoreo_Diario.json` | Cada día a las 08:00 consulta la serie temporal y avisa qué inversores inspeccionar |
| `SolarScan_Flujo_Errores.json` | Avisa por Gmail y Telegram si una ejecución falla |

## Estructura del repositorio

| Ruta | Contenido |
|---|---|
| `api_solar.py`, `interfaz_solar.py` | API FastAPI, interfaz web y tablero |
| `inferencia_solar.py`, `modelo/` | Modelo de imágenes y sus pesos |
| `recomendacion_integrada.py` | Reglas de decisión, prompt, validación del JSON y verificación de cifras y fuentes |
| `recomendacion_gemini.py` | Recomendación de la interfaz web del Hito 1 |
| `serie_temporal/` | Servicio de la serie temporal, datos de la planta 2 y artefactos entrenados |
| `rag/` | Construcción del índice del manual, buscador (embeddings y regla fija) y evaluación |
| `notebooks/` | `02_serie_temporal` (ejecutado) y `03_imagenes_comparacion` |
| `n8n/` | Flujos exportados |
| `tablero/` | Tablero web (HTML, CSS y JavaScript) |
| `negocio/SolarScan_ROI.xlsx` | Beneficio, costos, ROI por escenario y sensibilidad |
| `docs/` | Configuración del despliegue y plantilla de Google Sheets |
| `test_hito2.py` | Pruebas de la serie, reglas, controles del LLM, buscador y endpoints |
| `.github/workflows/modelos-hito2.yml` | Reproduce el índice del manual, la evaluación del buscador y la comparación de imágenes |

## Datos

| Componente | Fuente | Tamaño | Licencia |
|---|---|---|---|
| Imágenes | Kaggle `pythonafroz/solar-panel-images` | 885 imágenes, 787 usadas, 6 clases | No especificada en Kaggle |
| Serie temporal | Kaggle `anikannal/solar-power-generation-data`, planta 2 | 22 inversores, 34 días, cada 15 min (67.698 registros) | No especificada en Kaggle |
| Manual de O&M | NREL/TP-7A40-73822, *Best Practices for O&M of PV and Energy Storage Systems*, 3.ª ed. (2018) | Informe técnico público | Publicación pública de NREL |

Supuestos declarados: los datos de generación son de mayo y junio de 2020 y el sistema los reproduce día
a día como si fueran la operación actual; el inspector indica a qué inversor corresponde el panel de la
foto; la detección de fallas se evalúa con fallas inyectadas, porque el dataset no trae etiquetas. El PDF
del manual no se incluye en el repositorio: `rag/construir_indice.py` indica de dónde descargarlo.

## Resultados

**Serie temporal** (prueba: 11 al 17 de junio; umbral de 90 % elegido en validación):

| Modelo | MAE (kW) | Error energía diaria | F1 detección |
|---|---|---|---|
| Ingenuo (día anterior) | 208,9 | 25,7 % | 0,562 |
| Promedio móvil 3 días | 211,4 | 31,9 % | 0,664 |
| Regresión lineal física (elegido) | 71,1 | 4,0 % | 0,992 |
| LSTM | 86,2 | 5,1 % | 0,987 |

**Imágenes** (validación 118 fotos, prueba 117; `notebooks/03_imagenes_comparacion.ipynb`):

| Modelo | Macro-F1 validación | Macro-F1 prueba | Latencia CPU | Tamaño |
|---|---|---|---|---|
| Árbol de umbrales (base) | – | 38,2 % | – | – |
| EfficientNet-B0 (en servicio) | 79,2 % | 57,6 % | 14 ms | 16 MB |
| ConvNeXt-Tiny (elegido por la regla) | 92,9 % | 78,2 % | 59 ms | 111 MB |
| ViT-Small/16 | 90,0 % | 84,7 % | 58 ms | 87 MB |

La regla fijada antes de comparar (cambiar si otro modelo supera en 0,05 el macro-F1 de validación)
elige ConvNeXt-Tiny. El servicio mantiene EfficientNet-B0 mientras se valida la migración: ConvNeXt
pesa 7 veces más (111 MB, sobre el límite de 100 MB por archivo de GitHub) y responde 4 veces más lento.

**Manual (RAG)**, 12 preguntas, 323 fragmentos (`rag/resultados_rag.json`):

| Método | Acierto@3 | Precisión@3 | MRR@3 |
|---|---|---|---|
| Embeddings gemini-embedding-001 | 91,7 % | 77,8 % | 0,861 |
| Regla fija (palabras clave + BM25) | 91,7 % | 77,8 % | 0,819 |

Umbral de "sin información": 0,617 (preguntas del tema ≥ 0,658; fuera de tema ≤ 0,576).

## Ejecución local

```bash
python -m venv .venv && source .venv/bin/activate      # en Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt               # servicio (ONNX Runtime, sin PyTorch)
python -m uvicorn interfaz_solar:app --host 127.0.0.1 --port 8000
python -m pytest -q
```

Para entrenar, reproducir los notebooks o volver a exportar los modelos a ONNX:
`python -m pip install -r requirements-entrenamiento.txt`. El servicio usa los mismos pesos exportados
a ONNX (`modelo/efficientnet_b0_solar.onnx`, `serie_temporal/artefactos/lstm_solar.onnx`): las
probabilidades difieren de PyTorch en menos de 0,0001 y el servicio completo ocupa unos 160 MB.

## Variables de entorno (Render)

| Variable | Uso |
|---|---|
| `GEMINI_API_KEY` | Gemini (recomendación y embeddings). Nunca se escribe en el código. |
| `GEMINI_MODEL` | Opcional; por defecto `gemini-3.5-flash-lite` |
| `N8N_WEBHOOK_TOKEN` | Secreto compartido con n8n; protege `/recomendacion-integrada` |
| `TABLERO_CSV_URL` | Hoja `Recomendaciones` de Google Sheets publicada como CSV |
| `N8N_WEBHOOK_URL` | Avisos de la interfaz web del Hito 1 (opcional) |

La configuración paso a paso está en `docs/CONFIGURACION.md`.

## Seguridad y límites

- Ninguna clave, token, correo ni identificador de chat está en el repositorio ni en los flujos exportados.
- Gemini recibe resultados de los modelos, nunca la fotografía ni datos personales; el formulario pide un código de inspector, no un nombre.
- La acción y la prioridad las deciden reglas auditables; toda orden de trabajo requiere aprobación humana.
- Es un prototipo académico: no confirma fallas eléctricas ni reemplaza la inspección técnica.
