#!/usr/bin/env python3
"""nds2wiiu — inyecta juegos de Nintendo DS en titulos de Wii U, desde Linux.

Cada subcomando es un paso del proceso, y 'inyectar' los encadena todos.
Las rutas y la direccion de la consola salen de la linea de ordenes o del
archivo de configuracion; no hay nada fijo en el codigo.
"""
import argparse
import configparser
import os
import shutil
import sys
import tempfile

from nds2wiiu import claves, compatibilidad, consola, empaquetado, ia, inyeccion, rom

# arte e imagenes necesitan Pillow, que solo hace falta para generar las
# imagenes del titulo. Se importan dentro de la orden que los usa para que
# listar bases, extraer, empaquetar y subir funcionen sin tenerlo instalado.

CONFIG = os.path.expanduser('~/.config/nds2wiiu/config.ini')


def leer_config():
    cfg = configparser.ConfigParser()
    if os.path.isfile(CONFIG):
        cfg.read(CONFIG)
    return cfg['nds2wiiu'] if cfg.has_section('nds2wiiu') else {}


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
    ip = opcion(args, cfg, 'consola', True)
    encontradas = consola.bases(ip)
    if not encontradas:
        print('No hay titulos de Consola Virtual de DS instalados en esa consola.')
        print('Sin una base no se puede inyectar; mira el README.')
        return 1

    print('Bases disponibles, de emulador mas nuevo a mas viejo:')
    for tid, codigo, nombre, emulador in encontradas:
        print('   %-10s %-12s %-34s emulador %d' % (tid, codigo, nombre[:34], emulador))

    if args.rom:
        cab = rom.cabecera(args.rom)
        print()
        print('Para %s (%s):' % (cab['titulo_interno'], cab['codigo']))
        anotado = compatibilidad.consultar(cab['codigo'])
        if anotado:
            for e in anotado:
                print('   base %-6s %-12s %s' % (e['base'], e['resultado'],
                                                 e.get('fuente', '')))
        else:
            print('   no hay nada anotado todavia para este juego')
        elegida, motivo = compatibilidad.recomendar(cab['codigo'], encontradas)
        if elegida:
            print('   sugerida: %s (%s) — %s' % (elegida[0], elegida[2][:30], motivo))

        if args.consultar_ia and not anotado:
            consultar_ia(cab, encontradas, cfg)
    return 0


def consultar_ia(cab, bases_disponibles, cfg):
    """Pregunta a un modelo con acceso a internet, y guarda lo que conteste.

    Lo que diga entra al registro como 'sin probar': es una pista para empezar,
    no un hecho. Solo pasa a 'funciona' cuando alguien lo prueba de verdad.
    """
    clave = os.environ.get('OPENROUTER_API_KEY') or cfg.get('openrouter')
    modelo = cfg.get('modelo_ia', ia.MODELO)
    print()
    print('Consultando a %s...' % modelo)
    try:
        r = ia.consultar(cab['codigo'], cab['titulo_interno'], bases_disponibles,
                         clave, modelo)
    except ia.SinRespuesta as e:
        print('   sin respuesta util: %s' % e)
        print('   (que diga que no sabe es un resultado valido, no una falla)')
        return
    print('   propone: base %s   confianza %s' % (r['base'], r['confianza']))
    print('   motivo : %s' % r['motivo'])
    print('   fuente : %s' % r['fuente'])
    compatibilidad.anotar(cab['codigo'], r['base'], 'sin probar',
                          fuente='ia: ' + r['fuente'], nota=r['motivo'])
    print('   anotado como "sin probar". Confirmalo con "anotar" cuando lo pruebes.')


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
    nombre = args.nombre or cab['titulo_interno']
    print('ROM: %s  codigo %s  %.1f MB' % (cab['titulo_interno'], cab['codigo'],
                                           cab['tamano'] / 1048576.0))

    info = inyeccion.inyectar(args.base, args.rom, args.salida, nombre, codigo)
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
                                 hallado['icono'][1], ruta, nombre)
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
    ip = opcion(args, cfg, 'consola', True)
    destino = consola.subir(ip, args.paquete, args.nombre, avisar)
    print('Subido y verificado en %s' % destino)
    print('Instalalo desde la consola con WUP Installer GX2 o NUSspli.')
    return 0


def cmd_inyectar(args, cfg):
    """Encadena todo: base de la consola, inyeccion, empaquetado y subida."""
    ip = opcion(args, cfg, 'consola', True)
    jar = opcion(args, cfg, 'nuspacker', True)
    clave = claves.obtener(opcion(args, cfg, 'otp'), args.clave)

    cab = rom.cabecera(args.rom)
    codigo = args.codigo or cab['codigo']
    nombre = args.nombre or cab['titulo_interno']

    trabajo = args.trabajo or tempfile.mkdtemp(prefix='nds2wiiu-')
    base = os.path.join(trabajo, 'base')
    armado = os.path.join(trabajo, 'armado')
    paquete = args.salida or os.path.join(trabajo, 'paquete')

    print('1/4  bajando la base %s de la consola' % args.base)
    consola.extraer(ip, args.base, base)

    print('2/4  inyectando %s' % cab['titulo_interno'])
    sub = argparse.Namespace(rom=args.rom, base=base, salida=armado, nombre=nombre,
                             codigo=codigo, sin_arte=args.sin_arte, arte=args.arte)
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


def main():
    p = argparse.ArgumentParser(prog='nds2wiiu', description=__doc__.splitlines()[0])
    p.add_argument('--consola', help='direccion IP de la Wii U')
    p.add_argument('--otp', help='ruta al otp.bin volcado de tu consola')
    p.add_argument('--clave', help='clave comun en hexadecimal, en vez de --otp')
    p.add_argument('--nuspacker', help='ruta a NUSPacker.jar')
    sub = p.add_subparsers(dest='orden', required=True)

    s = sub.add_parser('bases', help='lista los titulos de DS que sirven de base')
    s.add_argument('--rom', help='ademas, sugiere cual conviene para esa ROM')
    s.add_argument('--consultar-ia', action='store_true',
                   help='si no hay nada anotado, preguntar a un modelo con acceso a internet')
    s.set_defaults(func=cmd_bases)

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
    s.add_argument('--rom', required=True)
    s.add_argument('--salida', required=True)
    s.add_argument('--nombre', help='como se vera en el menu (por defecto, el de la ROM)')
    s.add_argument('--codigo', help='codigo de 4 letras (por defecto, el de la ROM)')
    s.add_argument('--arte', help='carpeta con una imagen propia, en vez de buscarla')
    s.add_argument('--sin-arte', action='store_true', help='deja las imagenes de la base')
    s.set_defaults(func=cmd_armar)

    s = sub.add_parser('empaquetar', help='cifra una carpeta armada')
    s.add_argument('entrada')
    s.add_argument('salida')
    s.set_defaults(func=cmd_empaquetar)

    s = sub.add_parser('subir', help='deja un paquete en la tarjeta de la consola')
    s.add_argument('paquete')
    s.add_argument('nombre', help='nombre de la carpeta en install/')
    s.set_defaults(func=cmd_subir)

    s = sub.add_parser('inyectar', help='todo el proceso de una sola vez')
    s.add_argument('--base', required=True, help='identificador de la base en tu consola')
    s.add_argument('--rom', required=True)
    s.add_argument('--nombre')
    s.add_argument('--codigo')
    s.add_argument('--arte')
    s.add_argument('--sin-arte', action='store_true')
    s.add_argument('--salida', help='donde dejar el paquete')
    s.add_argument('--trabajo', help='carpeta de trabajo, para conservar los pasos')
    s.add_argument('--subir', action='store_true', help='dejarlo tambien en la consola')
    s.set_defaults(func=cmd_inyectar)

    args = p.parse_args()
    try:
        sys.exit(args.func(args, leer_config()))
    except KeyboardInterrupt:
        sys.exit('\ncancelado')
    except Exception as e:
        sys.exit('error: %s' % e)


if __name__ == '__main__':
    main()
