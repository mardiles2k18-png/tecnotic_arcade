---
name: marca-tecnotics
description: Identidad visual de Tecnotics, con logos, colores y tipografía oficiales y reglas de contraste. Úsala siempre que algo del proyecto deba verse como Tecnotics, como pantallas, ventanas de Windows (WinForms, WPF), páginas web, temas, íconos, instaladores, manuales, afiches o el README, o cuando el usuario pida «con la marca», «con los colores de Tecnotics» o «pon el logo».
---

# Marca Tecnotics

Todo lo visual de un proyecto Tecnotics parte de aquí. El rol
`disenador-grafico` decide cómo aplicarla y el `programador-analista` la usa
como variables, nunca con colores escritos a mano en el código.

## Archivos de esta skill

| Archivo | Uso |
|---|---|
| `logos/tecnotics-horizontal.png` | Cabeceras y barras (fondo transparente) |
| `logos/tecnotics-vertical.png` | Portadas, bienvenida, README |
| `logos/tecnotics-fondo-negro.jpg` | Redes sociales y avatar (cuadrado, fondo negro) |
| `logos/icono-32.png`, `icono-64.png`, `icono-256.png`, `tecnotics.ico` | Solo el chip: íconos de ventana, accesos directos, favicon |
| `tokens.json` | Todos los colores y la tipografía, como variables |

Copia al proyecto solo los archivos que uses, en su carpeta de recursos
(por ejemplo `assets/`, `public/images/` o `Resources/`), y anota en
`docs/diseno/GUIA.md` del proyecto de dónde vienen.

## Colores

| Token | HEX | Para qué |
|---|---|---|
| `marca.cian` | `#6EC6D8` | Color principal: acentos, selección, detalles |
| `marca.naranja` | `#F18E19` | Acción: botón principal de cada pantalla |
| `oscuro.fondo` | `#111418` | Cabeceras y superficies oscuras |
| `claro.fondo` / `claro.superficie` | `#F4F7F8` / `#FFFFFF` | Fondos donde se lee mucho |
| `claro.texto` | `#1A1D21` | Texto principal |
| `texto_de_marca.cian` / `.naranja` | `#1C7A8C` / `#A85600` | Cian y naranja oscurecidos para **texto** sobre fondo claro |
| `estado.ok` / `pendiente` / `atrasado` | `#1B7F3B` / `#A85600` / `#B3261E` | Estados, siempre acompañados de una palabra |

### Regla de oro

El cian y el naranja del logo **nunca van como letras sobre fondo claro**
(contraste 1,96 y 2,44: ilegible). Tienen dos usos válidos:

- Como **fondo**, con texto oscuro `#111418` encima. Así son los botones principales.
- Como **texto sobre fondo oscuro**: cian sobre negro tiene contraste 10,73 y naranja sobre negro, 8,62.

Para texto en cian o naranja sobre fondo claro usa `texto_de_marca`.
Todo texto debe tener un contraste de 4,5:1 como mínimo.

## Logo

- No deformarlo ni recolorearlo. El fondo es transparente y funciona sobre
  fondo claro u oscuro.
- Dejar alrededor un margen libre de al menos la altura de un «pin» naranja del chip.
- Por debajo de 32 px usar solo el chip (los íconos), sin la palabra TECNOTICS.
- La letra del logo es parte de la imagen. No se intenta imitar con una fuente.

## Tipografía

- Programas de Windows: **Segoe UI**. Títulos en negrita y texto a 10 pt.
  Rutas y registros en **Consolas**.
- Web: `"Segoe UI", system-ui, sans-serif` (o la que defina la guía del
  proyecto, si el diseñador la aprueba).

## Cómo aplicarla según el tipo de proyecto

- **Web (CSS / Tailwind)**: define los tokens como variables
  (`--tecnotics-cian: #6EC6D8;`…) o en `tailwind.config` y usa solo esas variables.
- **WPF**: un `ResourceDictionary` (`Themes/Tecnotics.xaml`) con
  `SolidColorBrush` por token, por ejemplo `x:Key="MarcaCian"`.
- **WinForms**: una clase estática `ColoresTecnotics` con un `Color` por token.
- **Python / tkinter**: lee `tokens.json` (no copies los HEX en el código).
- **Temas de terceros** (RetroBat, EmulationStation…): respeta el formato del
  tema y toma los colores de `tokens.json`.
- **Estructura típica de pantalla**: cabecera oscura con el logo horizontal,
  cuerpo claro, un botón principal naranja con texto oscuro y selección cian
  con texto oscuro.

## Reglas

- Los estados se muestran con color **y** con palabras ("al día", "atrasado").
- Si un proyecto necesita un color nuevo, propónlo al usuario y anótalo en
  `docs/diseno/GUIA.md` del proyecto y en `docs/DECISIONES.md`.
- Cualquier cambio a la marca en sí (logo, colores base) se hace en la guía
  oficial del Generador de Proyectos IA Tecnotics, no en un proyecto suelto.
