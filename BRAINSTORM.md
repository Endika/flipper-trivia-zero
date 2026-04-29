# Trivia Zero — Brainstorm

**Fecha**: 2026-04-23 (apertura) / 2026-04-28 (continuación y cierre)
**Estado**: Brainstorm cerrado. Spec consolidado en `docs/superpowers/specs/2026-04-28-trivia-zero-design.md` — ese es el documento fuente para implementar. Este fichero queda como historial de las decisiones tomadas y los descartes.

## Identidad de la app

- **name**: `Trivia Zero`
- **appid**: `flipper_trivia_zero`
- **entry_point**: `trivia_zero_app`
- **fap_category**: `Games` (alineado con Avocado Zero e Impostor Game)
- **Repo dir**: `flipper-trivia-zero` (renombrado desde `flipper-trivia` el 2026-04-28)
- **SD data path**: `/ext/apps_data/flipper_trivia_zero/`
- **Familia**: hermana de `flipper-avocado-zero` — sufijo `-zero` jugando con el nombre del dispositivo.

---

## Concepto

FAP (Flipper Application Package) para Flipper Zero, estilo flashcard:

- Pantalla muestra una pregunta
- Usuario pulsa para revelar la respuesta
- Pasa a siguiente pregunta random

Sin puntuación, sin multi-choice, sin game loop. Solo variedad de preguntas con dos idiomas.

---

## Decisiones cerradas

### 1. Idiomas

- Español e Inglés, ambos por defecto
- Una sesión = un idioma (no se mezclan)
- Selección de idioma se persiste en SD → próximas sesiones arrancan en la última pregunta sin volver a ver el menú de idioma
- Para cambiar idioma durante el uso: BACK → menú → Cambiar idioma

### 2. Categorías

- **Pool único random** (no se filtra por categoría, no se elige al inicio).
- Cada pregunta muestra su categoría como **etiqueta visual** en una cabecera invertida (vídeo inverso, ~10px) encima del texto de la pregunta.
- Taxonomía: **6 clásicas del Trivial Pursuit + 1 cajón "Cultura General"**:
  1. Geografía / Geography
  2. Entretenimiento / Entertainment
  3. Historia / History
  4. Arte y Literatura / Arts & Literature
  5. Ciencia y Naturaleza / Science & Nature
  6. Deportes y Ocio / Sports & Leisure
  7. Cultura General / General Knowledge
- Las 24 categorías nativas de OpenTDB se **mapean a estas 7** durante el empaquetado del pack (paso off-Flipper, no en runtime). Borrador de mapeo a definir; "General Knowledge" de OpenTDB → "Cultura General".
- Motivación: añade contexto visual tipo Trivial sin complicar la mecánica (no hay filtros, no hay selección al inicio, no afecta al anti-repetición).

### 3. Fuente de datos

- Base: Open Trivia DB (https://opentdb.com)
- Solo `pregunta + respuesta correcta` → se descartan los 3 distractores del formato multi-choice original

### 4. Empaquetado (opción A2)

- Pack de datos viaja con el instalador del FAP
- Se auto-instala en `/ext/apps_data/flipper_trivia_zero/` durante qFlipper install (o install script del firmware custom)
- El usuario **no** percibe paso de descarga separada
- Lectura en runtime desde SD card (no embebido en el binario `.fap`)

### 5. UI / Controles

Layout de pantalla (128x64 monocroma):

- **Cabecera invertida** (~10px, vídeo inverso) con el nombre de la categoría
- Pregunta debajo (con scroll si no cabe)
- Indicador de acción en la parte inferior

Botones:

- **OK (centro)** → revelar respuesta
- **→ derecha** → siguiente pregunta (random del pool, sin repetir en la sesión)
- **← izquierda** → pregunta anterior (buffer de últimas 5)
- **↑ / ↓** → scroll vertical si la pregunta o respuesta no cabe, con indicador "▼" cuando hay más texto abajo
- **BACK** → menú con {Cambiar idioma, Salir}

### 6. Anti-repetición

- Solo in-memory durante la sesión (set de IDs ya mostradas)
- Al agotar el pool, se reinicia el marcado
- Entre sesiones **no** se persiste → al reabrir la app puede repetir por casualidad
- Motivación: simplicidad, evita sincronizar estado con SD

---

## Preguntas abiertas (retomar aquí)

### Q1. Dataset en español — CERRADA

**Decisión: híbrido curado, simétrico entre idiomas.**

Pipeline off-Flipper (script Python) que se ejecuta una vez antes de empaquetar:

1. **Fuente**: OpenTDB ES + OpenTDB EN.
2. **Filtrado por blacklist heurística** aplicada a **ambos idiomas**: keywords culturalmente anglo (NFL, NBA, MLB, Premier League, royal, Tudor, Super Bowl, Hollywood, etc.) descartan la pregunta en los dos lados. La blacklist se mantiene en un fichero versionado en el repo del pipeline.
3. **Traducción solo para las que pasan el filtro**:
   - EN → ES con LLM para las EN que no tienen equivalente nativo
   - ES → EN con LLM para las ES nativas (~200-500 extra)
   - Modelo concreto a definir en el spec (Haiku candidato por coste).
4. **Mapeo categorías** OpenTDB (24) → 7 buckets (ver decisión #2).
5. **Salida**: pack file (formato pendiente Q2) con conjunto **simétrico** ES/EN — mismo abanico temático en ambos idiomas, solo cambia el idioma.

Tamaño estimado final: ~1500-2000 preguntas en cada idioma.

**Por qué simétrico**: dos usuarios con el mismo Flipper en distinto idioma esperan ver la "misma" trivia con distinto idioma; la asimetría temática (Super Bowl en EN pero no en ES) confundiría.

### Q2. Formato del pack en SD — CERRADA

**Decisión: TSV + sidecar `.idx` binario, un par de ficheros por idioma.**

Restricción de memoria: ~500 KB de pack total no entra en los 256 KB de SRAM del Flipper → acceso por seek/offset, no carga completa.

Layout en `/ext/apps_data/flipper_trivia_zero/`:

```
trivia_es.tsv   # id\tcategory_id\tquestion\tanswer\n  (UTF-8, sin tabs/newlines en campos)
trivia_es.idx   # cabecera + array uint32 de offsets de línea
trivia_en.tsv
trivia_en.idx
```

Cabecera del `.idx` (a definir exacta en spec): `magic` ("TRVI") + `version` (uint16) + `count` (uint32) + array de offsets.

**Por qué TSV en lugar de binario custom o JSONL**:
- Pack **legible** → debuggable a mano, `git diff` muestra cambios reales en el contenido en PRs.
- Parser C **trivial** (~30 líneas, `strtok` por tab) sin dependencias en el `.fap`.
- Sidecar `.idx` separado → reconstruir el índice no toca el TSV.
- Cabecera con `magic` + `version` permite migrar formato a futuro de forma explícita.

El pipeline garantiza la ausencia de `\t` y `\n` en los campos durante el empaquetado.

### Q3. Política de longitud de texto — CERRADA

**Decisión: sin límite duro.**

- El pipeline no descarta preguntas por longitud.
- La UI gestiona texto largo con scroll vertical (ya decidido en sección 5).
- Motivación: preservar volumen de dataset. Se asume que alguna pregunta esporádicamente larga será una experiencia con varios scrolls, pero es preferible a perder contenido válido por un threshold arbitrario.

### Q4. Formato del settings file — CERRADA

**Decisión: key=value plano en `/ext/apps_data/flipper_trivia_zero/settings`.**

Formato:

```
# trivia v1
lang=es
last_id=1234
```

- Primera línea: comentario versionado (`# trivia vN`) para migraciones futuras explícitas.
- Líneas que empiezan por `#` se ignoran.
- Claves desconocidas se ignoran (forward-compat).
- Líneas malformadas se saltan (resiliencia ante corrupción parcial).
- Parser C ~15 líneas, cero dependencias.

Campos confirmados:
- `lang` (es|en) — decisión #1
- `last_id` — entero, ID de la última pregunta vista (para retomar al relanzar la app)

El fichero crece con nuevas claves sin romper compatibilidad hacia atrás.

### Q5. Arquitectura del `.fap` — CERRADA

**Decisión: replicar el patrón de `flipper-impostor-game` y `flipper-habit-flow`.**

- **ViewDispatcher + Views** (no Scenes/SceneManager).
- **Builtins de Flipper** (`submenu`) para menú BACK y selector de idioma; **un único custom view** (`question_view.c`) para la pantalla de pregunta.
- Layout de carpetas (Clean Architecture-ish, idéntico a impostor):

```
src/
  app/             trivia_zero_app.c       (composición + ViewDispatcher wiring)
  domain/          question_pool.c, history_buffer.c, anti_repeat.c, category.c
  infrastructure/  pack_reader.c (TSV+idx), settings_storage.c
  platform/        random_port.c
  i18n/            strings.c               (botones, menús, nombres de categorías ES/EN)
  ui/              question_view.c
include/           (espejo de src/ con los .h)
```

- Enum `AppView` con: `AppViewLangSelect`, `AppViewQuestion`, `AppViewMenu`.
- `version.h` autogenerado + `# x-release-please-version` en `application.fam` (ya en patrón de la familia).

**Por qué A**: máxima consistencia con tus FAPs hermanas → facilita reutilizar utilidades (settings_storage, random_port, i18n/strings) casi tal cual desde impostor, baja coste cognitivo de mantenimiento, y mantiene la "familia" Endika de FAPs visualmente coherente.

---

## Referencias

- Open Trivia DB: https://opentdb.com
- Flipper Zero FAP docs: https://docs.flipper.net/development/applications/overview
- Flipper Zero hardware: pantalla 128x64 monocroma, sin acelerómetro integrado, botones {↑, ↓, ←, →, OK, BACK}

---

## Próximos pasos al retomar

1. Resolver Q1 (dataset ES)
2. Resolver Q2 (formato pack)
3. Resolver Q3, Q4 (rápidos)
4. Proponer 2-3 enfoques arquitecturales para la FAP
5. Presentar diseño completo en secciones, con aprobación progresiva del usuario
6. Escribir spec final en `docs/superpowers/specs/YYYY-MM-DD-flipper-trivia-design.md`
7. Invocar skill `writing-plans` para plan de implementación
