# El camino sin FTP: bases ya volcadas en una carpeta, y el paquete escrito en
# una tarjeta montada en la PC.
#
# Por que existe este modulo: la base NO esta en la tarjeta SD. Vive en el
# disco USB o en la memoria interna de la consola, y las dos estan cifradas y
# atadas a esa consola: enchufar el disco a una PC no sirve. El FTP de Aroma
# funciona porque no lee el disco crudo, pasa por la capa de archivos del
# sistema, que descifra al vuelo.
#
# Quien no pueda usar el FTP tiene que volcar el titulo descifrado DESDE la
# consola con un volcador homebrew (Dumpling es el que usa la gente), que lo
# escribe en la tarjeta. De ahi en adelante todo es local, y es lo que este
# modulo cubre.
import html
import os
import re
import shutil

# Los titulos de DS llevan 'WUP-N-D' en su codigo de producto.
PATRON_DS = r'WUP-N-D'
HONDURA = 4


def campo_meta(texto, etiqueta):
    """Saca un campo de un meta.xml.

    Los meta.xml traen entidades XML en los nombres: "Mario &amp; Luigi".
    """
    m = re.search(r'<%s[^>]*>(.*?)</%s>' % (etiqueta, etiqueta), texto, re.S)
    return html.unescape(m.group(1).strip()) if m else ''


def _tamano_emulador(carpeta):
    """El tamanio del .rpx, que es el emulador de DS que lleva esa base.

    Cada titulo salio con la revision del emulador que existia en su fecha, asi
    que este numero distingue unas bases de otras. Es un indicio, no una
    garantia, pero es el unico dato objetivo que hay sin instalar y probar.
    """
    code = os.path.join(carpeta, 'code')
    try:
        for n in os.listdir(code):
            if n.lower().endswith('.rpx'):
                return os.path.getsize(os.path.join(code, n))
    except OSError:
        pass
    return 0


def bases(carpeta):
    """Busca bases de DS en una carpeta y las devuelve de mas nueva a mas vieja.

    Cada entrada es (ruta, codigo, nombre, tamanio_del_emulador), la misma
    forma que devuelve consola.bases(), para que la recomendacion no tenga que
    saber de donde salio la lista.

    Se recorre en profundidad en vez de asumir una estructura: cada volcador
    arma las carpetas a su manera, y lo unico seguro es que un titulo tiene su
    meta/meta.xml adentro.
    """
    carpeta = os.path.abspath(os.path.expanduser(carpeta))
    if not os.path.isdir(carpeta):
        raise ValueError('%s no es una carpeta' % carpeta)

    encontrados = []
    for raiz, dirs, _archivos in os.walk(carpeta):
        if raiz[len(carpeta):].count(os.sep) >= HONDURA:
            dirs[:] = []
            continue
        meta = os.path.join(raiz, 'meta', 'meta.xml')
        if not os.path.isfile(meta):
            continue
        dirs[:] = []                 # un titulo no contiene otro titulo
        try:
            with open(meta, encoding='utf-8', errors='replace') as f:
                texto = f.read()
        except OSError:
            continue
        codigo = campo_meta(texto, 'product_code')
        if not re.match(PATRON_DS, codigo):
            continue
        encontrados.append((raiz, codigo,
                            campo_meta(texto, 'longname_en').replace('\n', ' '),
                            _tamano_emulador(raiz)))
    return sorted(encontrados, key=lambda x: (-x[3], x[2]))


# FAT32 no admite estos caracteres en un nombre de archivo, y la tarjeta de la
# Wii U es FAT32 siempre. Un nombre como "Mario & Luigi: Partners in Time"
# llegaba hasta aca —con el paquete ya armado y cifrado— y recien entonces
# fallaba la copia, sin decir por que.
PROHIBIDOS = r'\/:*?"<>|'


def nombre_de_carpeta(nombre, largo_max=100):
    """Deja un nombre que FAT32 acepte, lo mas parecido posible al original.

    Se reemplaza en vez de borrar: "Mario & Luigi: Partners in Time" queda
    como "Mario & Luigi - Partners in Time" y no como "Mario & Luigi Partners
    in Time", que se lee peor.
    """
    limpio = ''.join('-' if c in PROHIBIDOS else c
                     for c in nombre if ord(c) >= 32)
    limpio = ' '.join(limpio.split()).strip(' .')
    return limpio[:largo_max].strip(' .-') or 'sin nombre'


def copiar(carpeta, destino_raiz, nombre, aviso=None):
    """Copia el paquete a una tarjeta montada, verificando cada archivo.

    Solo escribe; nunca borra nada. Es el equivalente de consola.subir() para
    quien no usa FTP, y hace la misma comprobacion de tamanio archivo por
    archivo: una tarjeta que se llena a mitad de camino deja un paquete
    truncado que el instalador rechaza sin explicar por que.
    """
    archivos = sorted(n for n in os.listdir(carpeta)
                      if os.path.isfile(os.path.join(carpeta, n)))
    if not archivos:
        raise ValueError('no hay archivos en %s' % carpeta)

    destino_raiz = os.path.abspath(os.path.expanduser(destino_raiz))
    if not os.path.isdir(destino_raiz):
        raise ValueError('%s no existe; monta la tarjeta primero' % destino_raiz)

    # Se limpia aca y no en quien llama, para que no dependa de que se acuerde.
    destino = os.path.join(destino_raiz, nombre_de_carpeta(nombre))
    os.makedirs(destino, exist_ok=True)
    for n in archivos:
        origen = os.path.join(carpeta, n)
        copia = os.path.join(destino, n)
        shutil.copyfile(origen, copia)
        esperado = os.path.getsize(origen)
        obtenido = os.path.getsize(copia)
        if obtenido != esperado:
            raise IOError('%s se copio incompleto: %d de %d bytes'
                          % (n, obtenido, esperado))
        if aviso:
            aviso(n, obtenido)
    return destino
