"""Inferencia de imágenes en el servicio con ONNX Runtime.

Usa los mismos pesos y el mismo preprocesamiento que inferencia_solar.py (PyTorch), exportados a
ONNX. ONNX Runtime ocupa una fracción de la memoria de PyTorch, lo que permite publicar el servicio
completo en una instancia de 512 MB. inferencia_solar.py se mantiene para entrenar y reproducir.
"""
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps

ARCHIVO_ONNX = 'efficientnet_b0_solar.onnx'


def opciones_sesion():
    op = ort.SessionOptions()
    op.intra_op_num_threads = 1
    op.inter_op_num_threads = 1
    op.enable_cpu_mem_arena = False
    return op


def abrir_rgb(ruta):
    with Image.open(ruta) as im:
        im.load()
        return ImageOps.exif_transpose(im).convert('RGB')


def preparar(im, config):
    """EXIF -> RGB -> relleno gris a cuadrado (bilineal) -> [0, 1] -> normalización ImageNet."""
    tam = config['tam']
    im = ImageOps.pad(im, (tam, tam), method=Image.Resampling.BILINEAR, color=(128, 128, 128))
    x = np.asarray(im, dtype=np.float32) / 255.0
    x = (x - np.array(config['media'], dtype=np.float32)) / np.array(config['desv'], dtype=np.float32)
    return x.transpose(2, 0, 1)[None].astype(np.float32)


def cargar_modelo(carpeta, dispositivo='cpu'):
    carpeta = Path(carpeta)
    config = json.loads((carpeta / 'config.json').read_text())
    sesion = ort.InferenceSession(str(carpeta / ARCHIVO_ONNX), sess_options=opciones_sesion(),
                                  providers=['CPUExecutionProvider'])
    return sesion, config, preparar


def predecir(ruta, sesion, config, preparar_fn=preparar, dispositivo='cpu'):
    x = preparar_fn(abrir_rgb(ruta), config)
    logits = sesion.run(None, {sesion.get_inputs()[0].name: x})[0][0].astype(np.float64)
    p = np.exp(logits - logits.max())
    p = p / p.sum()
    i = int(p.argmax())
    clase = config['clases'][i]
    conf = float(p[i])
    baja = conf < config['umbral_revision']
    return {'clase': clase, 'confianza': conf, 'baja_confianza': baja,
            'revision_humana': baja or clase in ['Electrical-damage', 'Physical-Damage'],
            'probabilidades': {c: float(p[k]) for k, c in enumerate(config['clases'])},
            'nota': 'Puntaje softmax no calibrado; no confirma una falla eléctrica.'}
