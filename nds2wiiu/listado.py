# Las listas de compatibilidad de la comunidad, consultadas de verdad.
#
# Durante un buen rato este proyecto dio por sentado que no existia ninguna
# tabla publica y consultable de que base conviene para cada juego de DS, y
# construyo todo alrededor de esa creencia: un registro propio, una heuristica
# de "el emulador mas nuevo" y, al final, una consulta a un modelo de lenguaje.
#
# Existen, y son DOS, mantenidas por gente distinta:
#
#   UWUVCI   un JSON en GitHub, con un campo por dato y actualizado seguido.
#            Cada entrada dice que base se uso de verdad.
#   GBAtemp  una hoja de calculo de Google enlazada desde un hilo de 2022.
#            Cubre mas juegos, pero 512 de sus 533 heredan la base de un
#            "salvo que se indique": son suposiciones, no reportes.
#
# Se usan las dos, y no una. Medido: solo 79 juegos estan en ambas, 454 solo
# en GBAtemp y 199 solo en UWUVCI. Quedarse con una sola —cualquiera— tiraba
# a la basura mas de lo que ganaba. Juntas cubren 732.
#
# Cuando las dos tienen el mismo juego gana UWUVCI, porque su dato es mejor:
# base y region en campos propios, notas aparte, y sin la errata de la hoja
# ("Yoshi Touich & Go") que ningun catalogo puede reconocer.
import csv
import io
import json
import os
import re
import time
import unicodedata
import urllib.request

TIEMPO = 30
AGENTE = 'nds2wiiu/1.0'
VIGENCIA = 7 * 24 * 3600
CACHE_DIR = os.path.expanduser('~/.cache/nds2wiiu')
DATOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     'datos')

# La fecha de las copias de respaldo va aca y no en el mtime de los archivos
# porque git no conserva fechas de modificacion: un clon las pone todas en el
# momento del clon.
RESPALDO_FECHA = '2026-11-13'

# Se mantiene para quien quiera citar una sola fuente; la de cada entrada esta
# en su campo 'fuente'.
FUENTE = 'https://github.com/UWUVCI-PRIME/UWUVCI-Compatibility'

# Lo que el sitio de UWUVCI muestra para cada status, leido de su propio
# codigo: status==2 -> working, ==1 -> issues, else -> broken.
ESTADOS_UWUVCI = {2: 'funciona', 1: 'con fallas', 0: 'no arranca'}

# Los tres encabezados de seccion de la hoja de GBAtemp.
SECCIONES = {
    'working:': 'funciona',
    'partially working:': 'con fallas',
    'not working:': 'no arranca',
}

# Lo que la hoja de GBAtemp aclara en su cabecera, y que vale solo para ella:
#   "Unless specified, Base Game (WUP) is always [USA] New Super Mario Bros."
BASE_POR_DEFECTO = '[USA] New Super Mario Bros.'


class NoDisponible(Exception):
    """No se pudo traer ninguna lista: quedan la busqueda y el registro propio."""


def _normalizar(nombre):
    """Deja el nombre comparable: sin region, sin notas, sin puntuacion.

    Una lista escribe '[USA] Castlevania Portrait of Ruin (No Issues)', la otra
    'Castlevania: Portrait of Ruin' y el archivo de la ROM
    'Castlevania - Portrait of Ruin (USA)'. Sin normalizar, tres nombres del
    mismo juego no se parecen en nada.
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


def _filas_uwuvci(texto):
    """Parsea el JSON de UWUVCI. Cada entrada ya trae base y region aparte."""
    datos = json.loads(texto).get('compatibility', [])
    salida = []
    for e in datos:
        nombre = (e.get('game_name') or '').strip()
        if not nombre:
            continue
        base = (e.get('base_name') or '').strip()
        region_base = (e.get('base_region') or '').strip().upper()
        nota = (e.get('notes') or '').strip()
        salida.append({
            'nombre': nombre,
            'clave': _normalizar(nombre),
            'region': (e.get('game_region') or '').strip().upper() or None,
            'estado': ESTADOS_UWUVCI.get(e.get('status'), 'sin probar'),
            'nota': '' if nota.lower() in ('', 'none') else nota,
            'base': ('[%s] %s' % (region_base, base)) if region_base else base,
            'base_explicita': bool(base),
            'fuente': 'UWUVCI',
        })
    return salida


def _filas_gbatemp(texto):
    """Parsea la hoja de GBAtemp, que es un CSV por secciones."""
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
        nota = (parentesis[-1] if parentesis else '') or nota_hoja
        salida.append({
            'nombre': primera,
            'clave': _normalizar(primera),
            'region': _region(primera),
            'estado': estado,
            'nota': '' if nota.lower() == 'no issues' else nota,
            'base': base or BASE_POR_DEFECTO,
            'base_explicita': bool(base),
            'fuente': 'GBAtemp',
        })
    return salida


# Orden de prioridad: la primera gana cuando las dos tienen el mismo juego.
FUENTES = (
    {
        'id': 'uwuvci',
        'nombre': 'UWUVCI',
        'url': 'https://raw.githubusercontent.com/UWUVCI-PRIME/'
               'UWUVCI-Compatibility/main/NDSCompat.json',
        'cache': os.path.join(CACHE_DIR, 'uwuvci-nds.json'),
        'respaldo': os.path.join(DATOS, 'compatibilidad-uwuvci.json'),
        'parser': _filas_uwuvci,
        'enlace': 'https://github.com/UWUVCI-PRIME/UWUVCI-Compatibility',
    },
    {
        'id': 'gbatemp',
        'nombre': 'GBAtemp',
        'url': 'https://docs.google.com/spreadsheets/d/'
               '1-2OTotf1p2kz7DzfcxiY-iLWoqvl14wLn4sZ9uEjHsg/export?format=csv',
        'cache': os.path.join(CACHE_DIR, 'compatibilidad-gbatemp.csv'),
        'respaldo': os.path.join(DATOS, 'compatibilidad-gbatemp.csv'),
        'parser': _filas_gbatemp,
        'enlace': 'https://gbatemp.net/threads/'
                  'new-wii-u-nds-injection-compatibility-list.605592/',
    },
)


def _leer(ruta):
    with io.open(ruta, encoding='utf-8') as f:
        return f.read()


def _traer_una(fuente, refrescar=False):
    """Devuelve (texto, origen) para una fuente. Cuatro niveles.

      'cache'    bajada hace menos de una semana. Estas listas las edita gente
                 a mano cada tanto, no cambian por hora.
      'internet' recien bajada.
      'vieja'    la cache pasada de fecha, cuando la descarga falla.
      'respaldo' la copia incluida en el proyecto, cuando no hay nada mas.

    El origen se devuelve para poder decirselo a quien lee: una lista de hace
    meses puede estar bien o puede estar vieja, y eso no se puede adivinar.
    """
    cache = fuente['cache']
    if not refrescar and os.path.isfile(cache):
        if time.time() - os.path.getmtime(cache) < VIGENCIA:
            return _leer(cache), 'cache'
    try:
        pedido = urllib.request.Request(fuente['url'], headers={'User-Agent': AGENTE})
        with urllib.request.urlopen(pedido, timeout=TIEMPO) as r:
            texto = r.read().decode('utf-8', 'replace')
    except Exception:
        if os.path.isfile(cache):
            return _leer(cache), 'vieja'
        if os.path.isfile(fuente['respaldo']):
            return _leer(fuente['respaldo']), 'respaldo'
        return None, 'no disponible'
    try:
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        with io.open(cache, 'w', encoding='utf-8') as f:
            f.write(texto)
    except OSError:
        pass                                   # sin cache tambien sirve
    return texto, 'internet'


def cargar(refrescar=False):
    """Trae y fusiona las dos listas. Devuelve (entradas, origenes).

    'origenes' es {nombre: origen} para poder avisar de donde salio cada una;
    si una falla se sigue con la otra, que es mejor que no tener nada.

    La fusion es por juego, no por entrada: si UWUVCI conoce ese juego, se usan
    SOLO sus entradas para el. Mezclar las dos para un mismo juego daria dos
    recomendaciones distintas sin forma de elegir entre ellas.
    """
    por_clave = {}
    origenes = {}
    for fuente in FUENTES:
        texto, origen = _traer_una(fuente, refrescar)
        origenes[fuente['nombre']] = origen
        if texto is None:
            continue
        try:
            entradas = fuente['parser'](texto)
        except Exception:
            origenes[fuente['nombre']] = 'ilegible'
            continue
        for e in entradas:
            if e['clave'] and e['clave'] not in por_clave:
                por_clave.setdefault(e['clave'], []).append(e)
            elif e['clave'] and por_clave[e['clave']][0]['fuente'] == e['fuente']:
                por_clave[e['clave']].append(e)

    if not por_clave and all(o in ('no disponible', 'ilegible')
                             for o in origenes.values()):
        raise NoDisponible('no se pudo traer ninguna lista de compatibilidad')

    salida = []
    for entradas in por_clave.values():
        salida.extend(entradas)
    return salida, origenes


def traer(refrescar=False):
    """Compatibilidad hacia atras: devuelve (entradas, origen_resumido)."""
    entradas, origenes = cargar(refrescar)
    viejas = [o for o in origenes.values() if o in ('vieja', 'respaldo')]
    return entradas, (viejas[0] if viejas and len(viejas) == len(origenes) else 'cache')


def filas(entradas=None):
    """Las entradas ya fusionadas. Acepta una lista ya cargada."""
    return cargar()[0] if entradas is None else entradas


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


def base_mas_usada(entradas=None):
    """La base que mas aparece, con cuantos juegos la usan y cuantos hay.

    Se cuenta sobre las listas en vez de dejar el numero escrito en el codigo:
    las listas se editan y los numeros de hoy no son los de dentro de un anio.

    Dos cuidados que cambian el resultado:

    Solo cuentan las entradas con base EXPLICITA. La hoja de GBAtemp le asigna
    "[USA] New Super Mario Bros." a todo lo que no diga otra cosa, asi que
    contando esas la respuesta seria esa base por construccion: 467 de 659, un
    71% que en realidad son suposiciones. Contando solo lo reportado da 65 de
    260, que es un dato y no un eco de la regla de la hoja.

    Y se cuenta por JUEGO, no por entrada, porque un juego con cinco bases
    probadas pesaria cinco veces.
    """
    entradas = filas() if entradas is None else entradas
    juegos = {}
    for e in entradas:
        if e['base_explicita'] and e['estado'] != 'no arranca' and e['base']:
            juegos.setdefault(e['clave'], set()).add(e['base'])
    cuenta = {}
    for bases in juegos.values():
        for b in bases:
            cuenta[b] = cuenta.get(b, 0) + 1
    if not cuenta:
        return BASE_POR_DEFECTO, 0, 0
    base = max(cuenta, key=lambda b: (cuenta[b], b))
    return base, cuenta[base], len(juegos)


def estadisticas(entradas=None):
    """Cuantos juegos distintos hay y cuantas entradas en total."""
    entradas = filas() if entradas is None else entradas
    return len({e['clave'] for e in entradas}), len(entradas)


def consultar(nombre_rom, entradas=None):
    """Busca ese juego en las listas. Devuelve la lista de coincidencias.

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

    # Primero lo que funciona, y dentro de eso la region del archivo que se
    # tiene: una entrada que dice "no arranca" no deberia encabezar la lista.
    orden = {'funciona': 0, 'con fallas': 1, 'sin probar': 2, 'no arranca': 3}
    exactas.sort(key=lambda e: (orden.get(e['estado'], 9),
                                e['region'] != region, e['nombre']))
    return exactas
