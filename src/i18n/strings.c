#include "include/i18n/strings.h"

static Lang g_locale = LangEn;

static const char *const k_en[TzStrCount] = {
    [TzStrMenuChangeLang] = "Change language",
    [TzStrMenuExit] = "Exit",
    [TzStrFooterReveal] = "OK: reveal",
    [TzStrFooterNext] = ">: next",
    [TzStrLangPickHeader] = "Language",
    [TzStrLangSpanish] = "Spanish",
    [TzStrLangEnglish] = "English",
};

static const char *const k_es[TzStrCount] = {
    [TzStrMenuChangeLang] = "Cambiar idioma",
    [TzStrMenuExit] = "Salir",
    [TzStrFooterReveal] = "OK: revelar",
    [TzStrFooterNext] = ">: siguiente",
    [TzStrLangPickHeader] = "Idioma",
    [TzStrLangSpanish] = "Español",
    [TzStrLangEnglish] = "Inglés",
};

Lang tz_locale_get(void) {
    return g_locale;
}

void tz_locale_set(Lang locale) {
    g_locale = (locale == LangEs) ? LangEs : LangEn;
}

const char *tz_str(TzStrId id) {
    if ((unsigned)id >= (unsigned)TzStrCount) {
        return "?";
    }
    return (g_locale == LangEs) ? k_es[id] : k_en[id];
}
