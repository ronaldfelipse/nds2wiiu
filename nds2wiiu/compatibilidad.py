# Registro propio de que combinaciones de juego y base funcionan.
#
# Este modulo nacio de una creencia equivocada: que no existia ninguna tabla
# publica y consultable de bases para DS. Existe, la mantiene la comunidad en
# una hoja de calculo, y la lee listado.py. Pero cubre 539 juegos de los mas de
# mil quinientos que salieron para DS, asi que este registro sigue haciendo
# falta para todo lo que no figura ahi.
#
# El archivo se versiona junto al codigo, de modo que cada resultado que alguien
# aporta por pull request le sirve al siguiente. Lo anotado aca manda sobre la
# heuristica del emulador mas nuevo; la hoja de la comunidad manda sobre las dos.
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


def recomendar_base(codigo_juego, en_lista, datos=None):
    """Que base conviene, sin mirar que tiene instalado nadie.

    Devuelve (base, motivo). La base es un nombre tal como lo escribe la hoja
    ("[USA] New Super Mario Bros.") o un codigo de producto de cuatro letras si
    sale del registro propio, que es como se anota ahi.

    Tres niveles:
      1. lo que alguien probo y anoto para ESE juego
      2. lo que dicen las listas de la comunidad para ESE juego
      3. la base mas reportada del conjunto, que es una apuesta y se dice

    Antes esta decision dependia de la lista de bases instaladas en la consola,
    lo que obligaba a tener la consola encendida y en su menu principal solo
    para preguntar que base conviene. La pregunta no necesita la consola.
    """
    from nds2wiiu import listado

    for entrada in consultar(codigo_juego, datos):
        if entrada.get('resultado') == 'funciona':
            return entrada['base'], 'probada y anotada para este juego'

    for c in en_lista:
        if c.get('estado') != 'no arranca':
            return c['base'], 'la que usa la lista de la comunidad para este juego'

    base, cuantos, total = listado.base_mas_usada()
    return (base, 'la base mas reportada de las listas: %d de %d juegos'
                  % (cuantos, total))


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
