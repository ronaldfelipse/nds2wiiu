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
