#!/usr/bin/env python3
"""nds2wiiu — inyecta juegos de Nintendo DS en titulos de Wii U, desde Linux.

Cada subcomando es un paso del proceso, y 'inyectar' los encadena todos.
Las rutas y la direccion de la consola salen de la linea de ordenes o del
archivo de configuracion; no hay nada fijo en el codigo.
"""
import argparse
import os
import re
import shlex
import shutil
import sys
import tempfile

from nds2wiiu import (asistente, busqueda, catalogo, claves, compatibilidad,
                      config, consola, empaquetado, inyeccion, listado, local,
                      rom)

# arte e imagenes necesitan Pillow, que solo hace falta para generar las
# imagenes del titulo. Se importan dentro de la orden que los usa para que
# listar bases, extraer, empaquetar y subir funcionen sin tenerlo instalado.

CONFIG = config.RUTA


def leer_config():
    return config.leer()


def opcion(args, cfg, nombre, obligatorio=False):
    valor = getattr(args, nombre, None) or cfg.get(nombre)
    if valor:
        valor = os.path.expanduser(valor)
    if obligatorio and not valor:
        sys.exit('falta --%s (o ponelo en %s)' % (nombre, CONFIG))
    return valor


def avisar(nombre, bytes_):
    print('   %-44s %10d' % (nombre[:44], bytes_), flush=True)


def cmd_bases(args, cfg):
    """Lista los titulos de DS que pueden servir de base.

    Solo lista: que base conviene para un juego lo responde 'recomendar', que
    no necesita la consola. Tener las dos cosas en la misma orden obligaba a
    encender la consola para una pregunta que no la necesita, y hacia que la
    sugerencia saliera de lo que habia instalado en vez de lo que conviene.
    """
    if args.local:
        encontradas = local.bases(args.local)
        if not encontradas:
            print('No se encontro ninguna base de DS en %s.' % args.local)
            print('Se busca una carpeta con meta/meta.xml y codigo WUP-N-D*.')
            return 1
    else:
        ip = opcion(args, cfg, 'consola', True)
        encontradas = consola.bases(ip)
        if not encontradas:
            print('No hay titulos de Consola Virtual de DS instalados en esa consola.')
            print('Sin una base no se puede inyectar; mira el README.')
            return 1

    print('Bases disponibles, de emulador mas nuevo a mas viejo:')
    for ident, codigo, nombre, emulador in encontradas:
        if args.local:
            print('   %-12s %-34s emulador %d' % (codigo, nombre[:34], emulador))
            print('      %s' % ident)
        else:
            print('   %-10s %-12s %-34s emulador %d'
                  % (ident, codigo, nombre[:34], emulador))
    if not args.local:
        print()
        print('Bajate una con: ./nds2wiiu.py extraer <identificador> <carpeta>')
    return 0


def buscar_base(ruta_rom):
    """Busca en foros con que base inyecto otra gente este juego.

    No pide clave ni consulta ningun modelo: busca, abre las paginas y muestra
    los fragmentos donde se nombra el juego. La conclusion la saca quien lee.
    """
    nombre = busqueda.termino(ruta_rom)
    print()
    print('Buscando en foros: %s' % nombre)
    try:
        resultados = busqueda.busca_web(nombre)
    except busqueda.SinRespuesta as e:
        print('   %s' % e)
        return
    if not resultados:
        print('   el buscador no devolvio nada')
        return

    for r in resultados[:8]:
        print('   %s' % (r.get('title') or '')[:70])
        print('      %s' % r.get('href', ''))

    print()
    print('Leyendo las primeras paginas...')
    fuentes = busqueda.explora(resultados)
    encontradas = busqueda.menciones(nombre, fuentes)
    if not encontradas:
        print('   ninguna de esas paginas nombra este juego')
        print('   (que no haya nada escrito sobre el es lo mas probable:')
        print('    la lista de la comunidad cubre 539 de mas de mil quinientos)')
        return

    print('Donde se lo nombra:')
    for direccion, _, fragmento in encontradas[:6]:
        print('   %s' % direccion)
        print('      ...%s...' % fragmento)


def cmd_asistente(args, cfg):
    """Arranca el asistente, que es lo que corre cuando no se pide una orden."""
    try:
        return asistente.correr(cfg, cmd_armar, avisar)
    except asistente.Cancelado:
        print()
        print('Cancelado.')
        return 1


def cmd_recomendar(args, cfg):
    """Dice que base conviene para una ROM y pide donde esta esa base.

    No toca la consola. Antes esta pregunta exigia tenerla encendida y en su
    menu principal solo para listar lo instalado, y despues elegia entre eso;
    terminaba sugiriendo lo que habia en vez de lo que conviene. La hoja de la
    comunidad responde la pregunta sin consola y sin red si ya esta en cache.
    """
    cab = rom.cabecera(args.rom)
    if cab['es_dsi']:
        print('Aviso: la ROM dice ser de DSi; el emulador de las bases solo corre DS comun.')
    print('ROM: %s   codigo %s   %.1f MB'
          % (cab['titulo_interno'], cab['codigo'], cab['tamano'] / 1048576.0))
    print()

    try:
        texto, origen = listado.traer()
        entradas = listado.filas(texto)
    except listado.NoDisponible as e:
        print('No se pudo consultar la lista de la comunidad: %s' % e)
        texto, origen, entradas = None, None, []
    if origen == 'respaldo':
        print('Sin internet: se usa la copia incluida en el proyecto, del %s'
              % listado.RESPALDO_FECHA)
    elif origen == 'vieja':
        print('Sin internet: se usa la ultima lista que se habia bajado')

    en_lista = listado.consultar(os.path.basename(args.rom), entradas) if entradas else []
    if en_lista:
        print('En la lista de compatibilidad de la comunidad:')
        for c in en_lista:
            print('   %-46s %s' % (c['nombre'][:46], c['estado']))
            if c['nota'] and c['nota'].lower() != 'no issues':
                print('      nota: %s' % c['nota'][:66])
        print('   fuente: %s' % listado.FUENTE)
    else:
        print('No figura en la lista de la comunidad.')

    anotado = compatibilidad.consultar(cab['codigo'])
    if anotado:
        print('Anotado en este proyecto:')
        for e in anotado:
            print('   base %-6s %-12s %s' % (e['base'], e['resultado'], e.get('fuente', '')))

    base, motivo = compatibilidad.recomendar_base(cab['codigo'], en_lista)
    print()
    print('Base recomendada: %s' % base)
    # El identificador de titulo es lo unico que no se parece a nada: hay
    # juegos de Wii, de Wii U y remakes con nombres casi iguales, y buscar la
    # base por el nombre lleva al archivo equivocado.
    sena = catalogo.describir(base)
    if sena:
        print('   %s' % sena)
    else:
        print('   (no se reconoce entre los 93 titulos de Consola Virtual de DS)')
    print('   porque: %s' % motivo)
    if any(c.get('estado') == 'no arranca' for c in en_lista):
        print('   OJO: la lista lo da como "no arranca"; puede que no funcione'
              ' con ninguna base.')

    if args.buscar_base and not en_lista:
        buscar_base(args.rom)

    print()
    print('Conseguila de tu consola (ftpiiu + "extraer") o de una tarjeta volcada.')
    try:
        carpeta = input('Ruta de la base a usar (vacio para salir): ').strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return 0
    if not carpeta:
        return 0
    # Una ruta copiada de una terminal suele venir entrecomillada.
    comillas = '\'"'
    return _revisar_base(os.path.expanduser(carpeta.strip(comillas)), args.rom, base)


def _revisar_base(carpeta, ruta_rom, recomendada=''):
    """Comprueba que esa carpeta sea una base de DS y arma el comando siguiente.

    Imprime el identificador que trae la carpeta y lo compara con el de la
    base recomendada: es la unica forma de saber sin ambiguedad si se agarro
    el archivo correcto.
    """
    meta = os.path.join(carpeta, 'meta', 'meta.xml')
    if not os.path.isfile(meta):
        print('En %s no hay meta/meta.xml: eso no es un titulo de Wii U.' % carpeta)
        return 1
    with open(meta, encoding='utf-8', errors='replace') as f:
        texto = f.read()
    codigo = local.campo_meta(texto, 'product_code')
    nombre = local.campo_meta(texto, 'longname_en').replace('\n', ' ')
    if not re.match(local.PATRON_DS, codigo):
        print('%s es "%s" (%s), que no es un titulo de Consola Virtual de DS.'
              % (carpeta, nombre, codigo))
        return 1

    identidad = local.campo_meta(texto, 'title_id')
    print()
    print('Base: %s   %s' % (nombre, codigo))
    print('   title ID %s   emulador %d bytes'
          % (identidad, local._tamano_emulador(carpeta)))

    esperada = catalogo.buscar(recomendada)
    if esperada and esperada['title_id'].upper() != identidad.upper():
        print('   OJO: no es la recomendada, que es %s (%s).'
              % (esperada['title_id'], esperada['codigo']))
        print('        Sirve igual, pero anotalo con el codigo de ESTA base.')
    print('Ya podes inyectar:')
    print()
    print('   ./nds2wiiu.py inyectar --base %s --rom %s --subir'
          % (shlex.quote(carpeta), shlex.quote(ruta_rom)))
    return 0


def cmd_anotar(args, cfg):
    """Deja constancia de si una combinacion funciono, para la proxima vez."""
    compatibilidad.anotar(args.juego, args.base, args.resultado, args.fuente, args.nota)
    print('Anotado: %s con base %s -> %s' % (args.juego.upper(), args.base.upper(),
                                             args.resultado))
    print('Si te sirvio, mandalo como pull request: le ahorra la prueba al que venga.')
    return 0


def cmd_extraer(args, cfg):
    ip = opcion(args, cfg, 'consola', True)
    print('Bajando la base %s...' % args.base)
    total = consola.extraer(ip, args.base, args.salida, avisar)
    print('Listo: %.1f MB en %s' % (total / 1048576.0, args.salida))
    return 0


def cmd_armar(args, cfg):
    cab = rom.cabecera(args.rom)
    if cab['es_dsi']:
        print('Aviso: la ROM dice ser de DSi; el emulador de la base solo corre DS comun.')
    codigo = args.codigo or cab['codigo']
    # El nombre que se ve bajo el icono sale del archivo, no de la cabecera:
    # la cabecera tiene 12 caracteres y abrevia ("CASPIAN", "CRASH08DS").
    nombre = args.nombre or rom.nombre_legible(args.rom) or cab['titulo_interno']
    print('ROM: %s  codigo %s  %.1f MB' % (cab['titulo_interno'], cab['codigo'],
                                           cab['tamano'] / 1048576.0))
    print('Se instalara como: %s' % nombre)

    # Si viene en .zip se extrae a un temporal que se borra al salir; el
    # nombre para buscar arte sigue saliendo de args.rom, que es el nombre
    # con el que los catalogos indexan.
    with rom.abierta(args.rom) as ruta_nds:
        info = inyeccion.inyectar(args.base, ruta_nds, args.salida, nombre, codigo)
    print('Identidad nueva: %s  (%s)' % (info['identificador'], info['codigo']))

    if not args.sin_arte:
        try:
            from nds2wiiu import arte, imagenes
        except ImportError:
            print('Arte: hace falta Pillow para generarlo (pip install -r requirements.txt).')
            print('      Por ahora quedan las imagenes de la base.')
            print('Carpeta lista en %s' % args.salida)
            return 0
        with tempfile.TemporaryDirectory() as tmp:
            hallado = arte.buscar('nds', os.path.splitext(os.path.basename(args.rom))[0],
                                  codigo, tmp, local=args.arte)
            if hallado.get('pantalla'):
                fuente, ruta, medida = hallado['pantalla']
                print('Arte: %s%s' % (fuente, '  %dx%d' % medida if medida else ''))
                imagenes.generar(os.path.join(args.salida, 'meta'),
                                 hallado['icono'][1], ruta, nombre,
                                 anio=getattr(args, 'anio', 0) or 0,
                                 jugadores=getattr(args, 'jugadores', 0) or 0,
                                 marco_icono=getattr(args, 'marco_icono', False))
            else:
                print('Arte: no se encontro ninguno; quedan las imagenes de la base')
    print('Carpeta lista en %s' % args.salida)
    return 0


def cmd_empaquetar(args, cfg):
    jar = opcion(args, cfg, 'nuspacker', True)
    clave = claves.obtener(opcion(args, cfg, 'otp'), args.clave)
    codigo, texto = empaquetado.empaquetar(args.entrada, args.salida, jar, clave)
    if codigo != 0:
        print(texto)
        return codigo
    bien, detalle = empaquetado.verificar(args.salida)
    if not bien:
        print('El paquete quedo incompleto: falta %s' % ', '.join(detalle))
        print(texto)
        return 1
    print('Paquete listo en %s  (%d archivos .app)' % (args.salida, len(detalle)))
    return 0


def cmd_subir(args, cfg):
    if args.destino:
        destino = local.copiar(args.paquete, args.destino, args.nombre, avisar)
        print('Copiado y verificado en %s' % destino)
    else:
        ip = opcion(args, cfg, 'consola', True)
        destino = consola.subir(ip, args.paquete, args.nombre, avisar)
        print('Subido y verificado en %s' % destino)
    print('Instalalo desde la consola con WUP Installer GX2 o NUSspli.')
    return 0


def cmd_inyectar(args, cfg):
    """Encadena todo: base, inyeccion, empaquetado y subida.

    La base puede ser un identificador de titulo, que se baja de la consola, o
    una carpeta ya volcada. Con una carpeta y sin --subir no hace falta
    consola en ningun momento.
    """
    base_local = os.path.isdir(os.path.expanduser(args.base))
    ip = (opcion(args, cfg, 'consola', True)
          if args.subir or not base_local else None)
    jar = opcion(args, cfg, 'nuspacker', True)
    clave = claves.obtener(opcion(args, cfg, 'otp'), args.clave)

    cab = rom.cabecera(args.rom)
    codigo = args.codigo or cab['codigo']
    nombre = args.nombre or rom.nombre_legible(args.rom) or cab['titulo_interno']

    trabajo = args.trabajo or tempfile.mkdtemp(prefix='nds2wiiu-')
    base = os.path.join(trabajo, 'base')
    armado = os.path.join(trabajo, 'armado')
    paquete = args.salida or os.path.join(trabajo, 'paquete')

    if base_local:
        base = os.path.expanduser(args.base)
        print('1/4  usando la base de %s' % base)
    else:
        print('1/4  bajando la base %s de la consola' % args.base)
        consola.extraer(ip, args.base, base)

    print('2/4  inyectando %s' % cab['titulo_interno'])
    sub = argparse.Namespace(rom=args.rom, base=base, salida=armado, nombre=nombre,
                             codigo=codigo, sin_arte=args.sin_arte, arte=args.arte,
                             anio=args.anio, jugadores=args.jugadores,
                             marco_icono=args.marco_icono)
    cmd_armar(sub, cfg)

    print('3/4  empaquetando y cifrando')
    cod, texto = empaquetado.empaquetar(armado, paquete, jar, clave)
    if cod != 0:
        print(texto)
        return cod

    if args.subir:
        print('4/4  subiendo a la consola')
        consola.subir(ip, paquete, '[WUP][NDS] %s' % nombre)
        print('Listo. Instalalo desde la consola.')
    else:
        print('4/4  omitido (no se pidio --subir)')
        print('Paquete en %s' % paquete)

    if not args.trabajo and not args.salida:
        print('Nota: el trabajo quedo en %s' % trabajo)
    elif not args.trabajo:
        shutil.rmtree(trabajo, ignore_errors=True)
    return 0


class Parser(argparse.ArgumentParser):
    """Igual que el de siempre, pero explica el error mas probable.

    Los nombres de No-Intro traen espacios y parentesis: "Chronicles of
    Narnia, The - The Lion... (USA) (En,Fr,Es,It,Nl).zip". Sin comillas, el
    shell los parte en pedazos y argparse dice "unrecognized arguments" sin
    dar ninguna pista de por que.
    """

    def error(self, mensaje):
        if 'unrecognized arguments' in mensaje:
            mensaje += ('\n\nSi la ruta de la ROM tiene espacios, va entre comillas:'
                        '\n   --rom "Mi Juego (USA) (En,Fr,Es).zip"')
        super().error(mensaje)


def main():
    p = Parser(prog='nds2wiiu', description=__doc__.splitlines()[0])
    p.add_argument('--consola', help='direccion IP de la Wii U')
    p.add_argument('--otp', help='ruta al otp.bin volcado de tu consola')
    p.add_argument('--clave', help='clave comun en hexadecimal, en vez de --otp')
    p.add_argument('--nuspacker', help='ruta a NUSPacker.jar')
    # Sin orden arranca el asistente: quien usa esto una vez cada varios meses
    # no tiene por que recordar siete ordenes y sus banderas.
    sub = p.add_subparsers(dest='orden')

    s = sub.add_parser('asistente', help='pregunta paso a paso lo que hace falta')
    s.set_defaults(func=cmd_asistente)

    s = sub.add_parser('bases', help='lista los titulos de DS que sirven de base')
    s.add_argument('--local', metavar='CARPETA',
                   help='buscar las bases en una carpeta volcada en vez de'
                        ' la consola; no necesita FTP')
    s.set_defaults(func=cmd_bases)

    s = sub.add_parser('recomendar',
                       help='que base conviene para una ROM, sin tocar la consola')
    s.add_argument('--rom', required=True, help='.nds, .srl o .zip')
    s.add_argument('--buscar-base', '--consultar-ia', dest='buscar_base',
                   action='store_true',
                   help='si no figura en la lista, buscar ademas en foros')
    s.set_defaults(func=cmd_recomendar)

    s = sub.add_parser('anotar', help='registra si una combinacion funciono')
    s.add_argument('juego', help='codigo de 4 letras del juego, por ejemplo CR8E')
    s.add_argument('base', help='codigo de 4 letras de la base, por ejemplo DAGP')
    s.add_argument('resultado', choices=compatibilidad.RESULTADOS)
    s.add_argument('--fuente', default='probado')
    s.add_argument('--nota', default='')
    s.set_defaults(func=cmd_anotar)

    s = sub.add_parser('extraer', help='baja una base de la consola')
    s.add_argument('base', help='identificador del titulo, por ejemplo 101a2000')
    s.add_argument('salida')
    s.set_defaults(func=cmd_extraer)

    s = sub.add_parser('armar', help='mete la ROM en una base ya bajada')
    s.add_argument('--base', required=True)
    s.add_argument('--rom', required=True, help='.nds, .srl o .zip')
    s.add_argument('--salida', required=True)
    s.add_argument('--nombre', help='como se vera en el menu (por defecto, el de la ROM)')
    s.add_argument('--codigo', help='codigo de 4 letras (por defecto, el de la ROM)')
    s.add_argument('--arte', help='carpeta con una imagen propia, en vez de buscarla')
    s.add_argument('--sin-arte', action='store_true', help='deja las imagenes de la base')
    s.add_argument('--anio', type=int, metavar='AAAA',
                   help='anio de lanzamiento, para la pantalla de arranque')
    s.add_argument('--jugadores', type=int, metavar='N',
                   help='cuantos jugadores, para la pantalla de arranque')
    s.add_argument('--marco-icono', action='store_true',
                   help='superpone el marco de DS al icono; util para arte'
                        ' propio que no lo traiga')
    s.set_defaults(func=cmd_armar)

    s = sub.add_parser('empaquetar', help='cifra una carpeta armada')
    s.add_argument('entrada')
    s.add_argument('salida')
    s.set_defaults(func=cmd_empaquetar)

    s = sub.add_parser('subir', help='deja un paquete en la tarjeta de la consola')
    s.add_argument('paquete')
    s.add_argument('nombre', help='nombre de la carpeta en install/')
    s.add_argument('--destino', metavar='RUTA',
                   help='carpeta install/ de una tarjeta montada en la PC,'
                        ' en vez de subir por FTP')
    s.set_defaults(func=cmd_subir)

    s = sub.add_parser('inyectar', help='todo el proceso de una sola vez')
    s.add_argument('--base', required=True,
                   help='identificador de la base en tu consola, o la ruta de'
                        ' una base ya volcada')
    s.add_argument('--rom', required=True, help='.nds, .srl o .zip')
    s.add_argument('--nombre')
    s.add_argument('--codigo')
    s.add_argument('--arte')
    s.add_argument('--sin-arte', action='store_true')
    s.add_argument('--salida', help='donde dejar el paquete')
    s.add_argument('--trabajo', help='carpeta de trabajo, para conservar los pasos')
    s.add_argument('--subir', action='store_true', help='dejarlo tambien en la consola')
    s.add_argument('--anio', type=int, metavar='AAAA',
                   help='anio de lanzamiento, para la pantalla de arranque')
    s.add_argument('--jugadores', type=int, metavar='N',
                   help='cuantos jugadores, para la pantalla de arranque')
    s.add_argument('--marco-icono', action='store_true',
                   help='superpone el marco de DS al icono; util para arte'
                        ' propio que no lo traiga')
    s.set_defaults(func=cmd_inyectar)

    args = p.parse_args()
    if not getattr(args, 'func', None):
        sys.exit(cmd_asistente(args, leer_config()))
    try:
        sys.exit(args.func(args, leer_config()))
    except KeyboardInterrupt:
        sys.exit('\ncancelado')
    except Exception as e:
        sys.exit('error: %s' % e)


if __name__ == '__main__':
    main()
