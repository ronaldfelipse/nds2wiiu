# Consulta opcional a un modelo con acceso a internet, para cuando no hay nada
# anotado todavia sobre un juego.
#
# Por que con tanto cuidado: esta pregunta TIENE FORMA DE TENER RESPUESTA, y un
# modelo al que se le pregunta "que base conviene" casi nunca contesta "no se";
# produce algo que suena bien. Y el error es silencioso y caro: empaquetar,
# instalar y probar lleva veinte minutos, y si falla no se sabe si fue la base
# o el juego.
#
# De ahi las tres reglas que impone este modulo:
#   1. Sin una fuente citada, la respuesta se descarta.
#   2. "No encontre nada" es una respuesta valida y esperada, no un fallo.
#   3. Lo que diga entra al registro como 'sin probar', nunca como 'funciona'.
import json
import re
import urllib.request

URL = 'https://openrouter.ai/api/v1/chat/completions'
MODELO = 'perplexity/sonar'
TIEMPO = 90

INSTRUCCIONES = """Sos un asistente que ayuda a elegir la base para inyectar un
juego de Nintendo DS en un titulo de Consola Virtual de Wii U.

Buscá en internet si alguien reporto haber inyectado ese juego y con que base lo
hizo. Las bases se identifican por su codigo de producto de cuatro letras.

Respondé UNICAMENTE con un objeto JSON con estas claves:
  "base"      el codigo de cuatro letras, o null si no encontraste nada
  "motivo"    una frase corta explicando por que
  "fuente"    la direccion web exacta donde lo leiste, o null
  "confianza" "alta", "media" o "baja"

Reglas que no podes romper:
- Si no encontraste informacion concreta sobre ESE juego, poné base en null.
  No inventes ni deduzcas por parecido con otros juegos.
- Si pones una base, "fuente" tiene que ser una direccion web real donde
  aparezca esa informacion. Sin fuente, poné base en null.
- No expliques nada fuera del JSON."""


class SinRespuesta(Exception):
    """El modelo no supo, o no cito fuente: no es un error, es un resultado."""


def _pedir(clave, modelo, mensaje):
    cuerpo = json.dumps({
        'model': modelo,
        'messages': [{'role': 'system', 'content': INSTRUCCIONES},
                     {'role': 'user', 'content': mensaje}],
        'temperature': 0,
    }).encode('utf-8')
    pedido = urllib.request.Request(URL, data=cuerpo, headers={
        'Authorization': 'Bearer %s' % clave,
        'Content-Type': 'application/json',
    })
    with urllib.request.urlopen(pedido, timeout=TIEMPO) as r:
        return json.load(r)


def consultar(codigo, nombre, bases_disponibles, clave, modelo=MODELO):
    """Pregunta que base conviene. Devuelve un dict o levanta SinRespuesta."""
    if not clave:
        raise SinRespuesta('no hay clave de OpenRouter configurada')

    codigos = ', '.join(b[1][-4:] for b in bases_disponibles) or 'ninguna'
    mensaje = ('Juego de Nintendo DS: "%s", codigo %s.\n'
               'Bases que tiene el usuario: %s.\n'
               'Que base conviene para inyectarlo en Wii U?' % (nombre, codigo, codigos))

    try:
        respuesta = _pedir(clave, modelo, mensaje)
    except Exception as e:
        raise SinRespuesta('no se pudo consultar: %s' % e)

    try:
        texto = respuesta['choices'][0]['message']['content']
    except (KeyError, IndexError):
        raise SinRespuesta('la respuesta vino con una forma inesperada')

    m = re.search(r'\{.*\}', texto, re.S)
    if not m:
        raise SinRespuesta('el modelo no devolvio JSON')
    try:
        datos = json.loads(m.group())
    except ValueError:
        raise SinRespuesta('el JSON del modelo no se pudo leer')

    base = (datos.get('base') or '').strip().upper()
    fuente = (datos.get('fuente') or '').strip()

    if not base:
        raise SinRespuesta(datos.get('motivo') or 'no encontro informacion sobre ese juego')
    # Regla 1: sin fuente citada, la respuesta no vale. Da igual lo convincente
    # que suene; es justamente cuando suena bien que conviene desconfiar.
    if not re.match(r'https?://', fuente):
        raise SinRespuesta('propuso %s pero no cito ninguna fuente' % base)
    if not re.fullmatch(r'[A-Z0-9]{4}', base):
        raise SinRespuesta('devolvio un codigo de base con forma rara: %r' % base)

    return {'base': base,
            'motivo': (datos.get('motivo') or '').strip(),
            'fuente': fuente,
            'confianza': (datos.get('confianza') or 'baja').strip().lower()}
