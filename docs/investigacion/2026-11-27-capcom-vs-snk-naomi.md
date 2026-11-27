# Capcom Vs. SNK: Millennium Fight 2000 — ¿a qué sistema pertenece?

**Fecha:** 2026-11-27 · **Rol:** Investigador · **Autor:** Claude

Carpeta revisada (solo lectura, no se ejecutó nada):
`C:\Users\Tecnotics\Downloads\Teknoparrot\Capcom Vs. SNK - Millennium Fight 2000 (2000)[Sega NAOMI][TP]`

## Conclusión

- **Sistema original:** placa arcade **Sega NAOMI** (Capcom, año 2000). Es un juego en
  **cartucho**, no en disco GD-ROM.
- **Formato de los archivos:** es el juego de MAME llamado `capsnk`, **descomprimido**, con las
  **BIOS de NAOMI mezcladas** en la misma carpeta.
- **Lanzador:** la etiqueta `[TP]` significa que viene de un paquete para **TeknoParrot**.
  La lista oficial de TeknoParrot incluye este juego en "Sega NAOMI" como **Perfect**.
- **En RetroBat** corresponde al sistema **`naomi`**, con Flycast (código abierto) o Demul.

## Qué hay en la carpeta

| Archivos | Qué son |
|---|---|
| `epr-23511c.ic22` + `mpr-23504.ic1` … `mpr-23510.ic7` | El juego, revisión C (versión principal). |
| `capsnka\epr-23511a.ic22` | Variante revisión A (solo cambia el programa). |
| `capsnkb\epr-23511.ic22` | Variante original, sin revisión. |
| `epr-21576*.ic27`, `epr-21577*`, `epr-21578*`, `epr-21579*`, `epr-21580a`, `naomi_boot_2491`, `develop*.ic27`, `zukinver0930.ic25` | BIOS de NAOMI de varias regiones y de desarrollo (en MAME van dentro de `naomi.zip`). |
| `315-6146.bin`, `315-6188.ic31`, `315-6215.bin`, `sp5001*.bin`, `sp5002-a.bin`, `boot_rom_64b8.ic606` | Chips de la placa NAOMI y de sus tarjetas de entradas (también parte de la BIOS). |
| `main_eeprom.bin`, `x76f100_eeprom.bin` | Memorias de configuración de la placa y del cartucho. |

Las tres versiones del juego coinciden con las tres que lista TeknoParrot:
"Millennium Fight 2000", "(Rev A)" y "(Rev C)". La versión "Pro (GDL-0004)" de la lista es
otro juego en GD-ROM y **no** está en esta carpeta.

## Cómo usarlo en el arcade

1. **TeknoParrot:** usar el `.zip` original que está en `Downloads\Teknoparrot`, no la carpeta
   descomprimida. No se encontró documentación de TeknoParrot sobre qué emulador usa por dentro
   para NAOMI ni qué formato exige; hay que probarlo en el equipo.
2. **RetroBat (alternativa de código abierto):** separar los archivos en dos zip con nombres de MAME:
   - `capsnk.zip` (archivos del juego) → `roms\naomi\`
   - `naomi.zip` (archivos de BIOS) → `bios\dc\`
   El Gestor podría hacer esta separación automáticamente (idea pendiente).

## Los otros juegos de la misma descarga

| Archivo | Sistema | En TeknoParrot |
|---|---|---|
| Capcom Vs. SNK 2 (2001) | Sega NAOMI | Perfect |
| Bloody Roar 3 (2001) | Namco System 246 | Perfect |
| Dragon Ball Zenkai Battle Royale (2017) | Namco System 357 (según la etiqueta) | Sin confirmar; podría figurar como Namco System 369 |

## Fuentes

- [TeknoParrot — Compatibilidad](https://teknoparrot.com/en/Compatibility)
- [RetroBat Wiki — Sega NAOMI](https://wiki.retrobat.org/systems-and-emulators/supported-game-systems/arcade/sega/sega-naomi) (BIOS `naomi.zip` en `bios\dc`)
- [Emulation General Wiki — Sega NAOMI y variantes](https://emulation.gametechwiki.com/index.php/Sega_NAOMI_and_variants)
- [Wikipedia — Capcom vs. SNK: Millennium Fight 2000](https://en.wikipedia.org/wiki/Capcom_vs._SNK:_Millennium_Fight_2000)
