# Lectura de la cabecera de una ROM de Nintendo DS.
#
# De aqui sale el codigo de juego de cuatro letras, que es lo que usamos para
# darle identidad propia al titulo inyectado y para buscarle arte. Se lee del
# archivo en vez de pedirselo al usuario: es un dato que ya esta ahi.
import os
import struct


def cabecera(ruta):
    """Devuelve lo que interesa de la cabecera de un .nds o .srl."""
    tam = os.path.getsize(ruta)
    with open(ruta, 'rb') as f:
        d = f.read(0x200)
    if len(d) < 0x200:
        raise ValueError('%s es demasiado chico para ser una ROM de DS' % ruta)

    titulo = d[0:12].decode('ascii', 'replace').rstrip('\x00 ')
    codigo = d[12:16].decode('ascii', 'replace')
    if not codigo.isalnum():
        raise ValueError('%s no parece una ROM de DS: el codigo de juego es ilegible' % ruta)

    return {
        'titulo_interno': titulo,
        'codigo': codigo,
        'fabricante': d[16:18].decode('ascii', 'replace'),
        'unidad': d[0x12],
        'usado': struct.unpack('<I', d[0x80:0x84])[0],
        'tamano': tam,
        'es_dsi': d[0x12] != 0,
    }
