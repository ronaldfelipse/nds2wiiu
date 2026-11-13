# nds2wiiu

Pone en el menú de tu Wii U juegos de Nintendo DS **que nunca salieron en su
tienda**. Desde Linux.

## Para qué sirve

De los más de mil quinientos juegos que tuvo la Nintendo DS, a la Consola
Virtual de Wii U llegaron **31**. El resto nunca estuvo disponible, y al cerrar
la eShop en 2023 esa lista quedó congelada para siempre.

Esta herramienta aprovecha algo que sí está ahí: **el emulador de DS que
Nintendo escribió para la Wii U**, que viaja dentro de cada uno de esos 31
títulos. La idea es tomar uno de ellos, sacarle el juego que trae y poner otro
en su lugar. El resultado se instala y se comporta como un título más del menú:
su propio ícono, su pantalla de arranque, sus guardados.

A eso se le llama **inyectar**, y para hacerlo necesitás dos cosas.

### 1. El juego, en digital

Un archivo `.nds` (o `.srl`, o un `.zip` que contenga uno). Puede salir del
cartucho que tengas, volcado con un lector, o de donde lo tengas guardado. La
herramienta no lo descarga ni te ayuda a conseguirlo: lo pide y punto.

### 2. Una base

Uno de esos 31 títulos de Consola Virtual de DS. Es de donde sale el emulador,
y sin él no hay nada en lo que inyectar.

Si ya tenés alguno instalado, la herramienta lo baja de tu consola por FTP.
Si no, la forma habitual de conseguir títulos de Wii U es
**[NUSspli](https://github.com/V10lator/NUSspli)**, que corre en la consola.

### Dónde está la diferencia entre las dos

Es la pregunta que más confunde, así que conviene decirla derecho:

| | NUSspli | nds2wiiu |
|---|---|---|
| trae **títulos que ya existen** | sí | no |
| crea un título **que no existía** | no | sí |
| sirve para los 31 juegos de DS que salieron | **sí** | no hace falta |
| sirve para los otros mil quinientos | **no** | **sí** |

NUSspli es un repartidor: va, busca un título y lo instala tal cual. Nunca abre
la caja.

Esta herramienta hace lo contrario: toma una caja que ya tenés, le saca el juego
que traía y le pone otro. Por eso la base es imprescindible, y por eso no
descarga nada.

**Las dos se complementan.** Con NUSspli conseguís la base; con ésta la
convertís en el juego que querías.

## Qué hace, y qué no

**Sí:**

- Baja una base de tu propia consola por FTP, ya descifrada, o la toma de una
  carpeta si preferís no usar la red
- Mete tu ROM de DS adentro y le da identidad propia
- Le busca carátula y le arma el ícono y las pantallas de arranque
- Empaqueta y cifra el resultado
- Lo deja en la tarjeta de la consola, listo para instalar

**No:** no descarga juegos —ni la ROM ni la base—, no trae claves de títulos y
no incluye la clave común: ésa te la pide, igual que las demás herramientas.

## Requisitos

| | |
|---|---|
| Una Wii U con **Aroma** | para instalar lo que produce |
| El complemento **ftpiiu** | opcional: para sacar la base y subir el resultado sin tocar la tarjeta |
| **Un título de Consola Virtual de DS** | la base; sin eso no hay nada que inyectar |
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
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Y después se usa `.venv/bin/python nds2wiiu.py ...`, o se activa el entorno con
`source .venv/bin/activate`.

**El entorno virtual no es un lujo.** En Debian, Ubuntu y derivados, un
`pip install` a secas falla con `externally-managed-environment`: el sistema
protege su propio Python. Sin entorno virtual la instalación no arranca, y eso
pasó en la máquina donde se desarrolló esto.

Dos dependencias, y ninguna es obligatoria para todo:

| | |
|---|---|
| **Pillow** | solo para generar las imágenes del título |
| **ddgs** | solo para buscar en foros con `--buscar-base` |

Listar bases, extraer, empaquetar y subir funcionan sin ninguna de las dos.

## Uso

### Lo más simple: arrancarlo sin nada

```bash
./nds2wiiu.py
```

Pregunta paso a paso lo que haga falta: la ROM, de dónde sacar la base —de la
consola por FTP o de una carpeta volcada—, el `otp.bin`, el empaquetador y
dónde dejar el resultado. Antes de pedirte la base te dice **cuál conviene**, y
marca esa opción en la lista.

Las órdenes sueltas de abajo siguen estando para quien automatiza.

### Qué base conviene

```bash
./nds2wiiu.py recomendar --rom juego.zip
```

No toca la consola: la pregunta «¿qué base conviene?» no necesita saber qué
tenés instalado. Más abajo, en [Qué base usar](#qué-base-usar), está de dónde
sale la respuesta.

### Ver qué bases tenés

Con la consola encendida y **en su menú principal** — el FTP se cae al abrir
cualquier juego.

```bash
./nds2wiiu.py --consola 192.168.1.50 bases
```

```
Bases disponibles, de emulador mas nuevo a mas viejo:
   101abf00   WUP-N-DALP   Wario: Master of Disguise          emulador 1542592
   101a2300   WUP-N-DAHP   Mario & Luigi: Partners in Time    emulador 1541120
   101a2000   WUP-N-DAGP   WarioWare: Touched!                emulador 1540608

Bajate una con: ./nds2wiiu.py extraer <identificador> <carpeta>
```

Solo lista. Qué base conviene para tu juego lo responde `recomendar`, que no
necesita la consola.

Con `--local <carpeta>` lista las que ya tengas volcadas en el disco, sin FTP.

### Inyectar, de punta a punta

```bash
./nds2wiiu.py \
    --consola 192.168.1.50 \
    --otp ~/claves/otp.bin \
    --nuspacker ~/herramientas/NUSPacker.jar \
    inyectar \
    --base 101a2000 \
    --rom "Crash - Mind over Mutant (USA).nds" \
    --subir
```

`--base` acepta tanto un identificador de la consola, que baja por FTP, como la
ruta de una carpeta ya volcada. Con una carpeta y sin `--subir`, no hace falta
consola en ningún momento.

Después, desde la consola, instalalo con **WUP Installer GX2** o **NUSspli**.

### Paso a paso, si preferís control

```bash
./nds2wiiu.py extraer 101a2000 bases/warioware
./nds2wiiu.py armar --base bases/warioware --rom juego.nds --salida armado/
./nds2wiiu.py empaquetar armado/ paquete/
./nds2wiiu.py subir paquete/ "[WUP][NDS] Mi Juego"
```

Con `--destino <ruta>` en lugar del FTP, `subir` escribe en una tarjeta montada
en la PC.

### Sin FTP, con la tarjeta en la mano

**La base no está en la tarjeta SD.** Vive en el disco USB o en la memoria
interna de la consola, y las dos están cifradas y atadas a esa consola:
enchufar el disco a una PC no sirve de nada. El FTP de Aroma funciona porque no
lee el disco crudo — pasa por la capa de archivos del sistema, que descifra al
vuelo.

Así que sin FTP hay que volcar el título **desde la consola**, ya descifrado, a
la tarjeta. El volcador que usa la gente es
[Dumpling](https://github.com/dumpling-app/dumpling). Después todo es local:

```bash
# 1. qué base conviene, y qué bases hay en la tarjeta
./nds2wiiu.py recomendar --rom juego.zip
./nds2wiiu.py bases --local /media/sd/dumpling

# 2. inyectar, usando la ruta que te dio el paso anterior
./nds2wiiu.py armar --base "/media/sd/dumpling/WarioWare Touched" \
    --rom juego.zip --salida armado/

# 3. empaquetar y cifrar
./nds2wiiu.py empaquetar armado/ paquete/

# 4. dejarlo en la tarjeta, verificando archivo por archivo
./nds2wiiu.py subir paquete/ "[WUP][NDS] Mi Juego" --destino /media/sd/install
```

`--local` y `--destino` son las dos puertas de atrás: con ellas **nada de este
proceso toca la red**, ni la consola. Lo único que sigue necesitando la consola
es la orden `inyectar`, que es el atajo que encadena todo por FTP.

La lista de compatibilidad tampoco necesita red si ya la bajaste una vez: queda
en caché, y si nunca la bajaste viene una copia en `datos/`.

### Qué base usar

```bash
./nds2wiiu.py recomendar --rom juego.zip
```

Se consultan tres fuentes y **sale una sola sugerencia**, con el motivo al lado
y el identificador exacto del título:

```
Base recomendada: [USA] New Super Mario Bros.
   title ID 0005000010195A00   WUP-N-DADE   USA
   porque: la base mas reportada de las listas: 65 de 260 juegos

Ruta de la base a usar (vacio para salir):
```

El orden de precedencia es este:

| | fuente | por qué va ahí |
|---|---|---|
| 1 | un resultado **probado y anotado** para ese juego | es el único dato que viene de una consola real con un resultado conocido |
| 2 | las **listas de la comunidad**, si ese juego figura | 732 juegos probados por gente, pero no en tu consola |
| 3 | la **base más reportada** del conjunto | es una apuesta, y la salida dice que lo es |

Las tres son automáticas, ninguna pide clave y **ninguna necesita la consola**:
qué base conviene no depende de lo que tengas instalado.

**El identificador de título no es decorativo.** La lista recomienda la base por
su nombre, y hay juegos de Wii, de Wii U y remakes que se llaman casi igual: ese
número es lo único que no se parece a nada. Sale de los 93 títulos de Consola
Virtual de DS que existen, que vienen en `datos/bases-ds.json`.

Cuando le das la ruta, comprueba que sea de verdad un título de DS, **avisa si
no es la recomendada** —sirve igual, pero conviene saberlo antes de anotar el
resultado— y te arma el comando de inyección listo para copiar.

**1. Dos listas de la comunidad.** Mantenidas por gente distinta, y se usan
las dos:

| | mantiene | formato | cubre |
|---|---|---|---|
| [UWUVCI](https://github.com/UWUVCI-PRIME/UWUVCI-Compatibility) | la comunidad de UWUVCI, con un bot de Discord | JSON, un campo por dato | 282 juegos |
| [GBAtemp](https://gbatemp.net/threads/new-wii-u-nds-injection-compatibility-list.605592/) | un hilo de foro de 2022 | hoja de cálculo exportada como CSV | 533 juegos |

**Se usan las dos porque apenas se solapan.** Medido: solo 79 juegos están en
ambas, 454 solo en GBAtemp y 199 solo en UWUVCI. Quedarse con una —cualquiera—
tiraba más de lo que ganaba. Juntas cubren **732**.

Cuando las dos conocen el mismo juego gana UWUVCI, porque su dato es mejor:
cada entrada dice qué base se usó de verdad, mientras que en la hoja de GBAtemp
**512 de 533 la heredan** de un *«salvo que se indique, la base es New Super
Mario Bros.»*. Son suposiciones, no reportes.

Eso cambia un número que conviene no repetir sin mirar: contando solo bases
reportadas de verdad, New Super Mario Bros. (USA) aparece en **65 de 260**
juegos, un 25%, y no en el 95% que sugeriría la regla de la hoja. Sigue siendo
la más común, pero no por goleada.

```
En las listas de compatibilidad de la comunidad:
   Advance Wars: Days of Ruin               con fallas   UWUVCI
      base: [USA] Advance Wars: Days of Ruin
      nota: Major graphical glitches and slowdown on maps.
```

Cada coincidencia dice **de qué lista salió** y si la base es un reporte o una
suposición. Las dos se bajan y se cachean por separado, una semana cada una; si
una falla se sigue con la otra. Sin internet se usa la última bajada, y si
nunca bajaste ninguna, las **copias de respaldo** que vienen en `datos/`. La
salida lo dice siempre, con la fecha. Procedencia y atribución en
[`datos/PROCEDENCIA.md`](datos/PROCEDENCIA.md).

**2. El registro propio del proyecto.** `compatibilidad.json`, con lo que
prueba la gente que usa esta herramienta. Cubre lo que las listas no, y un
resultado anotado acá manda sobre todo lo demás.

```bash
./nds2wiiu.py anotar CR8E DAGP funciona --nota "arranca y se juega entero"
```

Se versiona junto al código. **Si mandás tu resultado como pull request, le
ahorrás la prueba al que venga después.**

**3. Si no figura en ninguna parte**, se recomienda la base más reportada del
conjunto, que hoy es New Super Mario Bros. (USA) con 65 de 260 juegos. No es
una deducción sobre tu juego: es la que más gente usó con éxito en otros. La
salida dice ese número para que sepas que estás ante una apuesta y no un dato,
y se recalcula en cada corrida —las listas se editan y el número de hoy no es
el de dentro de un año.

### Buscar en foros (opcional)

Cuando un juego no está en ninguna de las dos listas — y eso es lo normal —, se
puede salir a buscarlo:

```bash
./nds2wiiu.py recomendar --rom juego.zip --buscar-base
```

Raspa varios buscadores con [ddgs](https://pypi.org/project/ddgs/), abre las
primeras páginas y **te muestra los fragmentos donde se nombra el juego**, con
el enlace al lado. No pide clave, no cuesta nada y no consulta ningún modelo de
lenguaje: la conclusión la sacás vos leyendo.

Solo muestra fragmentos de páginas que además hablen de inyecciones. La ficha
de Wikipedia de la película de Narnia nombra el juego veinte veces y no dice
nada del tema; sin ese filtro, el resultado era ruido con forma de hallazgo.

**Hubo dos modelos de lenguaje acá, y los dos se fueron.** Vale la pena contar
por qué, porque es el tipo de pieza que se agrega sin pensarla:

El primero tenía acceso a internet y buscaba por su cuenta. Eso obligaba a un
modelo de pago, y la regla que exigía citar una fuente comprobaba solo que la
respuesta *tuviera forma* de dirección web — un modelo sin buscador podía
escribir una inexistente y pasar el filtro.

El segundo ya no buscaba: la herramienta buscaba y abría las páginas, y el
modelo solo leía y elegía. Mejor, y suficiente para que alcanzara un modelo
gratuito. Pero medido sobre un caso real, leyó tres páginas y contestó *«no hay
información sobre este juego»* — exactamente lo que ve cualquiera que abra esas
páginas. Para eso no hacen falta una clave, una cuota diaria ni una
dependencia más.

Lo que llena el hueco de los juegos que no figuran en ninguna lista no es un
modelo: es gente probando y anotando. Por eso existe `anotar`.

### Configuración

Para no repetir lo mismo cada vez, en `~/.config/nds2wiiu/config.ini`:

```ini
[nds2wiiu]
consola = 192.168.1.50
otp = ~/claves/otp.bin
nuspacker = ~/herramientas/NUSPacker.jar
```

No hay nada más que configurar: ninguna parte de esta herramienta pide una
cuenta, una clave de API ni un servicio de terceros.

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

**La ROM puede ir comprimida.** Acepta `.nds`, `.srl` y `.zip` — que es como
circulan casi todas. De un `.zip` solo lee los primeros 512 bytes para sacar el
código del juego, sin descomprimir nada; descomprime entero recién al inyectar,
en un temporal que borra al terminar. Los `.7z` no, y lo dice en lugar de fallar
de forma rara.

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

La lista de compatibilidad de `datos/compatibilidad-gbatemp.csv` **no es obra de
este proyecto**: la mantiene la comunidad de GBAtemp en
[este hilo](https://gbatemp.net/threads/new-wii-u-nds-injection-compatibility-list.605592/),
y se incluye como copia de respaldo, sin modificar y con atribución. Si quien la
mantiene prefiere que no se distribuya acá, basta con abrir un issue y se quita.
