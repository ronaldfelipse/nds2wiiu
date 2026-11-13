# Procedencia de `compatibilidad-gbatemp.csv`

Este archivo **no es obra de este proyecto**. Es una copia de respaldo de la
lista de compatibilidad de inyecciones de Nintendo DS en Wii U que mantiene la
comunidad.

| | |
|---|---|
| Fuente | <https://gbatemp.net/threads/new-wii-u-nds-injection-compatibility-list.605592/> |
| Hoja de cálculo | <https://docs.google.com/spreadsheets/d/1-2OTotf1p2kz7DzfcxiY-iLWoqvl14wLn4sZ9uEjHsg/edit> |
| Mantiene | el usuario **NecroNova** de GBAtemp, con aportes de otros miembros del hilo |
| Copia tomada el | 2026-11-12 |
| Contenido | 539 juegos con su estado y, cuando difiere de la base por defecto, la base usada |

## Por qué hay una copia acá

La herramienta **siempre intenta bajar la versión actual** y guarda lo que baja
en `~/.cache/nds2wiiu/`. Esta copia solo se usa como último recurso: cuando no
hay internet y tampoco hay caché, por ejemplo en un clon recién hecho.

Existe porque la fuente es una hoja de cálculo personal enlazada desde un hilo
de foro de 2022. No tiene ninguna garantía de permanencia: si el enlace se cae
o cambia de permisos, sin esta copia el proyecto perdería su mejor fuente de
datos y nadie podría reconstruirla.

Cuando se use esta copia, la herramienta lo dice en la salida junto con la
fecha, para que quede claro que se está leyendo algo potencialmente viejo.

## Qué es y qué no

Son **datos de compatibilidad medidos**: qué juego arranca con qué base. Se
incluyen con atribución y sin modificar. Si quien los mantiene prefiere que no
se distribuyan acá, se quitan: basta con abrir un issue.

---

# Procedencia de `bases-ds.json`

Los **93 títulos de Consola Virtual de DS** que salieron para Wii U —31 juegos
en tres regiones—, con su identificador de título, su código de producto y su
región.

| | |
|---|---|
| Fuente | <https://wiiubrew.org/wiki/Title_database> |
| Mantiene | la comunidad de WiiUBrew |
| Copia tomada el | 2026-11-13 |

Sirve para una sola cosa: cuando la lista de compatibilidad recomienda una base
por su nombre —«[USA] New Super Mario Bros.»—, poder decir también **cuál es su
identificador exacto**. Sin eso, un nombre parecido lleva al archivo
equivocado: hay versiones de Wii, de Wii U y remakes que se llaman casi igual.

Son identificadores públicos, no claves: no sirven para descargar ni descifrar
nada.

---

# Procedencia de `plantillas/`

Los marcos con la estetica de Consola Virtual sobre los que se componen el
icono y la pantalla de arranque.

| | |
|---|---|
| Fuente | <https://github.com/stuff-by-3-random-dudes/UWUVCI-AIO-WPF> |
| Archivos originales | `Resources/NDS.png` y `Resources/NDS Alt2.png` |
| Licencia | GPL-3, la misma que este proyecto |
| Copia tomada el | 2026-11-13 |

Se renombraron a `nds-pantalla.png` (1280x720) y `nds-icono.png` (128x128);
el contenido no se modifico.

Las coordenadas con las que se compone encima —el hueco de la caratula, las
dos lineas del nombre, el anio y la cantidad de jugadores— se leyeron de
`Classes/BootImage.cs` del mismo proyecto.

UWUVCI AIO es GPL-3 y este proyecto tambien, asi que la reutilizacion es la
que esa licencia contempla: se mantiene la licencia y se reconoce el origen.

---

# Procedencia de `compatibilidad-uwuvci.json`

La segunda lista de compatibilidad, en JSON, con un campo por dato.

| | |
|---|---|
| Fuente | <https://github.com/UWUVCI-PRIME/UWUVCI-Compatibility> |
| Archivo original | `NDSCompat.json` |
| Mantiene | la comunidad de UWUVCI, con un bot de Discord |
| Copia tomada el | 2026-11-13 |
| Contenido | 323 reportes sobre 282 juegos, con base y region en campos propios |

Alimenta el sitio <https://uwuvci.net/n64compat> y sus equivalentes por consola.

## Por que hay DOS listas y no una

Se midio el solapamiento antes de decidir:

| | |
|---|---|
| solo en GBAtemp | 454 juegos |
| solo en UWUVCI | 199 juegos |
| en las dos | 79 juegos |
| union | **732 juegos** |

Quedarse con una sola —cualquiera de las dos— tiraba mas de lo que ganaba.

Cuando las dos conocen el mismo juego gana UWUVCI, porque su dato es mejor:
cada entrada dice que base se uso de verdad, mientras que en la hoja de GBAtemp
512 de 533 la heredan de un "salvo que se indique" y son suposiciones.

Ese detalle cambia los numeros que la herramienta informa: contando solo bases
reportadas, New Super Mario Bros. (USA) aparece en 65 de 260 juegos, un 25%, y
no en el 95% que sugeriria la regla de la hoja.

## Que es y que no

Son **datos de compatibilidad medidos** por quienes probaron cada combinacion.
Se incluyen con atribucion y sin modificar, como copia de respaldo para cuando
no hay internet. Si quienes los mantienen prefieren que no se distribuyan aca,
basta con abrir un issue.
