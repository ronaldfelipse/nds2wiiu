# Inyector de juegos de Nintendo DS en un titulo de Consola Virtual de Wii U.
#
# Parte de una base: un titulo de DS ya descifrado, tal como lo entrega el FTP
# de la consola. Reemplaza la ROM que lleva adentro y le cambia la identidad
# (identificador, codigo de producto y nombre) para que el sistema lo trate como
# un titulo distinto y no pise al original.
#
# Queda fuera, a proposito, el empaquetado final cifrado: esto produce la
# carpeta lista, y el cifrado lo hace otra herramienta.
import os, re, shutil, zipfile

# Los titulos inyectados van en la categoria 00050002, la misma donde la consola
# guarda los que ya tenia inyectados de antes.
CATEGORIA = '00050002'

IDIOMAS = ['ja', 'en', 'fr', 'de', 'it', 'es', 'zhs', 'ko', 'nl', 'pt', 'ru', 'zht']

# La forma instalada que entrega la consola trae estos dos archivos, que el
# empaquetador genera por su cuenta. Si se los dejamos puestos se planta con
# "not assigned to any content" y no llega a escribir nada.
SOBRANTES = [('code', 'title.fst'), ('code', 'title.tmd')]


def nombre_rom_en_zip(ruta_zip):
    """Devuelve el nombre del unico archivo que la base lleva dentro de rom.zip."""
    with zipfile.ZipFile(ruta_zip) as z:
        nombres = [i.filename for i in z.infolist() if not i.is_dir()]
    if len(nombres) != 1:
        raise ValueError('se esperaba un solo archivo en %s, hay %d' % (ruta_zip, len(nombres)))
    return nombres[0]


def identidad_desde_codigo(codigo):
    """Del codigo de producto de 4 letras saca el identificador y el grupo.

    Es el mismo esquema que usan los titulos ya inyectados de la consola: el
    identificador son los cuatro caracteres en hexadecimal (por ejemplo GGSE ->
    47475345), y el grupo toma del segundo al quinto digito de ese valor.
    """
    codigo = codigo.upper()
    if not re.fullmatch(r'[A-Z0-9]{4}', codigo):
        raise ValueError('el codigo de producto deben ser 4 letras o numeros: %r' % codigo)
    ident = ''.join('%02X' % ord(c) for c in codigo)
    return ident, '0000' + ident[2:6]


def _reemplazar_en_xml(ruta, cambios):
    with open(ruta, encoding='utf-8') as f:
        texto = f.read()
    for etiqueta, valor in cambios.items():
        patron = r'(<%s\b[^>]*>)(.*?)(</%s>)' % (etiqueta, etiqueta)
        nuevo, n = re.subn(patron, lambda m: m.group(1) + valor + m.group(3), texto, flags=re.S)
        if n == 0:
            raise ValueError('no se encontro la etiqueta <%s> en %s' % (etiqueta, ruta))
        texto = nuevo
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(texto)


def _nombres(nombre):
    """Devuelve el nombre para el menu grande y para el menu HOME.

    Los dos reciben el nombre entero. La herramienta de Windows corta por la
    primera coma, porque recibe los nombres como los escribe No-Intro, con el
    articulo desplazado al final: "Zelda, The Legend of - Spirit Tracks". Ahi
    la coma marca ese desplazamiento y cortar tiene sentido.

    Aca no: rom.nombre_legible ya devolvio el articulo a su lugar, asi que
    toda coma que sobreviva es parte del titulo de verdad. Cortando por ella,
    "The Chronicles of Narnia - The Lion, the Witch and the Wardrobe" quedaba
    como "The Chronicles of Narnia - The Lion", partido a la mitad de la
    frase. Si el nombre no entra en el menu HOME, lo acorta la consola, que
    sabe cuanto espacio tiene.
    """
    return nombre, nombre


def inyectar(base, rom, salida, nombre, codigo):
    """Arma en 'salida' una copia de 'base' con 'rom' adentro y la identidad nueva."""
    if os.path.exists(salida):
        raise FileExistsError('ya existe %s' % salida)
    ident, grupo = identidad_desde_codigo(codigo)

    shutil.copytree(base, salida)

    quitados = []
    for partes in SOBRANTES:
        ruta = os.path.join(salida, *partes)
        if os.path.isfile(ruta):
            os.remove(ruta)
            quitados.append(os.path.join(*partes))

    ruta_zip = os.path.join(salida, 'content', '0010', 'rom.zip')
    interno = nombre_rom_en_zip(ruta_zip)
    with open(rom, 'rb') as f:
        datos = f.read()
    # Se reescribe el zip entero con el mismo nombre interno: el emulador busca
    # ese nombre, no el del archivo que le demos.
    with zipfile.ZipFile(ruta_zip, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr(interno, datos)

    _reemplazar_en_xml(os.path.join(salida, 'code', 'app.xml'), {
        'title_id': CATEGORIA + ident,
        'group_id': grupo,
    })
    cambios = {'title_id': CATEGORIA + ident,
               'group_id': grupo,
               'product_code': 'WUP-N-' + codigo.upper()}
    # Hay DOS nombres, y hay que cambiar los dos. El largo es el que se ve
    # bajo el icono del menu; el corto, el que muestra el menu HOME con el
    # juego andando. Reescribir solo el largo dejaba el titulo inyectado
    # diciendo el nombre de la base en cuanto se apretaba HOME.
    largo, corto = _nombres(nombre)
    for i in IDIOMAS:
        cambios['longname_' + i] = largo
        cambios['shortname_' + i] = corto
    _reemplazar_en_xml(os.path.join(salida, 'meta', 'meta.xml'), cambios)

    return {'identificador': CATEGORIA + ident, 'grupo': grupo,
            'codigo': 'WUP-N-' + codigo.upper(), 'nombre_interno': interno,
            'rom_bytes': len(datos), 'quitados': quitados}
