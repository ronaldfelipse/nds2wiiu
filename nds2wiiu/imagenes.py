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
            claro=(0x3a, 0x3f, 0x4c), oscuro=(0x10, 0x12, 0x18),
            anio=0, jugadores=0, idioma=None, marco_icono=False):
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
    conplantilla = None if icono_fuente.size == (ancho, alto) else \
        icono_con_plantilla(icono_fuente, marco_icono)
    if icono_fuente.size == (ancho, alto):
        icono = icono_fuente
    elif conplantilla is not None:
        icono = conplantilla
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
            armada = pantalla_con_plantilla(caja_fuente, nombre, anio, jugadores,
                                            idioma)
            if armada is None:
                imagen = _pantalla(ancho, alto, caja_fuente, nombre, claro, oscuro)
            else:
                imagen = armada if armada.size == (ancho, alto) else \
                    armada.resize((ancho, alto), Image.LANCZOS)
        resultados[archivo] = escribir_tga(
            os.path.join(carpeta_meta, archivo), imagen, bits, relleno)

    # bootLogoTex.tga NO se toca: es el logotipo de Nintendo que el sistema
    # dibuja en una esquina al arrancar, no un lugar para el nombre del juego.
    # Escribir texto ahi, en 170x42, da un borron ilegible en pantalla.
    return resultados


# Composicion sobre una plantilla, que es como lo hace la herramienta de
# Windows y por que sus titulos se ven iguales a los originales: el marco con
# la estetica de Consola Virtual esta dibujado a mano, y el programa solo le
# pinta encima la caratula, el nombre, el anio y la cantidad de jugadores.
#
# Las medidas salieron de leer BootImage.cs de UWUVCI AIO, que es GPL-3 igual
# que este proyecto. Las plantillas vienen de ahi, con atribucion en
# datos/PROCEDENCIA.md.
PLANTILLAS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          'datos', 'plantillas')

# (x, y, ancho, alto) sobre un lienzo de 1280x720.
HUECO_ARTE = (131, 249, 400, 300)
LINEA_1_SOLA = (578, 340)
LINEA_1_DE_2 = (578, 313)
LINEA_2 = (578, 368)
ANIO = (586, 450)
JUGADORES = (586, 496)
ALTO_NOMBRE = 34
ALTO_DATO = 28

# El marco del icono tapa una banda arriba —el logotipo de la consola— y otra
# abajo. Medido sobre el canal alfa de la plantilla: lo unico libre va de la
# fila 23 a la 117. Llenando los 128x128 enteros, el logotipo le comia la
# cabeza a la caratula y los costados se iban de cuadro.
VENTANA_ICONO = (0, 23, 128, 94)

ETIQUETAS = {
    'es': ('Lanzamiento: %s', 'Jugadores: %s'),
    'en': ('Released: %s', 'Players: %s'),
    'pt': ('Lancamento: %s', 'Jogadores: %s'),
    'fr': ('Sortie: %s', 'Joueurs: %s'),
    'it': ('Uscita: %s', 'Giocatori: %s'),
    'de': ('Erschienen: %s', 'Spieler: %s'),
}


def _etiquetas(idioma=None):
    """Los rotulos del anio y los jugadores, en el idioma que corresponda.

    Sin idioma explicito se mira el del sistema, que es el que mas chances
    tiene de coincidir con el de la consola. Si no esta traducido, ingles.
    """
    if not idioma:
        import os as _os
        for var in ('LC_ALL', 'LC_MESSAGES', 'LANG'):
            if _os.environ.get(var):
                idioma = _os.environ[var][:2].lower()
                break
    return ETIQUETAS.get((idioma or 'en').lower(), ETIQUETAS['en'])


def _plantilla(nombre):
    ruta = os.path.join(PLANTILLAS, nombre)
    return Image.open(ruta).convert('RGBA') if os.path.isfile(ruta) else None


def _texto_con_borde(dibujo, posicion, texto, fuente, borde=3):
    """Texto claro con contorno oscuro, para que se lea sobre cualquier fondo."""
    x, y = posicion
    for dx in range(-borde, borde + 1):
        for dy in range(-borde, borde + 1):
            if dx * dx + dy * dy <= borde * borde:
                dibujo.text((x + dx, y + dy), texto, font=fuente, fill=(40, 40, 40))
    dibujo.text((x, y), texto, font=fuente, fill=(255, 255, 255))


def _fuente(alto):
    try:
        return ImageFont.truetype(FUENTE, alto)
    except OSError:
        return ImageFont.load_default()


def _partir_nombre(dibujo, nombre, fuente, ancho_max=640):
    """Parte el nombre en como mucho dos lineas, que es lo que admite el marco."""
    palabras = nombre.replace('\n', ' ').split()
    lineas, actual = [], ''
    for palabra in palabras:
        prueba = (actual + ' ' + palabra).strip()
        if dibujo.textlength(prueba, font=fuente) <= ancho_max or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
            if len(lineas) == 1:
                break
    if actual:
        lineas.append(actual)
    return lineas[:2]


def pantalla_con_plantilla(arte, nombre, anio=0, jugadores=0, idioma=None):
    """Arma la pantalla de arranque de 1280x720 sobre la plantilla de DS.

    Devuelve None si la plantilla no esta, para que el llamador se quede con
    la composicion propia.
    """
    marco = _plantilla('nds-pantalla.png')
    if marco is None:
        return None

    limpio = _quitar_bordes_muertos(arte).convert('RGB')
    x, y, ancho, alto = HUECO_ARTE

    # Entera y centrada, no recortada a la medida del hueco: la proporcion de
    # una caratula de DS no es la del hueco, y llenandolo se le comian los
    # bordes. Lo que sobra se rellena con el color promedio de la propia
    # caratula, que al lado del original no canta.
    lienzo = Image.new('RGBA', (1280, 720), (0, 0, 0, 255))
    copia = limpio.copy()
    copia.thumbnail((ancho, alto), Image.LANCZOS)
    lienzo.paste(Image.new('RGB', (ancho, alto), _color_promedio(limpio)), (x, y))
    lienzo.paste(copia, (x + (ancho - copia.width) // 2,
                         y + (alto - copia.height) // 2))
    lienzo = Image.alpha_composite(lienzo, marco)

    dibujo = ImageDraw.Draw(lienzo)
    fuente = _fuente(ALTO_NOMBRE)
    lineas = _partir_nombre(dibujo, nombre, fuente)
    if len(lineas) > 1:
        _texto_con_borde(dibujo, LINEA_1_DE_2, lineas[0], fuente)
        _texto_con_borde(dibujo, LINEA_2, lineas[1], fuente)
    elif lineas:
        _texto_con_borde(dibujo, LINEA_1_SOLA, lineas[0], fuente)

    chica = _fuente(ALTO_DATO)
    rotulo_anio, rotulo_jug = _etiquetas(idioma)
    if anio:
        _texto_con_borde(dibujo, ANIO, rotulo_anio % anio, chica, borde=2)
    if jugadores:
        cuantos = '1' if jugadores == 1 else '1-%d' % min(jugadores, 4)
        _texto_con_borde(dibujo, JUGADORES, rotulo_jug % cuantos, chica, borde=2)
    return lienzo.convert('RGB')


def _color_promedio(imagen):
    """Un color sacado de la propia imagen, para rellenar sin inventar nada."""
    return imagen.convert('RGB').resize((1, 1), Image.LANCZOS).getpixel((0, 0))


def icono_con_plantilla(arte, marco=False):
    """Icono de 128x128 con la caratula entera, con o sin el marco de DS.

    Sin marco por defecto: la plantilla trae el logotipo de la consola arriba,
    y las caratulas de DS ya lo traen impreso en su franja lateral. Puestos los
    dos quedaba repetido, y el de arriba ademas le tapaba la cabeza a la
    ilustracion.

    Con marco=True se superpone igual, para arte propio que no lo traiga. En
    ese caso la caratula entra en la franja que el marco deja libre, no en el
    cuadro entero, asi el logotipo no tapa nada.

    Lo que sobra alrededor se rellena con el color promedio de la caratula.
    """
    limpio = _quitar_bordes_muertos(arte).convert('RGB')
    plantilla = _plantilla('nds-icono.png') if marco else None

    if plantilla is None:
        hueco = (0, 0, 128, 128)
    else:
        hueco = VENTANA_ICONO

    x, y, ancho, alto = hueco
    copia = limpio.copy()
    copia.thumbnail((ancho, alto), Image.LANCZOS)
    lienzo = Image.new('RGBA', (128, 128), _color_promedio(limpio) + (255,))
    lienzo.paste(copia, (x + (ancho - copia.width) // 2,
                         y + (alto - copia.height) // 2))
    return lienzo if plantilla is None else Image.alpha_composite(lienzo, plantilla)
