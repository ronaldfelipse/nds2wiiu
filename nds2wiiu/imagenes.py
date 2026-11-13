# Genera las imagenes de un titulo de Wii U: el icono del menu y las pantallas
# de arranque del TV y del GamePad.
#
# Los formatos salieron de medir los archivos de una base real, no de la
# documentacion. Son TGA sin comprimir, con las filas de abajo hacia arriba, y
# tres de ellos llevan cuatro bytes nulos de mas despues del pie estandar: sin
# esos cuatro bytes el tamanio no coincide con el de los originales.
import os
import struct

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

TIPO_SIN_COMPRIMIR = 2
PIE = b'\x00' * 8 + b'TRUEVISION-XFILE.\x00'

FUENTE = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

# (ancho, alto, bits, relleno extra tras el pie)
FORMATOS = {
    'iconTex.tga':     (128, 128, 32, 4),
    'bootTvTex.tga':   (1280, 720, 24, 4),
    'bootDrcTex.tga':  (854, 480, 24, 4),
    'bootLogoTex.tga': (170, 42, 32, 0),
}


def escribir_tga(ruta, imagen, bits, relleno):
    """Guarda la imagen como TGA sin comprimir, de abajo hacia arriba."""
    if bits == 32:
        imagen = imagen.convert('RGBA')
        canales = 4
        descriptor = 0x08
    else:
        imagen = imagen.convert('RGB')
        canales = 3
        descriptor = 0x00

    ancho, alto = imagen.size
    px = imagen.load()
    cuerpo = bytearray()
    for y in range(alto - 1, -1, -1):
        for x in range(ancho):
            if canales == 4:
                r, g, b, a = px[x, y]
                cuerpo += bytes((b, g, r, a))
            else:
                r, g, b = px[x, y]
                cuerpo += bytes((b, g, r))

    cabecera = struct.pack('<BBBHHBHHHHBB', 0, 0, TIPO_SIN_COMPRIMIR, 0, 0, 0,
                           0, 0, ancho, alto, bits, descriptor)
    with open(ruta, 'wb') as f:
        f.write(cabecera + bytes(cuerpo) + PIE + b'\x00' * relleno)
    return os.path.getsize(ruta)


def _degradado(ancho, alto, claro, oscuro):
    im = Image.new('RGB', (ancho, alto))
    d = ImageDraw.Draw(im)
    for y in range(alto):
        t = y / max(alto - 1, 1)
        d.line([(0, y), (ancho, y)],
               fill=tuple(int(claro[i] + (oscuro[i] - claro[i]) * t) for i in range(3)))
    return im


def _texto_centrado(im, texto, y, alto_fuente, color=(255, 255, 255)):
    d = ImageDraw.Draw(im)
    try:
        fuente = ImageFont.truetype(FUENTE, alto_fuente)
    except OSError:
        fuente = ImageFont.load_default()
    caja = d.textbbox((0, 0), texto, font=fuente)
    d.text(((im.width - (caja[2] - caja[0])) // 2 - caja[0], y), texto,
           font=fuente, fill=color)


def _escalar_a_alto(imagen, alto_destino):
    """Lleva la imagen a ese alto conservando la proporcion, agrandando si hace
    falta. No se usa thumbnail porque solo achica, y el arte de DS que hay
    disponible es mas chico que las pantallas de arranque."""
    factor = alto_destino / imagen.height
    return imagen.resize((max(1, round(imagen.width * factor)), alto_destino),
                         Image.LANCZOS)


def _quitar_bordes_muertos(imagen, umbral=18):
    """Recorta el marco casi negro que suele rodear al arte de GameTDB."""
    gris = imagen.convert('RGB').convert('L')
    caja = gris.point(lambda v: 255 if v > umbral else 0).getbbox()
    return imagen.crop(caja) if caja else imagen


def _recortar_rectangulo(imagen, ancho, alto):
    """Llena un rectangulo con la imagen, recortando lo que sobra."""
    factor = max(ancho / imagen.width, alto / imagen.height)
    escalada = imagen.resize((max(ancho, round(imagen.width * factor)),
                              max(alto, round(imagen.height * factor))), Image.LANCZOS)
    izq = (escalada.width - ancho) // 2
    arr = (escalada.height - alto) // 2
    return escalada.crop((izq, arr, izq + ancho, arr + alto))


def _recortar_cuadrado(imagen, lado):
    """Llena un cuadrado con la imagen, recortando lo que sobra del lado largo."""
    factor = max(lado / imagen.width, lado / imagen.height)
    escalada = imagen.resize((max(lado, round(imagen.width * factor)),
                              max(lado, round(imagen.height * factor))), Image.LANCZOS)
    izq = (escalada.width - lado) // 2
    arr = (escalada.height - lado) // 2
    return escalada.crop((izq, arr, izq + lado, arr + lado))


CLARO_VC = (0xfb, 0xfb, 0xfc)
OSCURO_VC = (0xd8, 0xdc, 0xe3)
TINTA_VC = (0x44, 0x4a, 0x55)


def _pantalla(ancho, alto, arte, nombre, claro=None, oscuro=None):
    """Compone la pantalla de arranque imitando la estetica de Consola Virtual.

    Las pantallas originales son claras y sobrias: fondo casi blanco, el arte
    del juego a un costado y el nombre al lado, en tinta oscura.

    Se probo antes un fondo oscuro con una copia desenfocada de la caratula, y
    al lado del original quedaba ruidoso: desenfocar un arte lleno de colores
    produce una mancha multicolor justo donde Nintendo deja espacio en blanco.
    """
    limpio = _quitar_bordes_muertos(arte).convert('RGB')
    fondo = _degradado(ancho, alto, CLARO_VC, OSCURO_VC)

    # El arte, a lo sumo al doble de su tamanio original, para no deshacerlo.
    alto_arte = min(int(alto * 0.62), limpio.height * 2)
    copia = _escalar_a_alto(limpio, alto_arte)
    x = int(ancho * 0.10)
    y = (alto - copia.height) // 2

    marco = 3
    sombra = Image.new('RGBA', (copia.width + 48, copia.height + 48), (0, 0, 0, 0))
    ImageDraw.Draw(sombra).rectangle(
        [24, 26, copia.width + 23, copia.height + 25], fill=(0, 0, 0, 90))
    sombra = sombra.filter(ImageFilter.GaussianBlur(radius=14))
    caja = (x - 24, y - 24, x + copia.width + 24, y + copia.height + 24)
    fondo.paste(Image.alpha_composite(
        fondo.crop(caja).convert('RGBA'), sombra).convert('RGB'), caja[:2])
    ImageDraw.Draw(fondo).rectangle(
        [x - marco, y - marco, x + copia.width + marco - 1, y + copia.height + marco - 1],
        fill=(255, 255, 255))
    fondo.paste(copia, (x, y))

    # El nombre a la derecha del arte, centrado en su mitad de la pantalla.
    izquierda = x + copia.width + int(ancho * 0.06)
    _texto_en_bloque(fondo, nombre, izquierda, ancho - int(ancho * 0.06),
                     max(16, int(alto * 0.062)), TINTA_VC)
    return fondo


def _texto_en_bloque(im, texto, x0, x1, alto_fuente, color):
    """Escribe el texto centrado en la franja entre x0 y x1, partiendo lineas."""
    d = ImageDraw.Draw(im)
    try:
        fuente = ImageFont.truetype(FUENTE, alto_fuente)
    except OSError:
        fuente = ImageFont.load_default()
    disponible = x1 - x0
    lineas, actual = [], ''
    for palabra in texto.split():
        prueba = (actual + ' ' + palabra).strip()
        if d.textlength(prueba, font=fuente) <= disponible or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)

    paso = int(alto_fuente * 1.25)
    y = (im.height - paso * len(lineas)) // 2
    for linea in lineas:
        ancho_linea = d.textlength(linea, font=fuente)
        d.text((x0 + (disponible - ancho_linea) / 2, y), linea, font=fuente, fill=color)
        y += paso


def generar(carpeta_meta, arte_icono, arte_caja, nombre,
            claro=(0x3a, 0x3f, 0x4c), oscuro=(0x10, 0x12, 0x18)):
    """Escribe las cuatro imagenes del titulo en 'carpeta_meta'."""
    icono_fuente = Image.open(arte_icono).convert('RGBA')
    caja_fuente = Image.open(arte_caja).convert('RGBA')
    resultados = {}

    # Icono: si la fuente ya viene en la medida exacta es arte hecho para esto,
    # asi que se usa tal cual. Si no, la portada entra ENTERA con un margen.
    #
    # Se probo recortarla para que llenara el cuadro y queda mal: el arte de
    # caratula suele incluir el estuche, y al recortarlo se corta por la mitad y
    # parece que se desborda del icono. Los iconos originales de Nintendo
    # tambien dejan margen.
    ancho, alto, bits, relleno = FORMATOS['iconTex.tga']
    if icono_fuente.size == (ancho, alto):
        icono = icono_fuente
    else:
        icono = _degradado(ancho, alto, claro, oscuro).convert('RGBA')
        arte = _quitar_bordes_muertos(icono_fuente)
        arte.thumbnail((ancho - 12, alto - 12), Image.LANCZOS)
        icono.alpha_composite(arte, ((ancho - arte.width) // 2,
                                     (alto - arte.height) // 2))
    resultados['iconTex.tga'] = escribir_tga(
        os.path.join(carpeta_meta, 'iconTex.tga'), icono, bits, relleno)

    # Lo mismo con las pantallas: una imagen que ya mide 1280x720 se respeta, y
    # la del GamePad se saca de ella reduciendola.
    completa = caja_fuente if caja_fuente.size == FORMATOS['bootTvTex.tga'][:2] else None
    for archivo in ('bootTvTex.tga', 'bootDrcTex.tga'):
        ancho, alto, bits, relleno = FORMATOS[archivo]
        if completa is not None:
            imagen = completa if completa.size == (ancho, alto) else \
                _recortar_rectangulo(completa.convert('RGB'), ancho, alto)
        else:
            imagen = _pantalla(ancho, alto, caja_fuente, nombre, claro, oscuro)
        resultados[archivo] = escribir_tga(
            os.path.join(carpeta_meta, archivo), imagen, bits, relleno)

    # bootLogoTex.tga NO se toca: es el logotipo de Nintendo que el sistema
    # dibuja en una esquina al arrancar, no un lugar para el nombre del juego.
    # Escribir texto ahi, en 170x42, da un borron ilegible en pantalla.
    return resultados
