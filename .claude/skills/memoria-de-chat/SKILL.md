---
name: memoria-de-chat
description: Úsala cuando el usuario pida «prepara la memoria», «resume para seguir en otro chat», «nota de traspaso» o «haz el resumen del chat», y también cuando el chat ya es largo, la conversación empieza a olvidar cosas dichas antes, repite errores o se acerca al límite de contexto. Sirve para continuar el trabajo en un chat nuevo, de la misma IA o de otra (Claude, ChatGPT, Gemini, Codex).
license: MIT
---

# Memoria de chat

Los chats muy largos hacen que la IA olvide y se equivoque. Esta skill deja una
**nota de memoria** ordenada para seguir en un chat nuevo sin perder el hilo.
La herramienta Tecnotics reconoce la nota por su título exacto, así que el
formato de abajo es obligatorio.

## Cuándo ofrecerla tú

Si el chat ya es largo (muchos mensajes, archivos grandes o varias horas de
trabajo), o notas que olvidas o repites cosas, dilo en una frase:
«Este chat ya es largo; ¿preparo la nota de memoria para seguir en uno nuevo?».
Hazla antes de que el chat esté muy lleno: con el contexto lleno el resumen sale peor.

## La nota: siempre este formato

Escribe la nota en un solo bloque de texto, con este título exacto en la primera
línea y esta línea final exacta. Completa todas las secciones; si una no
aplica, escribe «Nada».

```
## Nota de memoria · Tecnotics
Fecha: AAAA-MM-DD HH:MM · IA: <Claude | ChatGPT | Gemini | Codex> · Chat: <título del chat>
Proyecto: <nombre del proyecto, o «sin proyecto»>

### Objetivo
<Qué se quiere lograr, en 1 a 3 frases.>

### Decisiones tomadas
- <Decisión> — <por qué>. (No se vuelven a discutir.)

### Hecho
- <Qué quedó terminado, con su resultado.>

### Falta
- <Siguiente paso concreto, primero el más importante.>

### Datos importantes
- <Nombres, enlaces, archivos, rutas, cifras, versiones, colores… lo que el chat nuevo necesita tal cual.>

### Para el chat nuevo
- Rol: <jefe de proyecto | programador | diseñador | investigador>
- Skills: <las que conviene usar>
- Primera indicación sugerida: «<frase para pegar al empezar>»

Fin de la nota de memoria
```

## Reglas del contenido

- Solo hechos del chat. Si algo es una suposición, márcalo como «(por confirmar)».
- Lo que ya está guardado en un archivo, plan o repositorio se cita por su nombre
  o enlace, sin copiarlo entero.
- Reemplaza claves, contraseñas, tokens y datos personales por «[oculto]».
- Escribe en palabras simples: la nota también la lee el usuario.

## Dónde dejarla

- **Si trabajas en un proyecto con repositorio** (hay `AGENTS.md` y `docs/`):
  guarda la nota en `docs/memoria/AAAA-MM-DD-HHMM-<ia>.md`. En la línea «Chat:»
  añade al final «Anterior: <archivo de la nota anterior>» si existe. Luego haz
  commit y push como cualquier avance.
- **Si es un chat web** (ChatGPT, Claude o Gemini en el navegador o la app):
  entrega la nota en el chat. Después di: «Cópiala y, en un chat nuevo, pégala
  como primer mensaje. En la herramienta Tecnotics puedes guardarla en el
  proyecto con "Chats de IA" → "Guardar nota en un proyecto"».

## Al empezar un chat con una nota

Si el primer mensaje trae una «Nota de memoria · Tecnotics», o en
`docs/memoria/` hay notas: lee la más reciente, resume en 3 líneas dónde
quedamos y propone el siguiente paso de «Falta». No vuelvas a preguntar lo que
ya está en «Decisiones tomadas».

Basada en ideas de las skills de traspaso open source `handoff`
(mattpocock/skills, MIT) y `session-handoff` (forest/agent-skills, MIT).
