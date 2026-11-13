# nds2wiiu

Inyecta juegos de Nintendo DS en títulos de Consola Virtual de Wii U. **Desde Linux.**

Las herramientas que hacen esto son de Windows: están escritas con WPF, que no
existe fuera de Windows ni compilando el código. Esta corre en Linux sin Wine ni
máquinas virtuales.

## Qué hace, y qué no

**Sí:**

- Baja una base de tu propia consola por FTP, ya descifrada
- Mete tu ROM de DS adentro y le da identidad propia
- Le busca carátula y le genera el ícono y las pantallas de arranque
- Empaqueta y cifra el resultado
- Lo deja en la tarjeta de la consola, listo para instalar

**No:**

- **No descarga nada de Nintendo.** Usa lo que ya tenés instalado.
- **No trae claves de títulos.** No es una vía para conseguir juegos que no tengas.
- **No incluye la clave común.** Te la pide a vos, igual que las demás herramientas.

## Requisitos

| | |
|---|---|
| Una Wii U con **Aroma** y el complemento **ftpiiu** activo | para sacar la base y subir el resultado |
| **Un título de Consola Virtual de DS instalado** | es la base; sin eso no hay nada que inyectar |
| El **`otp.bin`** de tu consola | de ahí sale la clave para cifrar |
| **Python 3** y **Java** | |
| **NUSPacker.jar** | el empaquetador, se baja aparte |

### Lo que hay que conseguir aparte

**NUSPacker** no viene incluido: es de terceros y no declara licencia. Se baja de
[ihaveamac/nuspacker](https://github.com/ihaveamac/nuspacker) y se le indica la
ruta con `--nuspacker` o en la configuración.

**El `otp.bin`** se saca de tu consola con el volcador de NAND que viene en el
paquete de herramientas de Aroma.

## Instalación

```bash
git clone https://github.com/ronaldfelipse/nds2wiiu.git
cd nds2wiiu
pip install -r requirements.txt
```

Pillow solo hace falta para generar las imágenes del título. El resto de las
órdenes funciona sin él.

## Uso

Con la consola encendida y **en su menú principal** — el FTP se cae al abrir
cualquier juego.

### Ver qué bases tenés

```bash
./nds2wiiu.py --consola 192.168.40.150 bases
```

```
Bases disponibles:
   101a2300   WUP-N-DAHP   Mario & Luigi: Partners in Time
   101abf00   WUP-N-DALP   Wario: Master of Disguise
   101a2000   WUP-N-DAGP   WarioWare: Touched!
```

### Inyectar, de punta a punta

```bash
./nds2wiiu.py \
    --consola 192.168.40.150 \
    --otp ~/claves/otp.bin \
    --nuspacker ~/herramientas/NUSPacker.jar \
    inyectar \
    --base 101a2000 \
    --rom "Crash - Mind over Mutant (USA).nds" \
    --subir
```

Después, desde la consola, instalalo con **WUP Installer GX2** o **NUSspli**.

### Paso a paso, si preferís control

```bash
./nds2wiiu.py extraer 101a2000 bases/warioware
./nds2wiiu.py armar --base bases/warioware --rom juego.nds --salida armado/
./nds2wiiu.py empaquetar armado/ paquete/
./nds2wiiu.py subir paquete/ "[WUP][NDS] Mi Juego"
```

### Qué base usar

No existe ninguna tabla pública y consultable que diga qué base conviene para
cada juego: lo que hay son hilos de foro y wikis que casi nadie mantiene. Así
que este proyecto arma la suya con lo que la gente prueba de verdad.

```bash
./nds2wiiu.py --consola 192.168.40.150 bases --rom juego.nds
```

```
Bases disponibles, de emulador mas nuevo a mas viejo:
   101abf00   WUP-N-DALP   Wario: Master of Disguise          emulador 1542592
   101a2300   WUP-N-DAHP   Mario & Luigi: Partners in Time    emulador 1541120
   101a2000   WUP-N-DAGP   WarioWare: Touched!                emulador 1540608

Para CRASH08DS (CR8E):
   base DAGP   funciona     probado
   sugerida: 101a2000 (WarioWare: Touched!) — anotada como funcional
```

Un resultado probado manda sobre la heurística del emulador más nuevo. Si no hay
nada anotado para ese juego, sugiere el emulador más reciente, que es el único
criterio objetivo que queda.

Cuando pruebes una combinación, anotala:

```bash
./nds2wiiu.py anotar CR8E DAGP funciona --nota "arranca y se juega entero"
```

Queda en `compatibilidad.json`, que se versiona junto al código. **Si mandás tu
resultado como pull request, le ahorrás la prueba al que venga después.** Esa es
la única forma de que esta tabla exista.

### Configuración

Para no repetir lo mismo cada vez, en `~/.config/nds2wiiu/config.ini`:

```ini
[nds2wiiu]
consola = 192.168.40.150
otp = ~/claves/otp.bin
nuspacker = ~/herramientas/NUSPacker.jar
```

## De dónde sale el arte

Se prueban tres catálogos públicos, en orden de calidad, y se usa el primero que
responda. Ninguno pide cuenta ni clave:

1. **UWUVCI-IMAGES** — imágenes hechas a medida para inyecciones, ya en 1280×720.
   Cubre pocos juegos, pero los que cubre quedan perfectos.
2. **libretro-thumbnails** — indexado por el nombre exacto del archivo de la ROM.
   Cubre prácticamente todo, a unos 512 píxeles.
3. **GameTDB** — último recurso.

Con `--arte <carpeta>` le pasás una imagen propia y se saltea la búsqueda.
Con `--sin-arte` deja las imágenes de la base.

## Detalles que conviene saber

**No todas las bases son iguales.** Cada una trae una revisión distinta del
emulador de DS, y eso se puede medir:

```
Wario: Master of Disguise         1.542.592 bytes
Mario & Luigi: Partners in Time   1.541.120 bytes
WarioWare: Touched!               1.540.608 bytes
```

Tres tamaños, tres programas distintos. Por eso un juego puede andar con una
base y no con otra. `bases` las ordena de emulador más nuevo a más viejo.

**El código del juego se lee de la ROM.** De ahí sale el identificador del título
inyectado, con el mismo esquema que usan las demás herramientas: las cuatro
letras del código pasadas a hexadecimal.

**La clave nunca se muestra.** Se lee en el momento, se le pasa al empaquetador y
no queda escrita en ningún lado. Antes de empezar se valida contra su huella
conocida, así si apuntás al archivo equivocado te enterás al segundo.

**Juegos de DSi no.** El emulador de las bases solo corre DS común; la
herramienta avisa si detecta una ROM de DSi.

## Licencia

GPL-3. El diseño salió de leer
[UWUVCI AIO](https://github.com/stuff-by-3-random-dudes/UWUVCI-AIO-WPF), que es
GPL-3 — esta es una reimplementación independiente en Python, pero la deuda está
reconocida.

NUSPacker y el arte de los catálogos citados pertenecen a sus respectivos
autores y no se distribuyen con este proyecto.
