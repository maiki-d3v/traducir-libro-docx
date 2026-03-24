# traducir_libro_docx

Skill para traducir libros técnicos desde `.docx` en español a inglés académico británico, preservando estructura, tipografía y contenido técnico, y generando un `.docx` final listo para revisión o exportación.

---

## Objetivo

Este skill implementa un pipeline estructurado para traducir documentos técnicos y académicos con enfoque en:

- fidelidad semántica
- preservación estructural
- preservación tipográfica
- seguridad técnica
- consistencia terminológica
- salida final en `.docx`
- exportación opcional a GitHub

Está orientado a libros o capítulos en áreas como:

- lógica computacional
- inteligencia artificial
- inteligencia artificial simbólica
- matemáticas
- ingeniería de software
- disciplinas técnicas relacionadas

---

## Estructura del skill

```text
skills/traducir_libro_docx/
├── AGENTS.md
├── SKILL.md
├── README.md
├── .env.example
├── .gitignore
├── templates/
│   ├── master_prompt.md
│   ├── review_prompt.md
│   └── block_prompts/
│       ├── prose.md
│       ├── heading.md
│       ├── theorem.md
│       ├── proof.md
│       ├── code_block.md
│       ├── table.md
│       ├── reference.md
│       └── figure_caption.md
├── scripts/
│   ├── extract_docx.py
│   ├── segment_blocks.py
│   ├── protect_content.py
│   ├── translate_blocks.py
│   ├── restore_content.py
│   ├── validate_translation.py
│   ├── reconstruct_docx.py
│   ├── run_pipeline.py
│   └── export_github.sh
└── workspace/
    ├── input/
    ├── intermediate/
    ├── output/
    └── logs/
```

## Pipeline
El pipeline se ejecuta en este orden:

DOCX INPUT
- Extract
- Segment
- Protect
- Translate
- Restore
- Validate
- Reconstruct DOCX
- Optional GitHub export

## Requisitos

### Python
Se recomienda Python 3.11 o superior.

### Dependencias principales

Instala al menos:
```bash
pip install python-docx
```
Si luego amplías el pipeline, podrás agregar más dependencias.

## Configuración

Copia el archivo de ejemplo:

```bash
cp skills/traducir_libro_docx/.env.example skills/traducir_libro_docx/.env
```
Luego exporta las variables o cárgalas con tu método preferido.

### Variables de traducción
- TRANSLATION_PROVIDER
    - mock
    - openai_compatible
- TRANSLATION_MODEL
- OPENAI_COMPATIBLE_API_URL
- OPENAI_COMPATIBLE_API_KEY

### Variables de exportación GitHub
- GITHUB_EXPORT_REPO_PATH
- GITHUB_EXPORT_BRANCH
- GITHUB_EXPORT_TARGET_DIR
- GITHUB_EXPORT_COMMIT_MSG
- GITHUB_EXPORT_PUSH

## Modos de ejecución
1. Modo local de prueba
    Este modo no traduce realmente; deja pasar el contenido protegido para validar el pipeline.
    ```bash
    export TRANSLATION_PROVIDER=mock
    ```
2. Modo real con endpoint compatible con OpenAI
```bash
export TRANSLATION_PROVIDER=openai_compatible
export TRANSLATION_MODEL=gpt-4.1
export OPENAI_COMPATIBLE_API_URL="https://TU-ENDPOINT/v1/chat/completions"
export OPENAI_COMPATIBLE_API_KEY="TU_API_KEY"
```

## Uso rápido

Coloca tu archivo **.docx** en:

```bash
skills/traducir_libro_docx/workspace/input/
```

Ejecuta el pipeline completo:

```bash
python skills/traducir_libro_docx/scripts/run_pipeline.py \
  skills/traducir_libro_docx/workspace/input/tu_archivo.docx
```
## Uso con exportación a GitHub

```bash
export GITHUB_EXPORT_REPO_PATH="/ruta/absoluta/a/tu/repo"
export GITHUB_EXPORT_BRANCH="main"
export GITHUB_EXPORT_TARGET_DIR="translated-books"
export GITHUB_EXPORT_PUSH="true"

python skills/traducir_libro_docx/scripts/run_pipeline.py \
  skills/traducir_libro_docx/workspace/input/tu_archivo.docx \
  --export-github
``` 

## Ejecutar hasta un paso específico

```bash
python skills/traducir_libro_docx/scripts/run_pipeline.py \
  skills/traducir_libro_docx/workspace/input/tu_archivo.docx \
  --stop-after validate
```
Pasos disponibles:

- extract
- segment
- protect
- translate
- restore
- validate
reconstruct

## Salidas del pipeline
### Input original
```bash
workspace/input/
```

### Archivos intermedios

```bash
- workspace/intermediate/
```

Ejemplos:

- archivo.extracted.json
- archivo.segmented.json
- archivo.protected.json
- archivo.translated.json
- archivo.restored.json
- archivo.validated.json

### Archivo final
```bash
workspace/output/archivo.translated.en.docx
```

### Logs

```bash
workspace/logs/
```

## Qué preserva este skill

El pipeline está diseñado para preservar:

- estructura de capítulos y secciones
- numeración
- negrita
- cursiva
- subrayado
- superíndice y subíndice
- tablas
- código
- referencias
- URLs
- nombres de archivo
- rutas
- identificadores
- comandos
- símbolos y notación matemática

## Reglas de traducción

### Se traduce
- prosa
- headings
- definiciones
- teoremas
- pruebas
- ejemplos
- ejercicios
- captions editables
- comentarios dentro de código
- texto de tablas
### No se traduce
- referencias
- URLs
- nombres de archivo
- rutas
- comandos
- identificadores
- sintaxis de código
- notación matemática
- variables matemáticas
- nombres estándar de tecnologías y frameworks

## Limitaciones actuales del MVP

Esta versión inicial todavía tiene limitaciones importantes:

- no reconstruye ecuaciones OMML nativas de Word
- no conserva perfectamente listas automáticas complejas
- no reconstituye footnotes/endnotes reales
- no mantiene cajas de texto ni objetos flotantes
- no preserva todos los estilos avanzados del DOCX original
- la redistribución del texto traducido entre runs es heurística
- la detección semántica de bloques sigue siendo basada en reglas simples

Funciona bien como base operativa, pero aún no es una réplica perfecta del DOCX fuente.

## Flujo manual por scripts

Si quieres ejecutar cada paso por separado:

```bash
python skills/traducir_libro_docx/scripts/extract_docx.py \
  skills/traducir_libro_docx/workspace/input/tu_archivo.docx

python skills/traducir_libro_docx/scripts/segment_blocks.py \
  skills/traducir_libro_docx/workspace/intermediate/tu_archivo.extracted.json

python skills/traducir_libro_docx/scripts/protect_content.py \
  skills/traducir_libro_docx/workspace/intermediate/tu_archivo.segmented.json

python skills/traducir_libro_docx/scripts/translate_blocks.py \
  skills/traducir_libro_docx/workspace/intermediate/tu_archivo.protected.json

python skills/traducir_libro_docx/scripts/restore_content.py \
  skills/traducir_libro_docx/workspace/intermediate/tu_archivo.translated.json

python skills/traducir_libro_docx/scripts/validate_translation.py \
  skills/traducir_libro_docx/workspace/intermediate/tu_archivo.restored.json

python skills/traducir_libro_docx/scripts/reconstruct_docx.py \
  skills/traducir_libro_docx/workspace/intermediate/tu_archivo.validated.json
```

## Exportación manual a GitHub

```bash
chmod +x skills/traducir_libro_docx/scripts/export_github.sh

export GITHUB_EXPORT_REPO_PATH="/ruta/absoluta/a/tu/repo"
export GITHUB_EXPORT_BRANCH="main"
export GITHUB_EXPORT_TARGET_DIR="translated-books"
export GITHUB_EXPORT_PUSH="true"

skills/traducir_libro_docx/scripts/export_github.sh \
  skills/traducir_libro_docx/workspace/output/tu_archivo.translated.en.docx
```

## Recomendación de uso

Para pruebas de estructura:
- usa TRANSLATION_PROVIDER=mock

Para traducción real:
- usa openai_compatible

Para producción:
- revisa siempre workspace/logs/
- inspecciona *.validated.json
- abre el .docx final y compáralo con el original
