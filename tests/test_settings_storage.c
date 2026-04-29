#include "include/infrastructure/settings_storage.h"
#include <assert.h>
#include <string.h>

int main(void) {
    Settings s = settings_default();

    /* Defaults */
    assert(s.lang == LangEn);
    assert(s.last_id == 0u);
    assert(s.last_id_valid == false);

    /* Apply known kv */
    assert(settings_apply_kv(&s, "lang", "es") == true);
    assert(s.lang == LangEs);

    assert(settings_apply_kv(&s, "lang", "en") == true);
    assert(s.lang == LangEn);

    assert(settings_apply_kv(&s, "last_id", "1234") == true);
    assert(s.last_id == 1234u);
    assert(s.last_id_valid == true);

    /* Unknown key returns false but does not corrupt state */
    Settings before = s;
    assert(settings_apply_kv(&s, "future_key", "anything") == false);
    assert(memcmp(&s, &before, sizeof(s)) == 0);

    /* Malformed values keep prior state */
    assert(settings_apply_kv(&s, "lang", "fr") == false);
    assert(s.lang == LangEn); /* unchanged */
    assert(settings_apply_kv(&s, "last_id", "not-a-number") == false);
    assert(s.last_id == 1234u); /* unchanged */

    /* Line splitter */
    char key[32];
    char value[64];
    assert(settings_split_line("lang=es", key, sizeof(key), value, sizeof(value)) == true);
    assert(strcmp(key, "lang") == 0 && strcmp(value, "es") == 0);

    /* Comment line returns false */
    assert(settings_split_line("# trivia v1", key, sizeof(key), value, sizeof(value)) == false);

    /* Empty/whitespace returns false */
    assert(settings_split_line("", key, sizeof(key), value, sizeof(value)) == false);
    assert(settings_split_line("   ", key, sizeof(key), value, sizeof(value)) == false);

    /* No equals sign returns false */
    assert(settings_split_line("garbage", key, sizeof(key), value, sizeof(value)) == false);

    /* Trailing newline trimmed */
    assert(settings_split_line("last_id=42\n", key, sizeof(key), value, sizeof(value)) == true);
    assert(strcmp(key, "last_id") == 0 && strcmp(value, "42") == 0);

    return 0;
}
