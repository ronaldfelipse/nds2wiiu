# Obtencion y validacion de la clave comun de Wii U.
#
# Esa clave es la misma en todas las consolas y hace falta para cifrar el
# paquete final. No viene incluida en este proyecto a proposito: distribuir una
# clave de Nintendo en un repositorio publico es pedir que lo bajen. Se la
# pedimos al usuario, que la saca del volcado de su propia consola.
#
# La clave nunca se imprime ni se escribe en disco.
import os

OFFSET_EN_OTP = 0xE0
LARGO = 16

# Huella conocida de la clave correcta, para avisar enseguida cuando alguien
# apunta al archivo equivocado en vez de fallar diez minutos despues.
HUELLA_ESPERADA = -485504051


def _hash_determinista(texto):
    """Reproduce el hash de cadenas que usan las herramientas de este ambiente."""
    def i32(x):
        x &= 0xFFFFFFFF
        return x - 0x100000000 if x >= 0x80000000 else x

    h1 = i32((5381 << 16) + 5381)
    h2 = h1
    i = 0
    while i < len(texto):
        h1 = i32(i32((h1 << 5) + h1) ^ ord(texto[i]))
        if i == len(texto) - 1:
            break
        h2 = i32(i32((h2 << 5) + h2) ^ ord(texto[i + 1]))
        i += 2
    return i32(h1 + i32(h2 * 1566083941))


def valida(clave_hex):
    """Dice si la clave es la correcta, sin revelarla."""
    return _hash_determinista(clave_hex.lower()) == HUELLA_ESPERADA


def desde_otp(ruta):
    """Lee la clave comun del volcado otp.bin de una consola."""
    if not os.path.isfile(ruta):
        raise FileNotFoundError('no existe el volcado: %s' % ruta)
    with open(ruta, 'rb') as f:
        f.seek(OFFSET_EN_OTP)
        clave = f.read(LARGO)
    if len(clave) != LARGO:
        raise ValueError('%s no parece un otp.bin: es demasiado corto' % ruta)
    return clave.hex()


def obtener(otp=None, clave=None):
    """Devuelve la clave comun desde un otp.bin o desde el valor dado.

    Falla con un mensaje claro si no es la correcta, porque seguir adelante
    produciria un titulo que la consola rechaza sin decir por que.
    """
    if clave:
        valor = clave.strip().lower()
    elif otp:
        valor = desde_otp(otp)
    else:
        raise ValueError('hace falta --otp o --clave')
    if not valida(valor):
        raise ValueError('la clave comun no es la correcta: revisa el archivo '
                         'o el valor que pasaste')
    return valor
