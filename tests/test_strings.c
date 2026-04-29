#include "include/i18n/strings.h"
#include <assert.h>
#include <string.h>

int main(void) {
    /* Default locale is EN. */
    assert(tz_locale_get() == LangEn);
    assert(strcmp(tz_str(TzStrMenuChangeLang), "Change language") == 0);
    assert(strcmp(tz_str(TzStrMenuExit), "Exit") == 0);
    assert(strcmp(tz_str(TzStrFooterReveal), "OK: reveal") == 0);
    assert(strcmp(tz_str(TzStrFooterNext), ">: next") == 0);
    assert(strcmp(tz_str(TzStrLangPickHeader), "Language") == 0);
    assert(strcmp(tz_str(TzStrLangSpanish), "Spanish") == 0);
    assert(strcmp(tz_str(TzStrLangEnglish), "English") == 0);

    tz_locale_set(LangEs);
    assert(tz_locale_get() == LangEs);
    assert(strcmp(tz_str(TzStrMenuChangeLang), "Cambiar idioma") == 0);
    assert(strcmp(tz_str(TzStrMenuExit), "Salir") == 0);
    assert(strcmp(tz_str(TzStrFooterReveal), "OK: revelar") == 0);
    assert(strcmp(tz_str(TzStrFooterNext), ">: siguiente") == 0);
    assert(strcmp(tz_str(TzStrLangPickHeader), "Idioma") == 0);
    assert(strcmp(tz_str(TzStrLangSpanish), "Español") == 0);
    assert(strcmp(tz_str(TzStrLangEnglish), "Inglés") == 0);

    /* Out-of-range id falls back to a sentinel. */
    assert(strcmp(tz_str(TzStrCount), "?") == 0);

    /* Invalid locale falls back to EN. */
    tz_locale_set((Lang)99);
    assert(tz_locale_get() == LangEn);

    return 0;
}
