---
name: traducir_xml
description: Traduce libros técnicos desde XML (español) a inglés académico (británico), preservando estructura, código, fórmulas y tipografía. Exporta XML final.
user-invocable: true
---

# /traducir_xml

## Objetivo

Ejecutar un pipeline completo y seguro para traducir documentos técnicos en formato `.xml` desde español a inglés académico (British English), orientado a estudiantes de pregrado.

El pipeline garantiza:

- preservación estructural total
- preservación tipográfica (negrita, cursiva, etc.)
- preservación técnica (código, fórmulas, rutas, referencias)
- consistencia terminológica
- salida final en `.xml` lista para publicación
- compatibilidad con exportación a GitHub

---

# 🔁 Pipeline Obligatorio

El flujo debe ejecutarse **estrictamente en este orden**:

- XML INPUT
- Extract (estructura + estilos)
- Normalize (estructura intermedia)
- Block segmentation
- Block classification
- Content protection (placeholders)
- Translation (por tipo de bloque)
- Restore protected content
- Validation
- Second-pass review
- XML reconstruction
- (optional) GitHub export

---

# 1. INPUT

## Formato requerido

Se aceptan dos tipos de entrada:

1. Archivo local `.xml`
2. URL de GitHub que apunte a un archivo `.xml` o a un repositorio que lo contenga

## Soporte para GitHub URL

Si la entrada es una URL de GitHub:

- detectar si es:
  - archivo directo (`.xml`)
  - repositorio
  - carpeta dentro de un repositorio

### Reglas

- Si es un archivo `.xml`:
  - descargarlo directamente

- Si es un repositorio:
  - clonar o acceder al contenido
  - buscar automáticamente archivos `.xml`
  - si hay varios, seleccionar:
    - el principal (por nombre más relevante) o
    - solicitar selección si el sistema lo permite

- Si es una carpeta:
  - listar archivos `.xml` dentro de esa ruta
  - seleccionar según criterio anterior

## Restricciones

- No asumir credenciales privadas
- Solo procesar contenido accesible públicamente
- No modificar el repositorio fuente
- No subir cambios al mismo repositorio de entrada

## Resultado esperado

El sistema debe resolver la URL y convertirla en un `.xml` válido para continuar el pipeline estándar.

## Contenido esperado

Puede incluir:

- capítulos, secciones, subsecciones
- texto académico
- teoremas, definiciones, pruebas
- ejercicios
- código fuente
- comandos de consola
- fórmulas matemáticas
- tablas
- captions
- referencias

---

# 2. EXTRACCIÓN (XML → ESTRUCTURA)

## Objetivo

Convertir el `.xml` en una representación estructurada interna sin perder:

- jerarquía de headings
- numeración
- estilos (bold, italics, etc.)
- tablas
- listas
- bloques de código
- ecuaciones

## Reglas

- No perder contenido
- No colapsar párrafos
- No alterar orden
- Mantener metadatos de estilo por bloque

---

# 3. NORMALIZACIÓN

Convertir el documento en una estructura intermedia tipo Markdown enriquecido o JSON estructurado.

Debe permitir:

- segmentación clara
- clasificación posterior
- reconstrucción fiel

---

# 4. SEGMENTACIÓN EN BLOQUES

Dividir el documento en bloques semánticos:

Ejemplos:
- heading
- paragraph
- theorem
- proof
- example
- exercise
- code_block
- math_block
- table
- caption
- reference
- list_item

Cada bloque debe:
- mantener orden
- mantener metadata de estilo
- ser autónomo para traducción

---

# 5. CLASIFICACIÓN DE BLOQUES

Asignar un tipo a cada bloque.

Tipos soportados:

- chapter_title
- section_title
- subsection_title
- prose
- definition
- theorem
- lemma
- proposition
- corollary
- proof
- example
- exercise
- question
- algorithm
- table
- figure_caption
- math_inline
- math_block
- code_block
- console_command
- reference
- quote
- callout
- footnote
- filename
- path
- url
- list_item

---

# 6. PROTECCIÓN DE CONTENIDO

Antes de traducir, proteger contenido sensible.

## Debe protegerse:

- código
- fórmulas
- URLs
- referencias
- comandos
- rutas
- nombres de archivo
- identificadores
- variables
- símbolos matemáticos

## Usar placeholders:

Ejemplos:
- {{CODE_BLOCK_001}}
- {{MATH_BLOCK_002}}
- {{URL_003}}
- {{REFERENCE_004}}

## Modos:

- preserve_exact
- translate_comments_only
- preserve_notation
- preserve_identifier

---

# 7. TRADUCCIÓN POR BLOQUE

Aplicar el `AGENTS.md` + reglas específicas por tipo.

## Reglas clave

- prose → traducir completamente
- headings → traducir + mantener numeración
- code_block → traducir SOLO comentarios
- math → NO traducir notación
- table → traducir solo texto
- reference → NO traducir
- command → NO traducir

## Reglas críticas

- NO alterar código
- NO alterar fórmulas
- NO alterar rutas
- NO alterar referencias
- NO alterar identificadores
- mantener British English
- mantener consistencia terminológica

---

# 8. RESTAURACIÓN

Reemplazar placeholders con contenido original EXACTO.

Debe verificarse:

- integridad total
- sin modificaciones
- sin pérdidas

---

# 9. VALIDACIÓN

## 9.1 Estructura

- mismo número de headings
- misma jerarquía
- mismo orden

## 9.2 Técnica

- código intacto
- fórmulas intactas
- referencias intactas
- URLs intactas

## 9.3 Sintaxis

- balance de llaves {}
- balance de paréntesis ()
- balance de corchetes []
- delimitadores de código correctos

## 9.4 Terminología

- términos consistentes
- sin sinónimos innecesarios
- British English

## 9.5 Tipografía

- bold preservado
- italics preservado
- listas preservadas
- tablas preservadas

---

# 10. SECOND PASS (REVIEW)

Revisar:

- fluidez académica
- naturalidad
- consistencia
- eliminación de traducción literal
- corrección de errores

NO cambiar:
- estructura
- contenido técnico

---

# 11. RECONSTRUCCIÓN XML

## Objetivo

Generar el `.xml` final.

## Debe preservar:

- headings
- numeración
- **bold**
- *italics*
- listas
- tablas
- código
- ecuaciones
- captions

## No permitido:

- perder formato
- reordenar contenido
- simplificar estructura

---

# 12. EXPORTACIÓN A GITHUB (OPCIONAL)

Solo si está configurado:

## Flujo

1. guardar archivo `.xml`
2. nombre determinístico (ej: chapter_02_en.xml)
3. ubicar en carpeta `/output/`
4. commit
5. push

## Restricciones

- no asumir credenciales
- no inventar repo
- no fallar si no está configurado

---

# 13. REGLAS CRÍTICAS

- Nunca traducir código (excepto comentarios)
- Nunca modificar fórmulas
- Nunca traducir referencias
- Nunca alterar numeración
- Nunca inventar contenido
- Nunca agregar explicaciones no presentes
- Nunca perder formato
- Siempre entregar `.xml`

---

# 14. INVOCACIÓN

Ejemplo:

/traducir_xml archivo.xml

---

# 15. COMPORTAMIENTO ESPERADO

El sistema debe:

- ser determinista
- ser seguro para contenido técnico
- ser consistente en todo el libro
- evitar corrupción de contenido
- producir output listo para publicación académica

---

# 16. RESULTADO FINAL

El resultado debe ser:

- archivo `.xml`
- estructuralmente idéntico al original
- traducido a inglés académico
- técnicamente intacto
- legible para estudiantes
- listo para exportar o publicar
