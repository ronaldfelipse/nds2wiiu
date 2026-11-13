# Lectura de la cabecera de una ROM de Nintendo DS, venga suelta o comprimida.
#
# De aqui sale el codigo de juego de cuatro letras, que es lo que usamos para
# darle identidad propia al titulo inyectado y para buscarle arte. Se lee del
# archivo en vez de pedirselo al usuario: es un dato que ya esta ahi.
#
# El soporte de .zip no es un lujo: las ROMs circulan comprimidas casi siempre,
# y obligar a descomprimir a mano era el primer tropiezo de cualquiera que
# usara esto por primera vez.
import contextlib
import os
import re
import shutil
import struct
import tempfile
import zipfile

EXTENSIONES = ('.nds', '.srl')
LARGO_CABECERA = 0x200


def es_comprimida(ruta):
    return os.path.splitext(ruta)[1].lower() in ('.zip', '.7z')


def _miembro(z, ruta):
    """El primer .nds o .srl que haya dentro del comprimido."""
    for nombre in z.namelist():
        if nombre.lower().endswith(EXTENSIONES) and not nombre.endswith('/'):
            return nombre
    raise ValueError('%s no contiene ninguna ROM de DS (.nds o .srl)' % ruta)


def _interpretar(datos, tamano, ruta):
    if len(datos) < LARGO_CABECERA:
        raise ValueError('%s es demasiado chico para ser una ROM de DS' % ruta)

    titulo = datos[0:12].decode('ascii', 'replace').rstrip('\x00 ')
    codigo = datos[12:16].decode('ascii', 'replace')
    if not codigo.isalnum():
        raise ValueError('%s no parece una ROM de DS: el codigo de juego es ilegible'
                         % ruta)

    return {
        'titulo_interno': titulo,
        'codigo': codigo,
        'fabricante': datos[16:18].decode('ascii', 'replace'),
        'unidad': datos[0x12],
        'usado': struct.unpack('<I', datos[0x80:0x84])[0],
        'tamano': tamano,
        'es_dsi': datos[0x12] != 0,
    }


def nombre_legible(ruta):
    """El nombre del juego para mostrar, sacado del nombre del archivo.

    El titulo interno de la cabecera NO sirve para esto: son 12 caracteres y
    trae abreviaturas. "Prince Caspian" aparece como CASPIAN y "Crash: Mind
    over Mutant" como CRASH08DS, y eso es lo que terminaba leyendose debajo
    del icono en el menu de la consola.

    El nombre del archivo, en cambio, suele venir completo de No-Intro. Se le
    quitan el numero de lanzamiento y los parentesis de region e idiomas, y se
    le da vuelta el articulo que No-Intro escribe al final.
    """
    base = os.path.splitext(os.path.basename(ruta))[0]
    base = re.sub(r'^\s*\d{3,5}\s*[-_.]\s*', '', base)
    base = re.sub(r'\s*[\(\[][^\)\]]*[\)\]]', '', base)
    base = re.sub(r'^(.*?), (The|A|An|Los|Las|El|La)\b', r'\2 \1', base)
    return ' '.join(base.split()).strip(' -')


def cabecera(ruta):
    """Devuelve lo que interesa de la cabecera de un .nds, .srl o .zip.

    De un comprimido se leen solo los primeros 512 bytes del miembro, sin
    extraerlo: descomprimir 60 MB para mirar medio kilobyte no tiene sentido,
    y 'bases' hace justamente eso.
    """
    if ruta.lower().endswith('.7z'):
        raise ValueError('los .7z no estan soportados; descomprimilo a mano')

    if ruta.lower().endswith('.zip'):
        with zipfile.ZipFile(ruta) as z:
            nombre = _miembro(z, ruta)
            info = z.getinfo(nombre)
            with z.open(nombre) as f:
                return _interpretar(f.read(LARGO_CABECERA), info.file_size, ruta)

    with open(ruta, 'rb') as f:
        return _interpretar(f.read(LARGO_CABECERA), os.path.getsize(ruta), ruta)


@contextlib.contextmanager
def abierta(ruta):
    """Entrega la ruta de un .nds de verdad, extrayendolo si hace falta.

    Lo extraido se borra al salir. Para inyectar hace falta el archivo entero,
    a diferencia de leer la cabecera.
    """
    if not es_comprimida(ruta):
        yield ruta
        return

    if ruta.lower().endswith('.7z'):
        raise ValueError('los .7z no estan soportados; descomprimilo a mano')

    carpeta = tempfile.mkdtemp(prefix='nds2wiiu-rom-')
    try:
        with zipfile.ZipFile(ruta) as z:
            nombre = _miembro(z, ruta)
            # Se escribe con el nombre a secas: un zip puede traer rutas con
            # carpetas, y no hace falta reproducirlas.
            destino = os.path.join(carpeta, os.path.basename(nombre))
            with z.open(nombre) as origen, open(destino, 'wb') as salida:
                shutil.copyfileobj(origen, salida)
        yield destino
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)
