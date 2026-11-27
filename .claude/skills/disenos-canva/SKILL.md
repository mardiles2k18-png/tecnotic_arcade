---
name: disenos-canva
description: Úsala para derivar trabajo de diseño a Canva mediante su conector oficial: afiches, presentaciones, publicaciones para redes, portadas, infografías, folletos, banners, invitaciones o certificados con la marca Tecnotics, y para buscar, editar o exportar diseños de la cuenta de Canva (PDF, PNG, JPG, PPTX, MP4). También cuando el usuario diga «hazlo en Canva», «pásaselo a Canva» o «una pieza para publicar».
license: MIT
---

# Diseños en Canva

Canva hace las piezas gráficas terminadas. Tú preparas el encargo, lo pides
por el conector, revisas el resultado y lo dejas en el proyecto.

## Antes de empezar

1. Comprueba que tienes las herramientas del conector **Canva** (por ejemplo,
   las de crear o exportar diseños). Si no aparecen o piden iniciar sesión,
   dile al usuario: «En el Generador, abre **Programas del PC** y pulsa
   **Conectar Canva**; luego inicia sesión en Canva en el navegador». No
   intentes otra vía (API, claves o páginas web).
2. Lee `marca-tecnotics` y, si existe, `docs/diseno/GUIA.md`.

## Cómo encargar una pieza

1. Aclara con el usuario lo que solo él sabe: para qué es, quién la verá,
   el texto exacto y el formato (afiche, historia, presentación…).
2. Escribe el encargo para Canva con: tipo y tamaño, texto final, colores
   HEX de la marca, tipografía de la marca, logo que corresponde (claro u
   oscuro) y el tono.
3. Pide **2 o 3 opciones** cuando el conector lo permita y muéstraselas al
   usuario con tu recomendación.
4. Ajusta la elegida (textos, colores, logo) y revisa el contraste
   (texto normal 4,5:1 como mínimo).
5. Exporta y guarda en `docs/diseno/piezas/AAAA-MM-DD-<nombre>.<ext>`.
   Anota en `docs/diseno/piezas/README.md` el nombre, el enlace del diseño en
   Canva y para qué es.

## Reglas

- Si el Kit de Marca de Canva todavía no tiene los colores y logos de
  Tecnotics, propón al usuario cargarlos (están en `assets/` y en
  `marca-tecnotics`).
- No uses elementos premium sin licencia: la exportación puede fallar.
- No subas a Canva datos sensibles (pacientes, datos personales o internos de
  la institución).
- Para pantallas de una app o maquetas HTML sigue usando `frontend-design`;
  Canva es para piezas de comunicación.
- El conector actúa con la cuenta del usuario: no borres ni compartas diseños
  sin preguntar.
