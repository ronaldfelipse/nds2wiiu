# Registro de que combinaciones de juego y base funcionan.
#
# No existe ninguna tabla publica y consultable que diga que base conviene para
# cada juego: lo que hay son hilos de foro y wikis que casi nadie mantiene. Asi
# que el proyecto arma la suya con lo que la gente prueba de verdad.
#
# El archivo se versiona junto al codigo, de modo que cada resultado que alguien
# aporta por pull request le sirve al siguiente.
import json
import os

ARCHIVO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'compatibilidad.json')

# Un resultado probado vale mas que una sugerencia sin confirmar; el orden de
# esta lista es el orden de confianza.
RESULTADOS = ['funciona', 'con fallas', 'no arranca', 'sin probar']


def cargar(ruta=ARCHIVO):
    if not os.path.isfile(ruta):
        return {}
    with open(ruta, encoding='utf-8') as f:
        return json.load(f)


def guardar(datos, ruta=ARCHIVO):
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(datos, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write('\n')


def consultar(codigo_juego, datos=None):
    """Devuelve lo anotado para ese juego, lo mejor primero."""
    datos = cargar() if datos is None else datos
    entradas = datos.get(codigo_juego.upper(), [])
    return sorted(entradas, key=lambda e: RESULTADOS.index(e.get('resultado', 'sin probar')))


def recomendar(codigo_juego, bases_disponibles, datos=None):
    """Elige una base entre las que el usuario tiene, y explica por que.

    Primero manda lo que ya se probo; si no hay nada anotado, se cae al unico
    criterio objetivo que queda: el emulador mas nuevo.
    """
    codigos = {b[1][-4:].upper(): b for b in bases_disponibles}
    for entrada in consultar(codigo_juego, datos):
        if entrada.get('resultado') != 'funciona':
            continue
        base = codigos.get(entrada.get('base', '').upper())
        if base:
            return base, 'anotada como funcional (%s)' % entrada.get('fuente', 'sin fuente')
    if bases_disponibles:
        return bases_disponibles[0], 'emulador mas nuevo de las que tenes'
    return None, 'no hay bases disponibles'


def anotar(codigo_juego, codigo_base, resultado, fuente='probado', nota='', ruta=ARCHIVO):
    """Agrega o actualiza un resultado. Devuelve el archivo completo."""
    if resultado not in RESULTADOS:
        raise ValueError('resultado debe ser uno de: %s' % ', '.join(RESULTADOS))
    datos = cargar(ruta)
    juego = codigo_juego.upper()
    base = codigo_base.upper()
    entradas = [e for e in datos.get(juego, []) if e.get('base', '').upper() != base]
    entradas.append({'base': base, 'resultado': resultado, 'fuente': fuente, 'nota': nota})
    datos[juego] = entradas
    guardar(datos, ruta)
    return datos
