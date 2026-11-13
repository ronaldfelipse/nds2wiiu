# Busca en foros con que base inyecto otra gente un juego de DS.
#
# Aca no hay ningun modelo de lenguaje, y hubo dos antes. Vale la pena contar
# por que se fueron, porque es el tipo de pieza que se agrega sin pensarla.
#
# Primero hubo una consulta a un modelo con acceso a internet, que buscaba por
# su cuenta. Eso obligaba a un modelo de pago, y exigia que la respuesta citara
# una direccion web... comprobando solo que TUVIERA FORMA de direccion: un
# modelo sin buscador podia escribir una inexistente y pasar el filtro.
#
# Despues se paso el reparto de tareas al de la herramienta de traduccion de
# ROMs de la que salio esta idea: busca el programa, el modelo solo lee y
# elige. Mejor, y suficiente para que alcanzara un modelo gratuito.
#
# Pero medido sobre el unico caso real que habia a mano, el modelo aporto cero:
# leyo tres paginas y contesto "no hay informacion sobre este juego", que es lo
# mismo que ve cualquiera que abra esas paginas. Y para eso no hace falta una
# clave, una cuota diaria ni una dependencia mas.
#
# Asi que lo que queda es lo que de verdad servia: buscar, abrir las paginas y
# mostrar los fragmentos donde se nombra el juego. Quien decide es la persona.
import html
import os
import re
import unicodedata
import urllib.request

# Un nombre de agente generico: no lleva nada del usuario ni de su equipo.
AGENTE = 'nds2wiiu/1.0'
TIEMPO_PAGINA = 20
LARGO_PAGINA = 40000
PAGINAS = 4
CONTEXTO = 260


class SinRespuesta(Exception):
    """No se encontro nada, o no se pudo buscar: es un resultado, no un error."""


def termino(nombre_archivo):
    """El nombre del juego para buscarlo, que es el mismo que se muestra."""
    from nds2wiiu import rom
    return rom.nombre_legible(nombre_archivo)


def _corto(nombre):
    """La parte del nombre antes del subtitulo.

    Medido: con el titulo completo de Narnia el buscador devolvio una sola
    pagina, la de Wikipedia; recortado al nombre de la saga, el primer
    resultado fue el hilo de la lista de compatibilidad. Un titulo largo
    sobre-especifica la consulta.
    """
    for corte in (' - ', ': '):
        if corte in nombre:
            return nombre.split(corte)[0].strip()
    return nombre


def busca_web(nombre, max_resultados=8):
    """Devuelve resultados de buscador para ese juego. Lista vacia si no hay.

    ddgs reparte la consulta entre varios buscadores, asi que no depende de
    que uno solo conteste. No pide clave ni cuesta nada.

    Se tiran dos consultas, la del nombre completo y la del nombre recortado,
    y se juntan sin repetir: cada una trae resultados que la otra no.
    """
    try:
        from ddgs import DDGS
    except ImportError:
        raise SinRespuesta('falta la biblioteca ddgs: pip install ddgs')

    consultas = ['%s nds wii u virtual console inject base' % nombre]
    corto = _corto(nombre)
    if corto != nombre:
        consultas.append('%s nds wii u inject base' % corto)

    juntos, vistas, fallos = [], set(), []
    for consulta in consultas:
        try:
            encontrados = DDGS().text(consulta, max_results=max_resultados,
                                      region='us-en')
        except Exception as e:
            fallos.append(str(e))
            continue
        for r in encontrados:
            direccion = r.get('href')
            if direccion and direccion not in vistas:
                vistas.add(direccion)
                juntos.append(r)
    if not juntos and fallos:
        raise SinRespuesta('la busqueda fallo: %s' % fallos[0])
    return juntos


def _a_texto(crudo):
    """Saca el texto de una pagina sin traer otra dependencia.

    No pretende entender HTML: quita lo que nunca es texto visible, borra las
    etiquetas y junta los espacios. Para leer un hilo de foro alcanza.
    """
    t = crudo.decode('utf-8', 'replace')
    t = re.sub(r'(?is)<(script|style|head|nav|footer)[^>]*>.*?</\1>', ' ', t)
    t = re.sub(r'(?s)<[^>]+>', ' ', t)
    return re.sub(r'\s+', ' ', html.unescape(t)).strip()


def explora(resultados, tope=PAGINAS, avisar=None):
    """Abre las primeras paginas y devuelve (direccion, titulo, texto).

    Lo que no se pueda abrir se saltea quedandose con el fragmento que ya
    habia dado el buscador: algunos foros rechazan a quien no es un navegador.
    """
    fuentes = []
    for r in resultados[:tope]:
        direccion = r.get('href') or ''
        if not direccion.startswith('http'):
            continue
        if avisar:
            avisar(direccion)
        try:
            pedido = urllib.request.Request(
                direccion, headers={'User-Agent': AGENTE})
            with urllib.request.urlopen(pedido, timeout=TIEMPO_PAGINA) as f:
                texto = _a_texto(f.read(500000))
        except Exception:
            texto = r.get('body') or ''
        if texto:
            fuentes.append((direccion, r.get('title') or '', texto[:LARGO_PAGINA]))
    return fuentes


def _sin_acentos(t):
    t = unicodedata.normalize('NFKD', t)
    return ''.join(c for c in t if not unicodedata.combining(c)).lower()


def menciones(nombre, fuentes, contexto=CONTEXTO):
    """Devuelve los fragmentos de esas paginas donde se nombra el juego.

    Es deliberadamente tonto: busca el nombre, y si no esta, el nombre
    recortado. Lo que devuelve es texto que alguien escribio, no una
    conclusion. Quien decide que base usar es la persona que lo lee.
    """
    salida = []
    for direccion, titulo, texto in fuentes:
        plano = _sin_acentos(texto)
        # Que la pagina nombre el juego no alcanza: la ficha de Wikipedia de
        # la pelicula de Narnia lo nombra veinte veces y no dice nada de
        # inyecciones. Tiene que hablar del tema, no solo del juego.
        if 'inject' not in plano:
            continue
        for aguja in (nombre, _corto(nombre)):
            aguja = _sin_acentos(aguja)
            if len(aguja) < 4:
                continue
            posiciones = [m.start() for m in re.finditer(re.escape(aguja), plano)]
            if not posiciones:
                continue
            for p in posiciones[:3]:
                ini = max(0, p - contexto // 2)
                salida.append((direccion, titulo,
                               texto[ini:ini + contexto].strip()))
            break
    return salida
