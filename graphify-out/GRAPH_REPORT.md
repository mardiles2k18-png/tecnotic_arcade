# Graph Report - tecnotic_arcade  (2026-11-28)

## Corpus Check
- 35 files · ~25,731 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 15 file(s) not represented in the graph (top: .ttf 5, (none) 3, .xml 3)

## Summary
- 342 nodes · 563 edges · 35 communities (17 shown, 18 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 8 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b43716a8`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- tecnotic_arcade — instrucciones para los agentes
- Bienvenida
- Estado actual
- CLAUDE.md
- Ventana
- Decisiones
- diseno/README.md
- ideas/README.md
- investigacion/README.md
- planes/README.md
- guardar.sh
- generar_recursos.py
- Configurador.cs
- Nativo
- Tecnotics Arcade
- Gestor Arcade Tecnoticis 33 Implementation Plan
- Plan: Tecnotics Arcade con Windows 10 LTSC + RetroBat
- Estado
- Tema Tecnotics basado en AluBrush
- Registro de cambios · Tecnotics Arcade
- Mando
- tecnotics-wine.sh
- configurador/LEEME.md
- modo-arcade/LEEME.md
- instalar-logo-arranque.sh
- compilar.sh
- CREDITOS.md
- configurar-placa-hp.sh
- Mando

## God Nodes (most connected - your core abstractions)
1. `Bienvenida` - 53 edges
2. `Ventana` - 49 edges
3. `Nativo` - 15 edges
4. `Tecnotics Arcade` - 11 edges
5. `tecnotic_arcade — instrucciones para los agentes` - 10 edges
6. `DialogoPin` - 10 edges
7. `Bitácora de sesiones` - 9 edges
8. `Configuracion` - 7 edges
9. `Estado` - 7 edges
10. `Plan: Tecnotics Arcade con Windows 10 LTSC + RetroBat` - 7 edges

## Surprising Connections (you probably didn't know these)
- `Bienvenida` --inherits--> `Form`  [EXTRACTED]
  modo-arcade/TecnoticsArcade.cs →   _Bridges community 1 → community 4_
- `Bienvenida` --references--> `Mando`  [EXTRACTED]
  modo-arcade/TecnoticsArcade.cs → modo-arcade/TecnoticsArcade.cs  _Bridges community 1 → community 34_

## Import Cycles
- None detected.

## Communities (35 total, 18 thin omitted)

### Community 0 - "tecnotic_arcade — instrucciones para los agentes"
Cohesion: 0.18
Nodes (10): Al cerrar la sesión ("cerramos sesión"), Al empezar una sesión ("vamos a tecnotic_arcade"), Cómo hablar con el usuario, Datos técnicos, Equipo (roles), Gemini en el equipo, graphify, Memoria del proyecto (+2 more)

### Community 1 - "Bienvenida"
Cohesion: 0.07
Nodes (3): Bienvenida, Configuracion, Registro

### Community 2 - "Estado actual"
Cohesion: 0.10
Nodes (17): 2026-11-25 — Codex, 2026-11-25 — Generador de Proyectos IA Tecnotics, 2026-11-26 — Codex, 2026-11-26 — Codex · Adaptación de temas, 2026-11-26 — Codex · Migrar RetroBat, 2026-11-26 — Codex · TeknoParrot en un disco de otro PC, 2026-11-27 — Claude · Juegos NAOMI y otros de la descarga TeknoParrot, 2026-11-28 — Codex · Gestor 45 y consolidación de ROMs (+9 more)

### Community 4 - "Ventana"
Cohesion: 0.09
Nodes (6): DialogoPin, Actual, Nuevo, Repetido, Ventana, AlTerminar

### Community 11 - "generar_recursos.py"
Cohesion: 0.12
Nodes (15): arte_tema(), boot_logo(), con_brillo(), fondo_base(), fotograma(), logo_vertical(), main(), pegar_centrado() (+7 more)

### Community 12 - "Configurador.cs"
Cohesion: 0.13
Nodes (4): Programa, TecnoticsConfigurador, TecnoticsArcade, Programa

### Community 13 - "Nativo"
Cohesion: 0.21
Nodes (3): Nativo, LSA_OBJECT_ATTRIBUTES, LSA_UNICODE_STRING

### Community 14 - "Tecnotics Arcade"
Cohesion: 0.13
Nodes (14): 1. Vídeo de inicio, 2. Tema, 3. Logo fijo del primer instante, Al encender la máquina, Batocera enseña tres pantallas, Configuración de la placa HP ProOne 400 G2, Contenido, Instalación, Juegos de Windows: preparación automática (+6 more)

### Community 15 - "Gestor Arcade Tecnoticis 33 Implementation Plan"
Cohesion: 0.20
Nodes (8): Actualización desde el Gestor, Gestor Arcade Tecnoticis 33, 1. Nombre y versión, 2. Modo arcade, 3. Vista de mandos, 4. Actualización desde la aplicación, 5. Entrega, Gestor Arcade Tecnoticis 33 Implementation Plan

### Community 16 - "Plan: Tecnotics Arcade con Windows 10 LTSC + RetroBat"
Cohesion: 0.25
Nodes (7): Fase 1: Windows mínimo (con internet, por última vez), Fase 2: probar los juegos de Windows, Fase 3: RetroBat, Fase 4: controles, Fase 5: modo quiosco (eliminar rastros de Windows), Fase 6: copia maestra, Plan: Tecnotics Arcade con Windows 10 LTSC + RetroBat

### Community 17 - "Estado"
Cohesion: 0.29
Nodes (7): Estado, Arcade, Botones, CuentaAtras, EnWindows, Menu, Pin

### Community 18 - "Tema Tecnotics basado en AluBrush"
Cohesion: 0.29
Nodes (6): Estado de validación, Instalar, Logo, Sistemas nuevos (versión 0.3), Tema Tecnotics basado en AluBrush, Uso

### Community 19 - "Registro de cambios · Tecnotics Arcade"
Cohesion: 0.33
Nodes (5): 1.0.0 — 2026-11-20, 1.1.0 — 2026-11-20, 1.1.1 — 2026-11-20, 1.2.0 — 2026-11-20, Registro de cambios · Tecnotics Arcade

### Community 20 - "Mando"
Cohesion: 0.29
Nodes (6): Capcom Vs. SNK: Millennium Fight 2000 — ¿a qué sistema pertenece?, Conclusión, Cómo usarlo en el arcade, Fuentes, Los otros juegos de la misma descarga, Qué hay en la carpeta

### Community 21 - "tecnotics-wine.sh"
Cohesion: 0.73
Nodes (5): bin_runner(), log(), preparar_prefijo(), preparar_todos(), tecnotics-wine.sh script

### Community 22 - "configurador/LEEME.md"
Cohesion: 0.40
Nodes (4): Compilar, Ediciones de Windows, Pestañas, Una sola cuenta

### Community 23 - "modo-arcade/LEEME.md"
Cohesion: 0.50
Nodes (3): Cómo funciona (una sola cuenta), Parámetros, Si algo falla al arrancar

## Knowledge Gaps
- **9 isolated node(s):** `Arcade`, `Botones`, `CuentaAtras`, `EnWindows`, `Menu` (+4 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 153 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **18 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Bienvenida` connect `Bienvenida` to `Mando`, `Ventana`, `Configurador.cs`, `Nativo`, `Estado`?**
  _High betweenness centrality (0.164) - this node is a cross-community bridge._
- **What connects `Arcade`, `Botones`, `CuentaAtras` to the rest of the system?**
  _9 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Bienvenida` be split into smaller, more focused modules?**
  _Cohesion score 0.07322068612391193 - nodes in this community are weakly interconnected._
- **Why does `Ventana` connect `Ventana` to `Bienvenida`, `Configurador.cs`?**
  _High betweenness centrality (0.118) - this node is a cross-community bridge._
- **Should `Estado actual` be split into smaller, more focused modules?**
  _Cohesion score 0.1 - nodes in this community are weakly interconnected._
- **Why does `Nativo` connect `Nativo` to `Configurador.cs`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Should `Ventana` be split into smaller, more focused modules?**
  _Cohesion score 0.08636363636363636 - nodes in this community are weakly interconnected._