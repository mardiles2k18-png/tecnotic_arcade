# Graph Report - tecnotic_arcade  (2026-11-26)

## Corpus Check
- 34 files · ~24,550 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 15 file(s) not represented in the graph (top: .ttf 5, (none) 3, .xml 3)

## Summary
- 332 nodes · 554 edges · 34 communities (15 shown, 19 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 8 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d8624ad3`
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

## God Nodes (most connected - your core abstractions)
1. `Bienvenida` - 53 edges
2. `Ventana` - 49 edges
3. `Nativo` - 15 edges
4. `Tecnotics Arcade` - 11 edges
5. `DialogoPin` - 10 edges
6. `tecnotic_arcade — instrucciones para los agentes` - 9 edges
7. `Bitácora de sesiones` - 7 edges
8. `Configuracion` - 7 edges
9. `Estado` - 7 edges
10. `Plan: Tecnotics Arcade con Windows 10 LTSC + RetroBat` - 7 edges

## Surprising Connections (you probably didn't know these)
- `Bienvenida` --inherits--> `Form`  [EXTRACTED]
  modo-arcade/TecnoticsArcade.cs →   _Bridges community 1 → community 4_
- `Bienvenida` --references--> `Mando`  [EXTRACTED]
  modo-arcade/TecnoticsArcade.cs → modo-arcade/TecnoticsArcade.cs  _Bridges community 1 → community 20_

## Import Cycles
- None detected.

## Communities (34 total, 19 thin omitted)

### Community 0 - "tecnotic_arcade — instrucciones para los agentes"
Cohesion: 0.20
Nodes (9): Al cerrar la sesión ("cerramos sesión"), Al empezar una sesión ("vamos a tecnotic_arcade"), Cómo hablar con el usuario, Datos técnicos, Equipo (roles), graphify, Memoria del proyecto, Mientras trabajas (+1 more)

### Community 2 - "Estado actual"
Cohesion: 0.11
Nodes (15): 2026-11-25 — Codex, 2026-11-25 — Generador de Proyectos IA Tecnotics, 2026-11-26 — Codex, 2026-11-26 — Codex · Adaptación de temas, 2026-11-26 — Codex · Migrar RetroBat, 2026-11-26 — Codex · TeknoParrot en un disco de otro PC, Bitácora de sesiones, Bloqueos o dudas abiertas (+7 more)

### Community 4 - "Ventana"
Cohesion: 0.08
Nodes (6): DialogoPin, Actual, Nuevo, Repetido, Ventana, AlTerminar

### Community 11 - "generar_recursos.py"
Cohesion: 0.12
Nodes (15): arte_tema(), boot_logo(), con_brillo(), fondo_base(), fotograma(), logo_vertical(), main(), pegar_centrado() (+7 more)

### Community 12 - "Configurador.cs"
Cohesion: 0.12
Nodes (5): Programa, TecnoticsConfigurador, TecnoticsArcade, Programa, Registro

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
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 144 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **19 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Bienvenida` connect `Bienvenida` to `Ventana`, `Configurador.cs`, `Nativo`, `Estado`, `Mando`?**
  _High betweenness centrality (0.174) - this node is a cross-community bridge._
- **What connects `Arcade`, `Botones`, `CuentaAtras` to the rest of the system?**
  _9 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Bienvenida` be split into smaller, more focused modules?**
  _Cohesion score 0.07615018508725542 - nodes in this community are weakly interconnected._
- **Why does `Ventana` connect `Ventana` to `Bienvenida`, `Configurador.cs`?**
  _High betweenness centrality (0.126) - this node is a cross-community bridge._
- **Should `Estado actual` be split into smaller, more focused modules?**
  _Cohesion score 0.1111111111111111 - nodes in this community are weakly interconnected._
- **Why does `Nativo` connect `Nativo` to `Configurador.cs`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Should `Ventana` be split into smaller, more focused modules?**
  _Cohesion score 0.08395989974937343 - nodes in this community are weakly interconnected._