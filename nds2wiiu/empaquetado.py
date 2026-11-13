# Empaquetado y cifrado del titulo, apoyandose en NUSPacker.
#
# NUSPacker no viene incluido: es de terceros y no declara licencia. El README
# explica de donde bajarlo. Se le pasa la clave comun por argumento, leida en el
# momento y sin dejarla escrita en ningun lado.
import os
import re
import subprocess

# NUSPacker imprime en su salida la clave comun que se le pasa, y tambien la
# clave con la que cifro el titulo. Medido: tres lineas del tipo
# "Encrypted with this key : <32 digitos>". Si esa salida se muestra o se
# guarda en un registro, la clave sale con ella, asi que se tacha antes de
# devolverla. Es lo unico secreto que este programa llega a tocar.
CLAVE = re.compile(r'\b[0-9A-Fa-f]{32}\b')


def _tachar(texto):
    return CLAVE.sub('<clave tachada>', texto)


def empaquetar(entrada, salida, jar, clave_comun):
    """Cifra la carpeta 'entrada' en 'salida'. Devuelve (codigo, texto)."""
    if not os.path.isfile(jar):
        raise FileNotFoundError(
            'falta NUSPacker.jar en %s (mira el README para conseguirlo)' % jar)
    if not os.path.isdir(entrada):
        raise NotADirectoryError('no existe la carpeta de entrada: %s' % entrada)

    cmd = ['java', '-jar', jar,
           '-in', entrada,
           '-out', salida,
           '-encryptKeyWith', clave_comun]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        raise RuntimeError('no se encontro java; hace falta tenerlo instalado')
    # cmd lleva la clave, y la salida de NUSPacker tambien: ninguna de las
    # dos sale de aqui.
    return p.returncode, _tachar(p.stdout + p.stderr)


def verificar(carpeta):
    """Comprueba que el paquete tenga las tres piezas que la consola espera."""
    faltan = [n for n in ('title.tmd', 'title.tik', 'title.cert')
              if not os.path.isfile(os.path.join(carpeta, n))]
    apps = [n for n in os.listdir(carpeta) if n.endswith('.app')]
    if faltan or not apps:
        return False, (faltan or ['ningun archivo .app'])
    return True, apps
