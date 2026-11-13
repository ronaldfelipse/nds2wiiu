# Los 93 titulos de Consola Virtual de DS que salieron para Wii U: 31 juegos en
# tres regiones, con su identificador de titulo y su codigo de producto.
#
# Existe para evitar una confusion concreta y costosa: la lista de
# compatibilidad recomienda una base por su NOMBRE —"[USA] New Super Mario
# Bros."— y hay juegos de Wii, de Wii U y remakes que se llaman casi igual.
# Buscar ese nombre sin mas lleva al archivo equivocado, y el error recien se
# descubre despues de empaquetar, instalar y probar.
#
# Con esta tabla la recomendacion puede decir ademas cual es el identificador
# exacto, que es un dato que no se parece a ningun otro.
#
# Son identificadores publicos, no claves: no sirven para descargar ni
# descifrar nada. Procedencia y atribucion en datos/PROCEDENCIA.md.
import json
import os
import re

ARCHIVO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'datos', 'bases-ds.json')

_cache = None


def cargar(ruta=ARCHIVO):
    global _cache
    if _cache is None:
        if not os.path.isfile(ruta):
            _cache = []
        else:
            with open(ruta, encoding='utf-8') as f:
                _cache = json.load(f)
    return _cache


def _normalizar(nombre):
    from nds2wiiu import listado
    return listado._normalizar(nombre)


def _claves(nombre):
    """Los nombres por los que se puede reconocer una entrada.

    Las entradas japonesas traen el titulo en japones y el ingles entre
    parentesis; la normalizacion quita los parentesis, asi que se guarda
    tambien lo que habia adentro.
    """
    claves = {_normalizar(nombre)}
    for dentro in re.findall(r'\(([^)]*)\)', nombre):
        claves.add(_normalizar(dentro))
    return {c for c in claves if c}


def por_codigo(codigo):
    """Busca por codigo de producto completo o por sus ultimas cuatro letras."""
    codigo = (codigo or '').upper()
    corto = codigo[-4:]
    for e in cargar():
        if e['codigo'].upper() == codigo or e['codigo'].upper().endswith(corto):
            return e
    return None


def buscar(nombre):
    """Busca por un nombre como lo escribe la hoja: "[USA] New Super Mario Bros."

    Devuelve la entrada, o None si no se reconoce. Nunca adivina: si el nombre
    no coincide con ninguno de los 93, no hay respuesta, que es mejor que una
    respuesta parecida.
    """
    if not nombre:
        return None
    m = re.search(r'\[(USA|EUR|JPN|JAP|US|EU|JP)\]', nombre, re.I)
    region = {'US': 'USA', 'EU': 'EUR', 'JP': 'JPN',
              'JAP': 'JPN'}.get((m.group(1).upper() if m else ''), m.group(1).upper() if m else '')
    clave = _normalizar(nombre)
    if not clave:
        return None

    candidatos = [e for e in cargar() if clave in _claves(e['nombre'])]
    if not candidatos:
        return None
    if region:
        de_region = [e for e in candidatos if e['region'] == region]
        if de_region:
            return de_region[0]

    # Sin region pedida se prefiere la occidental. Devolver "la primera del
    # archivo" entregaba la japonesa, porque es la que viene antes en el
    # catalogo: para "New Super Mario Bros." contestaba el titulo JPN, que no
    # es el que busca nadie que escriba el nombre en ingles.
    for preferida in ('USA', 'EUR', 'JPN'):
        for e in candidatos:
            if e['region'] == preferida:
                return e
    return candidatos[0]


def describir(nombre_o_codigo):
    """Una linea con el identificador exacto, o cadena vacia si no se reconoce."""
    e = buscar(nombre_o_codigo)
    if e is None and re.fullmatch(r'[A-Z0-9]{4}', (nombre_o_codigo or '').upper()):
        e = por_codigo(nombre_o_codigo)
    if e is None:
        return ''
    return 'title ID %s   %s   %s' % (e['title_id'], e['codigo'], e['region'])
