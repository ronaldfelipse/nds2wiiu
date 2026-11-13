# Asistente paso a paso: se arranca sin argumentos y va pidiendo lo que hace
# falta, en los dos caminos posibles — por FTP contra la consola, o con una
# tarjeta montada en la PC.
#
# Existe porque la herramienta tenia siete ordenes y cada una pedia sus rutas
# por bandera. Para quien la usa una vez cada varios meses, eso significa leer
# el README entero antes de empezar. Las ordenes sueltas siguen estando para
# quien automatiza; esto es para el resto.
import os
import re
import tempfile

from nds2wiiu import (catalogo, claves, compatibilidad, config, consola,
                      empaquetado, listado, local, rom)

COMILLAS = '\'"'


def _texto(pregunta, defecto=None):
    etiqueta = '%s [%s]: ' % (pregunta, defecto) if defecto else '%s: ' % pregunta
    try:
        dicho = input(etiqueta).strip()
    except (EOFError, KeyboardInterrupt):
        raise Cancelado()
    return dicho or (defecto or '')


def _ruta(pregunta, defecto=None, debe_existir=True):
    """Pide una ruta. Acepta la forma en que la pega una terminal."""
    while True:
        dicho = _texto(pregunta, defecto)
        if not dicho:
            return ''
        camino = os.path.expanduser(dicho.strip(COMILLAS))
        if not debe_existir or os.path.exists(camino):
            return camino
        print('   no existe: %s' % camino)


def _elegir(pregunta, opciones):
    """Menu numerado. Devuelve el indice elegido.

    No hay opcion por omision a proposito: un Enter distraido elegia en
    silencio la primera, que no siempre es la recomendada, y el error recien
    aparecia veinte minutos despues al probar el juego en la consola. Aca no
    se avanza sin decir un numero.
    """
    for i, texto in enumerate(opciones, 1):
        print('   %d) %s' % (i, texto))
    while True:
        dicho = _texto(pregunta)
        if dicho.isdigit() and 1 <= int(dicho) <= len(opciones):
            return int(dicho) - 1
        print('   elegi un numero entre 1 y %d' % len(opciones))


def _entero(pregunta):
    """Un numero opcional. Vacio devuelve 0, que para quien lo recibe es 'no hay'."""
    while True:
        dicho = _texto(pregunta)
        if not dicho:
            return 0
        if dicho.isdigit():
            return int(dicho)
        print('   tiene que ser un numero, o Enter para omitirlo')


def _si(pregunta, defecto=True):
    dicho = _texto('%s (s/n)' % pregunta, 's' if defecto else 'n').lower()
    return dicho.startswith('s') or dicho.startswith('y')


class Cancelado(Exception):
    """El usuario corto el asistente."""


def _recomendacion(ruta_rom, cab):
    """Que base conviene, sin tocar la consola."""
    try:
        entradas, origenes = listado.cargar()
    except listado.NoDisponible as e:
        print('   no se pudo consultar ninguna lista: %s' % e)
        entradas, origenes = [], {}
    avisos = {'vieja': 'sin internet, la ultima bajada',
              'respaldo': 'sin internet, la copia del proyecto del %s'
                          % listado.RESPALDO_FECHA,
              'no disponible': 'no se pudo traer',
              'ilegible': 'formato ilegible'}
    for nombre, origen in sorted(origenes.items()):
        if origen in avisos:
            print('   lista de %s: %s' % (nombre, avisos[origen]))

    en_lista = listado.consultar(os.path.basename(ruta_rom), entradas) if entradas else []
    for c in en_lista:
        print('   %s lo da como "%s" con base %s'
              % (c['fuente'], c['estado'], c['base']))
        if c['nota']:
            print('      nota: %s' % c['nota'][:66])
    if not en_lista:
        print('   no figura en la lista de la comunidad')
    for e in compatibilidad.consultar(cab['codigo']):
        print('   anotado en este proyecto: base %s -> %s' % (e['base'], e['resultado']))

    base, motivo = compatibilidad.recomendar_base(cab['codigo'], en_lista)
    print()
    print('   Base recomendada: %s' % base)
    seña = catalogo.describir(base)
    if seña:
        print('   %s' % seña)
    else:
        print('   (no se reconoce entre los 93 titulos de Consola Virtual de DS)')
    print('   porque: %s' % motivo)
    if any(c.get('estado') == 'no arranca' for c in en_lista):
        print('   OJO: la lista lo da como "no arranca" con cualquier base.')
    return base


def _opciones(encontradas, recomendada):
    """Arma el menu y dice cual entrada es la recomendada.

    Devuelve (lineas, indice_recomendado). El indice es 0 cuando ninguna
    coincide, que es lo que hace cualquier menu sin preferencia.
    """
    clave = listado._normalizar(recomendada or '')
    lineas, cual = [], 0
    for i, (_id, _codigo, nombre, emulador) in enumerate(encontradas):
        es_esa = bool(clave) and listado._normalizar(nombre) == clave
        if es_esa:
            cual = i
        lineas.append('%-34s  emulador %d%s'
                      % (nombre[:34], emulador, '   <-- la recomendada' if es_esa else ''))
    return lineas, cual


def _es_base(carpeta):
    """True si esa carpeta es en si misma un titulo de Consola Virtual de DS."""
    meta = os.path.join(carpeta, 'meta', 'meta.xml')
    if not os.path.isfile(meta):
        return False
    with open(meta, encoding='utf-8', errors='replace') as f:
        codigo = local.campo_meta(f.read(), 'product_code')
    return bool(re.match(local.PATRON_DS, codigo))


def _codigo_base(carpeta):
    """Las cuatro letras con las que se anota esa base, sacadas de su meta.xml."""
    try:
        with open(os.path.join(carpeta, 'meta', 'meta.xml'),
                  encoding='utf-8', errors='replace') as f:
            return local.campo_meta(f.read(), 'product_code')[-4:].upper()
    except OSError:
        return ''


def _mostrar_base(carpeta):
    """Imprime la identidad exacta de la base elegida, leida de su meta.xml."""
    with open(os.path.join(carpeta, 'meta', 'meta.xml'),
              encoding='utf-8', errors='replace') as f:
        texto = f.read()
    print('   elegida: %s   title ID %s   %s'
          % (local.campo_meta(texto, 'longname_en').replace('\n', ' '),
             local.campo_meta(texto, 'title_id'),
             local.campo_meta(texto, 'product_code')))


def _pedir_base(recomendada, sugerida=None):
    """Pide la ruta de la base. No mira la consola ni adivina nada.

    Que base conviene se respondio arriba, con la hoja de la comunidad. De
    donde sale el archivo es cosa de quien usa la herramienta: listar lo que
    hay instalado en la consola para elegir de ahi era volver a sugerir lo que
    hay en vez de lo que conviene, y de paso obligaba a tener la consola
    encendida y en su menu principal.

    Acepta tanto la carpeta de una base como una que contenga varias.
    """
    print('   Es la carpeta de un titulo de DS ya volcado: la que tiene')
    print('   adentro code/, content/ y meta/. Si todavia no la tenes, sacala')
    print('   de tu consola con "./nds2wiiu.py bases" y "./nds2wiiu.py extraer".')
    while True:
        carpeta = _ruta('   Ruta de la base (vacio para salir)', sugerida)
        if not carpeta:
            return '', ''
        if _es_base(carpeta):
            _mostrar_base(carpeta)
            return carpeta, carpeta
        encontradas = local.bases(carpeta)
        if not encontradas:
            print('   ahi adentro no hay ningun titulo de Consola Virtual de DS')
            continue
        if len(encontradas) == 1:
            camino, _c, nombre, emu = encontradas[0]
            print('   unica base encontrada: %s (emulador %d)' % (nombre, emu))
            return camino, carpeta
        lineas, _cual = _opciones(encontradas, recomendada)
        elegida = encontradas[_elegir('   Cual uso', lineas)][0]
        _mostrar_base(elegida)
        return elegida, carpeta


def _recordar(cfg, valores):
    """Guarda en la configuracion lo que todavia no estaba.

    Recien aca, con la inyeccion terminada: lo que se guarda son respuestas
    que ya demostraron servir. Guardarlas antes seria dejar escrita una ruta
    equivocada en el primer intento fallido.

    Nunca pisa lo que ya estaba: quien edito el archivo a mano sabe mejor.
    """
    nuevas = config.guardar_faltantes({k: v for k, v in valores.items() if v})
    if nuevas:
        print()
        print('Guardado en %s: %s' % (config.RUTA, ', '.join(nuevas)))
        print('La proxima vez ya vienen puestos; para cambiarlos, edita el archivo.')


def correr(cfg, armar, avisar):
    """El asistente entero. 'armar' es la orden que inyecta y genera el arte."""
    import argparse

    print('nds2wiiu — inyectar un juego de DS en un titulo de Wii U')
    print()

    print('1. La ROM')
    ruta_rom = _ruta('   Archivo .nds, .srl o .zip')
    if not ruta_rom:
        return 1
    cab = rom.cabecera(ruta_rom)
    print('   %s   codigo %s   %.1f MB'
          % (cab['titulo_interno'], cab['codigo'], cab['tamano'] / 1048576.0))
    nombre_visible = rom.nombre_legible(ruta_rom) or cab['titulo_interno']
    print('   se instalara como: %s' % nombre_visible)
    # Datos opcionales que la pantalla de arranque muestra al costado, igual
    # que los titulos originales. No salen de ningun lado automatico: la ROM
    # no los trae y no hay catalogo publico que los de para todo el DS.
    anio = _entero('   Anio de lanzamiento (Enter para omitirlo)')
    jugadores = _entero('   Cuantos jugadores (Enter para omitirlo)')
    if cab['es_dsi']:
        print('   Aviso: dice ser de DSi; el emulador de las bases solo corre DS comun.')
    print()

    print('2. Que base conviene')
    recomendada = _recomendacion(ruta_rom, cab)
    print()

    print('3. La base')
    base, carpeta_bases = _pedir_base(recomendada, cfg.get('bases'))
    if not base:
        return 1
    print()

    print('4. Lo que hace falta para cifrar')
    otp = _ruta('   Ruta del otp.bin', cfg.get('otp'))
    clave = claves.obtener(otp, None)
    print('   clave leida y validada')
    jar = _ruta('   Ruta de NUSPacker.jar', cfg.get('nuspacker'))
    if not jar:
        print('Sin NUSPacker no se puede empaquetar.')
        return 1
    print()

    print('5. Donde dejo el resultado')
    ip, destino_sd = '', ''
    if _elegir('   Como lo entrego', [
            'subirlo por FTP a la tarjeta de la consola',
            'dejarlo en una carpeta de la PC (la tarjeta montada, o para copiar luego)'
            ]) == 0:
        ip = _texto('   Direccion IP de la consola', cfg.get('consola'))
        if not ip:
            print('Sin IP no se puede usar el FTP.')
            return 1
    else:
        destino_sd = _ruta('   Carpeta donde lo dejo', debe_existir=True)
        if not destino_sd:
            return 1
    nombre_carpeta = _texto('   Nombre de la carpeta en install',
                            '[WUP][NDS] %s' % nombre_visible)

    print()
    print('Resumen')
    print('   ROM    : %s' % os.path.basename(ruta_rom))
    print('   base   : %s' % base)
    print('   destino: %s' % (('FTP %s' % ip) if not destino_sd else destino_sd))
    print('   carpeta: %s' % nombre_carpeta)
    if not _si('Sigo'):
        return 1

    trabajo = tempfile.mkdtemp(prefix='nds2wiiu-')
    armado = os.path.join(trabajo, 'armado')
    paquete = os.path.join(trabajo, 'paquete')

    print()
    print('Inyectando...')
    armar(argparse.Namespace(rom=ruta_rom, base=base, salida=armado,
                             nombre=nombre_visible, codigo=cab['codigo'],
                             anio=anio, jugadores=jugadores,
                             sin_arte=False, arte=None), cfg)

    print('Empaquetando y cifrando...')
    codigo, texto = empaquetado.empaquetar(armado, paquete, jar, clave)
    if codigo != 0:
        print(texto)
        return codigo
    bien, falta = empaquetado.verificar(paquete)
    if not bien:
        print('El paquete quedo incompleto: falta %s' % ', '.join(falta))
        return 1

    print('Copiando...')
    if destino_sd:
        donde = local.copiar(paquete, destino_sd, nombre_carpeta, avisar)
    else:
        donde = consola.subir(ip, paquete, nombre_carpeta, avisar)
    print('Listo en %s' % donde)
    _recordar(cfg, {'otp': otp, 'nuspacker': jar, 'bases': carpeta_bases,
                    'consola': ip, 'destino': destino_sd})

    print()
    print('Instalalo desde la consola con WUP Installer GX2 o NUSspli.')
    # El codigo de la base se sabe: dejarlo como <codigo-de-la-base> obligaba
    # a ir a buscarlo justo cuando el trabajo ya estaba hecho, que es cuando
    # menos ganas hay de buscar nada.
    print('Cuando lo pruebes, anota el resultado para el que venga despues:')
    print('   ./nds2wiiu.py anotar %s %s funciona'
          % (cab['codigo'], _codigo_base(base) or '<codigo-de-la-base>'))
    return 0
