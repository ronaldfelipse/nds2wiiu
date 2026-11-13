# Lectura y escritura del archivo de configuracion.
#
# Lo que se guarda son rutas y la direccion de la consola: nada secreto, pero
# el archivo se escribe con permisos restringidos igual, porque es el lugar
# natural donde alguien terminaria pegando algo que si lo es.
#
# Se guarda SOLO lo que falta. Nunca se pisa un valor que ya estaba: quien
# edito el archivo a mano tiene mas idea de lo que quiere que nosotros.
import configparser
import os

RUTA = os.path.expanduser('~/.config/nds2wiiu/config.ini')
SECCION = 'nds2wiiu'


def leer(ruta=RUTA):
    cfg = configparser.ConfigParser()
    if os.path.isfile(ruta):
        cfg.read(ruta, encoding='utf-8')
    return cfg[SECCION] if cfg.has_section(SECCION) else {}


def guardar_faltantes(valores, ruta=RUTA):
    """Agrega las claves que todavia no estan. Devuelve las que escribio."""
    cfg = configparser.ConfigParser()
    if os.path.isfile(ruta):
        cfg.read(ruta, encoding='utf-8')
    if not cfg.has_section(SECCION):
        cfg.add_section(SECCION)

    nuevas = []
    for clave, valor in sorted(valores.items()):
        if valor and not cfg.get(SECCION, clave, fallback=''):
            cfg.set(SECCION, clave, str(valor))
            nuevas.append(clave)
    if not nuevas:
        return []

    try:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, 'w', encoding='utf-8') as f:
            cfg.write(f)
        os.chmod(ruta, 0o600)
    except OSError:
        return []
    return nuevas
