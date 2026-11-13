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


def _pantalla(ancho, alto, arte, nombre, claro, oscuro):
    """Compone la pantalla de arranque a partir de una caratula chica.

    El arte de DS que hay disponible ronda los 240 pixeles de lado, y estirarlo
    a 1280x720 se ve borroso. Por eso el arte se queda a un tamanio modesto y el
    resto de la pantalla lo llena una copia enorme y desenfocada de la misma
    imagen: el color ocupa el cuadro sin que se note la falta de resolucion.
    """
    limpio = _quitar_bordes_muertos(arte).convert('RGB')

    fondo = _recortar_rectangulo(limpio, ancho, alto)
    fondo = fondo.filter(ImageFilter.GaussianBlur(radius=max(12, alto // 18)))
    fondo = ImageEnhance.Brightness(fondo).enhance(0.38)
    fondo = Image.blend(fondo, _degradado(ancho, alto, claro, oscuro), 0.45)

    # El arte, a lo sumo al doble de su tamanio original, para no deshacerlo.
    alto_arte = min(int(alto * 0.52), limpio.height * 2)
    copia = _escalar_a_alto(limpio, alto_arte)
    x = (ancho - copia.width) // 2
    y = int(alto * 0.16)

    sombra = Image.new('RGBA', (copia.width + 40, copia.height + 40), (0, 0, 0, 0))
    ImageDraw.Draw(sombra).rectangle([20, 20, copia.width + 19, copia.height + 19],
                                     fill=(0, 0, 0, 170))
    sombra = sombra.filter(ImageFilter.GaussianBlur(radius=12))
    fondo.paste(Image.alpha_composite(
        fondo.crop((x - 20, y - 20, x + copia.width + 20, y + copia.height + 20))
             .convert('RGBA'), sombra).convert('RGB'), (x - 20, y - 20))
    fondo.paste(copia, (x, y))

    _texto_centrado(fondo, nombre, y + copia.height + int(alto * 0.07),
                    max(14, int(alto * 0.058)))
    return fondo


def generar(carpeta_meta, arte_icono, arte_caja, nombre,
            claro=(0x3a, 0x3f, 0x4c), oscuro=(0x10, 0x12, 0x18)):
    """Escribe las cuatro imagenes del titulo en 'carpeta_meta'."""
    icono_fuente = Image.open(arte_icono).convert('RGBA')
    caja_fuente = Image.open(arte_caja).convert('RGBA')
    resultados = {}

    # Icono: si la fuente ya viene en la medida exacta es arte hecho para esto,
    # asi que se usa tal cual. Si no, la portada llena el cuadro recortando lo
    # que sobra, para que no queden franjas vacias en el menu.
    ancho, alto, bits, relleno = FORMATOS['iconTex.tga']
    if icono_fuente.size == (ancho, alto):
        icono = icono_fuente
    else:
        icono = _degradado(ancho, alto, claro, oscuro).convert('RGBA')
        icono.alpha_composite(
            _recortar_cuadrado(_quitar_bordes_muertos(icono_fuente), ancho), (0, 0))
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

    # Logotipo: solo el nombre, que es para lo que lo usa el sistema.
    ancho, alto, bits, relleno = FORMATOS['bootLogoTex.tga']
    logo = Image.new('RGBA', (ancho, alto), (0, 0, 0, 0))
    _texto_centrado(logo, nombre[:18], 6, 20)
    resultados['bootLogoTex.tga'] = escribir_tga(
        os.path.join(carpeta_meta, 'bootLogoTex.tga'), logo, bits, relleno)

    return resultados
