---
name: elegir-ia
description: Úsala al recibir cada pedido nuevo del usuario (una investigación, un cambio de código, un diseño, una integración, un texto) para recomendar en una línea qué IA del equipo (Claude, Codex o Gemini), qué modelo y qué nivel de esfuerzo conviene usar y así no gastar créditos de más. También cuando el usuario pregunte «¿qué IA uso?», «¿con cuál conviene?», «¿cuánta cuota me queda?» o «ahorra créditos».
license: MIT
---

# Elegir IA

El equipo tiene tres IA: **Claude** y **Codex** (planes de pago con cuota por
ventanas de 5 horas y semanal) y **Gemini** en Antigravity (gratis, cuota
semanal). Tu trabajo es que cada tarea la haga la IA más barata que la pueda
hacer bien.

## Cuándo

Al empezar cada pedido nuevo, antes de trabajar. No lo repitas en cada
mensaje de una misma tarea.

## Cómo decidir

1. Clasifica el pedido con la tabla. Si mezcla varios tipos, usa el más
   exigente.
2. Revisa la cuota (ver «Cuota») y, si la IA elegida está baja, pasa a la
   siguiente opción.
3. Responde con **una línea** al inicio, en palabras simples:

   > Recomendación: **Gemini (Flash, esfuerzo bajo)**, porque es una
   > investigación con búsquedas y así no gastamos cuota de pago.

4. Si la IA recomendada **eres tú**, sigue con la tarea.
5. Si es **otra**, dilo y ofrece dos caminos: seguir aquí igual (gasta más)
   o cambiar. Para cambiar, deja una nota con `memoria-de-chat`, libera el
   turno en `docs/ESTADO.md` y dile al usuario qué botón pulsar en el
   Generador («Trabajar con Claude», «Trabajar con Codex» o «Trabajar con
   Gemini»). El usuario decide; nunca cambies sin preguntar.

## Tabla de tareas

| Tipo de tarea | 1.ª opción | 2.ª opción | Esfuerzo |
|---|---|---|---|
| Investigar, buscar, comparar, resumir fuentes | Gemini (Flash) | Codex (modelo ligero) | Bajo |
| Textos, documentos, bitácora, traducciones, ordenar ideas | Gemini (Flash) | Claude (Haiku) | Bajo |
| Cambios pequeños de código, corregir un error claro | Codex (modelo intermedio) | Claude (Sonnet) | Medio |
| Programar una función nueva, pruebas, revisar código | Codex (modelo intermedio) | Claude (Sonnet) | Medio |
| Diseño gráfico, imágenes, maquetas, piezas en Canva | Codex (modelo intermedio) | Claude (Sonnet) | Medio |
| Integraciones (conectores, Canva, APIs), automatizar, arquitectura, planes grandes | Claude (Opus) | Codex (modelo más capaz) | Alto |
| Auditoría de seguridad, errores difíciles, cambios en muchos archivos | Claude (Opus) | Codex (modelo más capaz) | Alto |

Modelos de referencia (noviembre de 2026; confirma el nombre exacto en el
selector de modelos de cada app):

- **Claude**: Haiku (ligero), Sonnet (intermedio), Opus (más capaz). El
  esfuerzo se elige en Claude Code (bajo, medio, alto, máximo). Opus gasta la
  cuota bastante más rápido.
- **Codex**: el selector de la app ofrece un modelo ligero (muchos más
  mensajes por ventana), uno intermedio y el más capaz (pocos mensajes). Úsalo
  con esfuerzo de razonamiento bajo, medio o alto según la tabla.
- **Gemini (Antigravity gratis)**: Flash para casi todo. Los modelos más
  capaces gastan rápido la cuota semanal.

## Cuota

El Generador guarda la última lectura de «Uso de IA» en
`~/.proyectos-ia/uso-ia.json` (en Windows,
`C:\Users\<usuario>\.proyectos-ia\uso-ia.json`). Cada IA tiene `fecha` y
`lineas` (por ejemplo «5 h: 35 % restante · se reinicia 14:20»).

- Si el archivo existe y tiene menos de 12 horas, úsalo.
- Si la IA elegida tiene **menos de 20 % restante** en su ventana de 5 horas
  o semanal, recomienda la siguiente opción y dilo («a Claude le queda 15 %
  esta semana»).
- Si no hay datos o son viejos, decide solo con la tabla y sugiere abrir
  «Uso de IA» en el Generador para actualizar.

## Reglas

- Una línea, sin tecnicismos. No conviertas la recomendación en una consulta
  larga.
- Para datos sensibles (pacientes, datos de la institución) da igual cuál de
  las tres se use, pero nunca derives el trabajo a una IA fuera del equipo.
- Si el usuario ya eligió una IA o un modelo, respeta su decisión y solo
  avisa si se va a quedar sin cuota.
