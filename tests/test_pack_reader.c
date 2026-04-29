#include "include/infrastructure/pack_reader.h"
#include <assert.h>
#include <string.h>

int main(void) {
    /* TSV line parsing */
    Question q;
    const char *line = "0\t6\tWhat year was Pelé born?\t1940";
    assert(pack_parse_tsv_line(line, strlen(line), &q) == true);
    assert(q.id == 0u);
    assert(q.category_id == 6u);
    assert(strcmp(q.question, "What year was Pelé born?") == 0);
    assert(strcmp(q.answer, "1940") == 0);

    /* Trailing newline tolerated */
    const char *line_nl = "12\t1\tCapital of Spain?\tMadrid\n";
    assert(pack_parse_tsv_line(line_nl, strlen(line_nl), &q) == true);
    assert(q.id == 12u && q.category_id == 1u);
    assert(strcmp(q.question, "Capital of Spain?") == 0);
    assert(strcmp(q.answer, "Madrid") == 0);

    /* Wrong number of fields */
    const char *bad = "1\t2\tonly three";
    assert(pack_parse_tsv_line(bad, strlen(bad), &q) == false);

    /* Non-numeric id */
    const char *bad_id = "abc\t2\tQ\tA";
    assert(pack_parse_tsv_line(bad_id, strlen(bad_id), &q) == false);

    /* Out-of-range category */
    const char *bad_cat = "1\t99\tQ\tA";
    assert(pack_parse_tsv_line(bad_cat, strlen(bad_cat), &q) == false);

    /* IDX header decoding */
    const uint8_t header_ok[] = {
        'T',  'R',  'V',  'I',  /* magic */
        0x01, 0x00,             /* version 1 LE */
        0x03, 0x00, 0x00, 0x00, /* count = 3 */
    };
    PackIdxHeader h;
    assert(pack_idx_header_decode(header_ok, sizeof(header_ok), &h) == true);
    assert(h.version == 1u);
    assert(h.count == 3u);

    /* Bad magic */
    uint8_t bad_magic[sizeof(header_ok)];
    memcpy(bad_magic, header_ok, sizeof(header_ok));
    bad_magic[0] = 'X';
    assert(pack_idx_header_decode(bad_magic, sizeof(bad_magic), &h) == false);

    /* Truncated */
    assert(pack_idx_header_decode(header_ok, 6u, &h) == false);

    /* Offset lookup with a 3-entry idx */
    const uint8_t idx_blob[] = {
        'T',  'R',  'V',  'I',  0x01, 0x00, 0x03,
        0x00, 0x00, 0x00, 0x10, 0x00, 0x00, 0x00, /* offsets[0] = 16 */
        0x40, 0x00, 0x00, 0x00,                   /* offsets[1] = 64 */
        0xA0, 0x00, 0x00, 0x00,                   /* offsets[2] = 160 */
    };
    uint32_t off;
    assert(pack_idx_offset_at(idx_blob, sizeof(idx_blob), 3u, 0u, &off) && off == 16u);
    assert(pack_idx_offset_at(idx_blob, sizeof(idx_blob), 3u, 2u, &off) && off == 160u);
    assert(pack_idx_offset_at(idx_blob, sizeof(idx_blob), 3u, 3u, &off) == false); /* OOB */

    return 0;
}
