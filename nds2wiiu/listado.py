# La lista de compatibilidad de la comunidad, consultada de verdad.
#
# Durante un buen rato este proyecto dio por sentado que no existia ninguna
# tabla publica y consultable de que base conviene para cada juego de DS, y
# construyo todo alrededor de esa creencia: un registro propio, una heuristica
# de "el emulador mas nuevo" y, al final, una consulta a un modelo de lenguaje.
#
# Existe. El hilo de GBAtemp "[NEW] Wii U NDS Injection Compatibility List"
# mantiene una hoja de calculo de Google con 547 juegos clasificados en tres
# estados, y Google la exporta como CSV con una direccion armada a mano. Sin
# clave, sin cuenta, sin modelo: una descarga y a leer.
#
# Lo que la hoja aclara en su propia cabecera, y que cambia la recomendacion
# por defecto de esta herramienta:
#
#   "Unless specified, Base Game (WUP) is always [USA] New Super Mario Bros."
#
# Es decir: la base que la comunidad usa por defecto es New Super Mario Bros.
# (USA), y solo 28 de los 547 juegos piden una base distinta. "El emulador mas
# nuevo de las que tenes" nunca fue el criterio de nadie; fue el unico que se
# podia calcular sin esta hoja.
import csv
import io
import os
import re
import time
import unicodedata
import urllib.request

HOJA = '1-2OTotf1p2kz7DzfcxiY-iLWoqvl14wLn4sZ9uEjHsg'
URL = 'https://docs.google.com/spreadsheets/d/%s/export?format=csv' % HOJA
FUENTE = 'https://gbatemp.net/threads/new-wii-u-nds-injection-compatibility-list.605592/'

BASE_POR_DEFECTO = '[USA] New Super Mario Bros.'

CACHE = os.path.expanduser('~/.cache/nds2wiiu/compatibilidad-gbatemp.csv')
VIGENCIA = 7 * 24 * 3600

# Copia de respaldo versionada, para cuando no hay internet ni cache. La fuente
# es una hoja de calculo personal enlazada desde un hilo de foro: no tiene
# ninguna garantia de permanencia, y sin esta copia un clon nuevo sin red se
# queda sin la mejor fuente de datos del proyecto. Su procedencia y atribucion
# estan en datos/PROCEDENCIA.md.
#
# La fecha va acá y no en el mtime del archivo porque git no conserva fechas de
# modificacion: un clon las pone todas en el momento del clon.
RESPALDO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'datos', 'compatibilidad-gbatemp.csv')
RESPALDO_FECHA = '2026-11-12'
TIEMPO = 30
AGENTE = 'nds2wiiu/1.0'

# Los tres encabezados de seccion de la hoja, y como los traducimos a los
# resultados que ya usa el registro propio del proyecto.
SECCIONES = {
    'working:': 'funciona',
    'partially working:': 'con fallas',
    'not working:': 'no arranca',
}


class NoDisponible(Exception):
    """No se pudo traer la hoja: queda la busqueda y el registro propio."""


def _descargar():
    pedido = urllib.request.Request(URL, headers={'User-Agent': AGENTE})
    with urllib.request.urlopen(pedido, timeout=TIEMPO) as r:
        return r.read().decode('utf-8', 'replace')


def _leer(ruta):
    with io.open(ruta, encoding='utf-8') as f:
        return f.read()


def traer(refrescar=False, cache=CACHE):
    """Devuelve (csv, origen) con el origen de donde salio el dato.

    Cuatro niveles, de mas fresco a mas viejo:

      'cache'    bajada de hace menos de una semana. La hoja la edita gente a
                 mano cada tanto, no cambia por hora.
      'internet' recien bajada.
      'vieja'    la cache pasada de fecha, cuando la descarga falla.
      'respaldo' la copia incluida en el proyecto, cuando no hay nada mas.

    El origen se devuelve para poder decirselo a quien lee: una lista de hace
    meses puede estar bien o puede estar vieja, y eso no se puede adivinar.
    """
    if not refrescar and os.path.isfile(cache):
        if time.time() - os.path.getmtime(cache) < VIGENCIA:
            return _leer(cache), 'cache'
    try:
        texto = _descargar()
    except Exception as e:
        if os.path.isfile(cache):
            return _leer(cache), 'vieja'
        if os.path.isfile(RESPALDO):
            return _leer(RESPALDO), 'respaldo'
        raise NoDisponible('no se pudo bajar la lista: %s' % e)
    try:
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        with io.open(cache, 'w', encoding='utf-8') as f:
            f.write(texto)
    except OSError:
        pass                                 # sin cache tambien sirve
    return texto, 'internet'


def _normalizar(nombre):
    """Deja el nombre comparable: sin region, sin notas, sin puntuacion.

    La hoja escribe '[USA] Castlevania Portrait of Ruin (No Issues)' y el
    archivo de la ROM 'Castlevania - Portrait of Ruin (USA)'. Sin normalizar,
    dos nombres del mismo juego no se parecen en nada.
    """
    t = unicodedata.normalize('NFKD', nombre)
    t = ''.join(c for c in t if not unicodedata.combining(c)).lower()
    t = re.sub(r'\[[^\]]*\]', ' ', t)          # [USA], [EUR], [JPN], [Hack]
    t = re.sub(r'\([^\)]*\)', ' ', t)          # (No Issues), (USA), (En,Fr,...)
    t = re.sub(r'^\s*(the|a|an)\b', ' ', t)
    t = re.sub(r'\b(the|a|an|of|and)\b', ' ', t)
    t = re.sub(r'[^a-z0-9]+', ' ', t)
    return ' '.join(t.split())


def _region(nombre):
    m = re.search(r'\[(USA|EUR|JPN|JAP|AUS)\]', nombre, re.I)
    if m:
        return m.group(1).upper()
    m = re.search(r'\((USA|Europe|Japan|Australia|Spain|Italy)\)', nombre, re.I)
    if m:
        return {'usa': 'USA', 'europe': 'EUR', 'japan': 'JPN', 'australia': 'AUS',
                'spain': 'EUR', 'italy': 'EUR'}.get(m.group(1).lower())
    # Las colecciones viejas abrevian la region a una sola letra.
    m = re.search(r'\(([EUJ])\)', nombre)
    return {'E': 'EUR', 'U': 'USA', 'J': 'JPN'}.get(m.group(1)) if m else None


def filas(texto=None):
    """Parsea la hoja en entradas: nombre, estado, nota, base y region."""
    texto = traer()[0] if texto is None else texto
    estado = None
    salida = []
    for campos in csv.reader(io.StringIO(texto)):
        if not any(c.strip() for c in campos):
            continue
        primera = campos[0].strip()
        clave = primera.lower()
        if clave in SECCIONES:
            estado = SECCIONES[clave]
            continue
        if clave in ('game', '') or set(primera) <= set('-'):
            continue
        if estado is None:
            continue
        nota_hoja = campos[2].strip() if len(campos) > 2 else ''
        base = campos[3].strip() if len(campos) > 3 else ''
        parentesis = re.findall(r'\(([^\)]*)\)', primera)
        salida.append({
            'nombre': primera,
            'clave': _normalizar(primera),
            'region': _region(primera),
            'estado': estado,
            'nota': (parentesis[-1] if parentesis else '') or nota_hoja,
            'base': base or BASE_POR_DEFECTO,
            'base_explicita': bool(base),
        })
    return salida


def _limpiar_archivo(nombre):
    """Quita de un nombre de archivo lo que no es el titulo del juego.

    Las colecciones de ROMs vienen rotuladas de maneras muy distintas, y cada
    rotulo rompe la comparacion de una forma propia. Medido sobre una
    biblioteca real de 31 juegos: con solo quitar la extension coincidian 9;
    quitando tambien el numero de lanzamiento que muchas colecciones ponen
    adelante ('0881 - Castlevania...'), coinciden bastantes mas.
    """
    nombre = re.sub(r'\.(nds|srl|zip|7z)$', '', nombre.strip(), flags=re.I)
    nombre = re.sub(r'^\s*\d{3,5}\s*[-_.]\s*', '', nombre)
    return nombre.strip()


def estadisticas(entradas=None):
    """Cuantos juegos hay y cuantos usan la base por defecto.

    Se cuenta sobre la hoja en vez de dejar los numeros escritos en el codigo:
    la hoja la editan y los numeros de hoy no son los de dentro de un anio.
    """
    entradas = filas() if entradas is None else entradas
    return len(entradas), sum(1 for e in entradas if not e['base_explicita'])


def consultar(nombre_rom, entradas=None):
    """Busca ese juego en la hoja. Devuelve la lista de coincidencias.

    Primero por nombre normalizado exacto, y si no hay, por parecido. No se
    inventa nada: si no aparece, la lista vuelve vacia, que es un resultado.
    """
    entradas = filas() if entradas is None else entradas
    nombre_rom = _limpiar_archivo(nombre_rom)
    clave = _normalizar(nombre_rom)
    region = _region(nombre_rom)
    if not clave:
        return []

    exactas = [e for e in entradas if e['clave'] == clave]
    if not exactas:
        import difflib
        claves = {e['clave'] for e in entradas}
        parecidas = difflib.get_close_matches(clave, claves, n=3, cutoff=0.88)
        exactas = [e for e in entradas if e['clave'] in parecidas]

    # Con varias regiones del mismo juego, primero la del archivo que se tiene.
    exactas.sort(key=lambda e: (e['region'] != region, e['nombre']))
    return exactas
