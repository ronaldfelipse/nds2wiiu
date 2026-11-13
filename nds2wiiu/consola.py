# Dialogo con la consola por FTP.
#
# El complemento ftpiiu de Aroma entrega el contenido YA DESCIFRADO, asi que un
# titulo bajado de aqui sirve directamente como base de inyeccion: no hay que
# descargar nada de Nintendo ni manejar claves de titulo.
#
# El FTP solo esta disponible mientras la consola esta en su menu principal. Al
# abrir un juego el complemento se descarga de memoria y el puerto se cierra;
# eso es normal y no significa que la consola se haya colgado.
import html
import os
import re
from ftplib import FTP

PUERTO = 21
# Categoria de los titulos de Consola Virtual de DS instalados.
RUTA_TITULOS = '/storage_usb/usr/title/00050000'
RUTA_INSTALL = '/fs/vol/external01/install'
BLOQUE = 65536


def _conectar(ip, tiempo=60):
    f = FTP()
    f.connect(ip, PUERTO, timeout=tiempo)
    f.login()
    f.voidcmd('TYPE I')
    return f


def _listar(f, ruta):
    f.cwd(ruta)
    filas = []
    f.retrlines('LIST', filas.append)
    salida = []
    for r in filas:
        p = r.split(None, 8)
        if len(p) >= 9:
            salida.append((r[0] == 'd', p[8], int(p[4])))
    return salida


def _campo(texto, etiqueta):
    m = re.search(r'<%s[^>]*>(.*?)</%s>' % (etiqueta, etiqueta), texto, re.S)
    # Los meta.xml traen entidades XML en los nombres: "Mario &amp; Luigi".
    return html.unescape(m.group(1).strip()) if m else ''


def _tamano_emulador(f, tid):
    """Devuelve el tamanio del emulador de DS que lleva esa base.

    Cada titulo salio con la revision del emulador que existia en su fecha, asi
    que este numero distingue unas bases de otras: a mayor tamanio, mas nueva.
    Es un indicio, no una garantia, pero es el unico dato objetivo disponible
    sin instalar y probar.
    """
    try:
        for es_dir, nombre, tam in _listar(f, '%s/%s/code' % (RUTA_TITULOS, tid)):
            if not es_dir and nombre.endswith('.rpx'):
                return tam
    except Exception:
        pass
    return 0


def bases(ip):
    """Lista los titulos que pueden servir de base, de mas nueva a mas vieja.

    Cada entrada es (tid, codigo, nombre, tamanio_del_emulador).
    """
    import io
    f = _conectar(ip)
    encontrados = []
    try:
        for es_dir, tid, _t in _listar(f, RUTA_TITULOS):
            if not es_dir:
                continue
            buf = io.BytesIO()
            try:
                f.retrbinary('RETR %s/%s/meta/meta.xml' % (RUTA_TITULOS, tid), buf.write)
            except Exception:
                continue
            texto = buf.getvalue().decode('utf-8', 'replace')
            codigo = _campo(texto, 'product_code')
            # Los titulos de DS llevan una D en la quinta posicion del codigo.
            if re.match(r'WUP-N-D', codigo):
                encontrados.append((tid, codigo,
                                    _campo(texto, 'longname_en').replace('\n', ' '),
                                    _tamano_emulador(f, tid)))
    finally:
        f.quit()
    return sorted(encontrados, key=lambda x: (-x[3], x[2]))


def extraer(ip, tid, destino, aviso=None):
    """Baja un titulo completo de la consola y verifica cada archivo."""
    f = _conectar(ip)
    total = [0]

    def bajar(remoto, local):
        os.makedirs(local, exist_ok=True)
        for es_dir, nombre, tam in _listar(f, remoto):
            if es_dir:
                bajar(remoto + '/' + nombre, os.path.join(local, nombre))
                f.cwd(remoto)
                continue
            ruta = os.path.join(local, nombre)
            with open(ruta, 'wb') as s:
                f.retrbinary('RETR %s/%s' % (remoto, nombre), s.write, blocksize=BLOQUE)
            obtenido = os.path.getsize(ruta)
            if obtenido != tam:
                raise IOError('%s llego incompleto: %d de %d bytes' % (nombre, obtenido, tam))
            total[0] += obtenido
            if aviso:
                aviso(nombre, obtenido)

    try:
        bajar('%s/%s' % (RUTA_TITULOS, tid), destino)
    finally:
        f.quit()
    return total[0]


def subir(ip, carpeta, nombre_remoto, aviso=None):
    """Deja un titulo empaquetado en la carpeta install de la tarjeta.

    Solo escribe; nunca borra nada de la consola.
    """
    archivos = sorted(n for n in os.listdir(carpeta)
                      if os.path.isfile(os.path.join(carpeta, n)))
    if not archivos:
        raise ValueError('no hay archivos en %s' % carpeta)

    f = _conectar(ip)
    try:
        f.cwd(RUTA_INSTALL)
        try:
            f.mkd(nombre_remoto)
        except Exception:
            pass
        destino = RUTA_INSTALL + '/' + nombre_remoto
        f.cwd(destino)
        for n in archivos:
            local = os.path.join(carpeta, n)
            with open(local, 'rb') as e:
                f.storbinary('STOR %s' % n, e, blocksize=BLOQUE)
            esperado = os.path.getsize(local)
            obtenido = f.size(n)
            if obtenido != esperado:
                raise IOError('%s subio incompleto: %d de %d bytes' % (n, obtenido, esperado))
            if aviso:
                aviso(n, obtenido)
    finally:
        f.quit()
    return destino
