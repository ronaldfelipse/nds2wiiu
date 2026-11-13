# Busca arte para la portada y las pantallas de arranque de un titulo inyectado.
#
# Prueba varias fuentes en orden de calidad y se queda con la primera que
# responda. Ninguna necesita cuenta ni clave: son repositorios publicos.
#
#   1. UWUVCI-IMAGES   imagenes hechas a medida para inyecciones de Wii U, ya en
#                      1280x720 y 128x128. Es lo mejor, pero cubre pocos juegos.
#   2. libretro        caratulas y capturas indexadas por el nombre exacto de la
#                      ROM. Cubre practicamente todo, a unos 512 pixeles.
#   3. GameTDB         ultimo recurso. Para Nintendo DS solo tiene 240 pixeles.
#
# Una carpeta local (por ejemplo lo que ya escrapeo Batocera) puede anteponerse
# a todas con el argumento 'local'.
import os
import urllib.parse
import urllib.request

AGENTE = {'User-Agent': 'curl/7.88'}
TIEMPO = 30

# sistema -> (carpeta en UWUVCI, repositorio de libretro, seccion de GameTDB)
SISTEMAS = {
    'nds':  ('nds',  'Nintendo_-_Nintendo_DS', 'ds'),
    'n64':  ('n64',  'Nintendo_-_Nintendo_64', None),
    'gcn':  ('gcn',  'Nintendo_-_GameCube', 'wii'),
    'snes': ('snes', 'Nintendo_-_Super_Nintendo_Entertainment_System', None),
    'nes':  ('nes',  'Nintendo_-_Nintendo_Entertainment_System', None),
    'gba':  ('gba',  'Nintendo_-_Game_Boy_Advance', None),
}


def _bajar(url, destino):
    try:
        pedido = urllib.request.Request(url, headers=AGENTE)
        datos = urllib.request.urlopen(pedido, timeout=TIEMPO).read()
    except Exception:
        return False
    if len(datos) < 2000 or datos[:8] != b'\x89PNG\r\n\x1a\n':
        return False
    with open(destino, 'wb') as f:
        f.write(datos)
    return True


def _medir(ruta):
    import struct
    with open(ruta, 'rb') as f:
        d = f.read(24)
    return struct.unpack('>II', d[16:24])


def buscar(sistema, nombre_rom, codigo, carpeta, local=None):
    """Deja en 'carpeta' el mejor arte que encuentre y describe de donde salio.

    nombre_rom va sin extension y con el nombre exacto del archivo, que es como
    lo indexa libretro. codigo es el de 4 letras de la cabecera de la ROM.
    """
    if sistema not in SISTEMAS:
        raise ValueError('sistema no contemplado: %s' % sistema)
    uwuvci, libretro, gametdb = SISTEMAS[sistema]
    os.makedirs(carpeta, exist_ok=True)
    hallazgos = {}

    # 1. Imagenes hechas para inyecciones: vienen ya en las dos medidas exactas.
    if codigo:
        base = 'https://raw.githubusercontent.com/UWUVCI-PRIME/UWUVCI-IMAGES/master/%s/%s' % (
            uwuvci, codigo.upper())
        pantalla = os.path.join(carpeta, 'uwuvci_bootTv.png')
        icono = os.path.join(carpeta, 'uwuvci_icon.png')
        if _bajar(base + '/bootTvTex.png', pantalla):
            hallazgos['pantalla'] = ('uwuvci', pantalla, _medir(pantalla))
            if _bajar(base + '/iconTex.png', icono):
                hallazgos['icono'] = ('uwuvci', icono, _medir(icono))

    # 2. libretro, indexado por el nombre exacto del archivo de la ROM.
    if 'pantalla' not in hallazgos and libretro:
        nombre = urllib.parse.quote(nombre_rom)
        for tipo, clave in (('Named_Boxarts', 'caja'), ('Named_Titles', 'titulo')):
            destino = os.path.join(carpeta, 'libretro_%s.png' % clave)
            url = ('https://raw.githubusercontent.com/libretro-thumbnails/%s/master/%s/%s.png'
                   % (libretro, tipo, nombre))
            if _bajar(url, destino):
                hallazgos.setdefault('pantalla', ('libretro/' + clave, destino, _medir(destino)))
                hallazgos.setdefault('icono', hallazgos['pantalla'])
                break

    # 3. GameTDB, lo mas chico pero lo que mas cubre en consolas de Nintendo.
    if 'pantalla' not in hallazgos and gametdb and codigo:
        for tipo in ('box', 'coverS', 'cover'):
            for region in ('US', 'EN', 'ES'):
                destino = os.path.join(carpeta, 'gametdb_%s.png' % tipo)
                url = 'https://art.gametdb.com/%s/%s/%s/%s.png' % (
                    gametdb, tipo, region, codigo.upper())
                if _bajar(url, destino):
                    hallazgos.setdefault('pantalla', ('gametdb/' + tipo, destino, _medir(destino)))
                    hallazgos.setdefault('icono', hallazgos['pantalla'])
                    break
            if 'pantalla' in hallazgos:
                break

    # Una carpeta local gana a todo: es arte que el usuario ya eligio.
    if local and os.path.isdir(local):
        for n in sorted(os.listdir(local)):
            if n.lower().endswith(('.png', '.jpg', '.jpeg')):
                ruta = os.path.join(local, n)
                hallazgos['pantalla'] = ('local', ruta, None)
                hallazgos['icono'] = ('local', ruta, None)
                break

    return hallazgos
