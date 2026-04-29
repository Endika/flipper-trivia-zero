#include "include/infrastructure/pack_reader.h"
#include <stdlib.h>
#include <string.h>

#ifdef __has_include
#if __has_include(<furi.h>)
#include <furi.h>
#include <storage/storage.h>
#define TZ_HAVE_FURI 1
#endif
#endif

#define IDX_HEADER_SIZE 10u /* 4 magic + 2 version + 4 count */

static uint16_t le_u16(const uint8_t *p) {
    return (uint16_t)(p[0] | ((uint16_t)p[1] << 8));
}

static uint32_t le_u32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

bool pack_parse_tsv_line(const char *line, size_t len, Question *out) {
    if (!line || !out || len == 0u) {
        return false;
    }
    /* Strip a trailing newline from the effective length. */
    while (len > 0u && (line[len - 1u] == '\n' || line[len - 1u] == '\r')) {
        len--;
    }
    if (len == 0u) {
        return false;
    }

    /* Find the three tab positions. */
    size_t tabs[3];
    size_t found = 0u;
    for (size_t i = 0u; i < len && found < 3u; ++i) {
        if (line[i] == '\t') {
            tabs[found++] = i;
        }
    }
    if (found != 3u) {
        return false;
    }

    /* id */
    char idbuf[16];
    if (tabs[0] >= sizeof(idbuf))
        return false;
    memcpy(idbuf, line, tabs[0]);
    idbuf[tabs[0]] = '\0';
    char *end = NULL;
    const unsigned long id = strtoul(idbuf, &end, 10);
    if (end == idbuf || *end != '\0')
        return false;

    /* category_id */
    const size_t cat_start = tabs[0] + 1u;
    const size_t cat_len = tabs[1] - cat_start;
    char catbuf[8];
    if (cat_len >= sizeof(catbuf))
        return false;
    memcpy(catbuf, line + cat_start, cat_len);
    catbuf[cat_len] = '\0';
    const unsigned long cat = strtoul(catbuf, &end, 10);
    if (end == catbuf || *end != '\0' || cat < 1u || cat > 7u)
        return false;

    /* question */
    const size_t q_start = tabs[1] + 1u;
    const size_t q_len = tabs[2] - q_start;
    if (q_len >= QUESTION_MAX)
        return false;

    /* answer */
    const size_t a_start = tabs[2] + 1u;
    const size_t a_len = len - a_start;
    if (a_len >= ANSWER_MAX)
        return false;

    out->id = (uint32_t)id;
    out->category_id = (uint8_t)cat;
    memcpy(out->question, line + q_start, q_len);
    out->question[q_len] = '\0';
    memcpy(out->answer, line + a_start, a_len);
    out->answer[a_len] = '\0';
    return true;
}

bool pack_idx_header_decode(const uint8_t *blob, size_t len, PackIdxHeader *out) {
    if (!blob || !out || len < IDX_HEADER_SIZE)
        return false;
    if (blob[0] != 'T' || blob[1] != 'R' || blob[2] != 'V' || blob[3] != 'I') {
        return false;
    }
    out->version = le_u16(blob + 4);
    out->count = le_u32(blob + 6);
    return true;
}

bool pack_idx_offset_at(const uint8_t *blob, size_t len, uint32_t count, uint32_t i,
                        uint32_t *offset_out) {
    if (!blob || !offset_out || i >= count)
        return false;
    const size_t need = (size_t)IDX_HEADER_SIZE + (size_t)count * 4u;
    if (len < need)
        return false;
    *offset_out = le_u32(blob + IDX_HEADER_SIZE + (size_t)i * 4u);
    return true;
}

#ifdef TZ_HAVE_FURI

static Storage *s_storage = NULL;
static File *s_tsv = NULL;
static File *s_idx = NULL;
static uint32_t s_count = 0u;

static const char *path_tsv(Lang lang) {
    return (lang == LangEs) ? "/ext/apps_data/flipper_trivia_zero/trivia_es.tsv"
                            : "/ext/apps_data/flipper_trivia_zero/trivia_en.tsv";
}

static const char *path_idx(Lang lang) {
    return (lang == LangEs) ? "/ext/apps_data/flipper_trivia_zero/trivia_es.idx"
                            : "/ext/apps_data/flipper_trivia_zero/trivia_en.idx";
}

bool pack_open(Lang lang) {
    pack_close();
    s_storage = furi_record_open(RECORD_STORAGE);
    s_tsv = storage_file_alloc(s_storage);
    s_idx = storage_file_alloc(s_storage);

    if (!storage_file_open(s_tsv, path_tsv(lang), FSAM_READ, FSOM_OPEN_EXISTING) ||
        !storage_file_open(s_idx, path_idx(lang), FSAM_READ, FSOM_OPEN_EXISTING)) {
        pack_close();
        return false;
    }

    uint8_t header[IDX_HEADER_SIZE];
    if (storage_file_read(s_idx, header, sizeof(header)) != sizeof(header)) {
        pack_close();
        return false;
    }
    PackIdxHeader h;
    if (!pack_idx_header_decode(header, sizeof(header), &h) || h.version != 1u) {
        pack_close();
        return false;
    }
    s_count = h.count;
    return true;
}

void pack_close(void) {
    if (s_tsv) {
        storage_file_close(s_tsv);
        storage_file_free(s_tsv);
        s_tsv = NULL;
    }
    if (s_idx) {
        storage_file_close(s_idx);
        storage_file_free(s_idx);
        s_idx = NULL;
    }
    if (s_storage) {
        furi_record_close(RECORD_STORAGE);
        s_storage = NULL;
    }
    s_count = 0u;
}

uint32_t pack_count(void) {
    return s_count;
}

bool pack_get_by_id(uint32_t id, Question *out) {
    if (!out || !s_idx || !s_tsv || id >= s_count)
        return false;

    /* Read offset[id] from idx */
    const uint64_t idx_pos = (uint64_t)IDX_HEADER_SIZE + (uint64_t)id * 4u;
    if (!storage_file_seek(s_idx, idx_pos, true))
        return false;
    uint8_t off_bytes[4];
    if (storage_file_read(s_idx, off_bytes, 4) != 4)
        return false;
    const uint32_t offset = (uint32_t)off_bytes[0] | ((uint32_t)off_bytes[1] << 8) |
                            ((uint32_t)off_bytes[2] << 16) | ((uint32_t)off_bytes[3] << 24);

    if (!storage_file_seek(s_tsv, offset, true))
        return false;

    /* Read line until '\n' or buffer full */
    char line[QUESTION_MAX + ANSWER_MAX + 32u];
    size_t pos = 0u;
    char ch;
    while (pos < sizeof(line) - 1u && storage_file_read(s_tsv, &ch, 1) == 1) {
        if (ch == '\n')
            break;
        line[pos++] = ch;
    }
    line[pos] = '\0';

    return pack_parse_tsv_line(line, pos, out);
}

#endif /* TZ_HAVE_FURI */
