#include "include/ui/question_view.h"
#include <assert.h>
#include <string.h>

int main(void) {
    char buf[256];
    LineSlices slices;

    /* Empty input → 0 lines */
    qview_wrap("", 21u, buf, sizeof(buf), &slices);
    assert(slices.count == 0u);

    /* Single short line */
    qview_wrap("Hello world", 21u, buf, sizeof(buf), &slices);
    assert(slices.count == 1u);
    assert(strcmp(slices.lines[0], "Hello world") == 0);

    /* Word wrap */
    qview_wrap("This is a longer string that needs to wrap across lines", 21u, buf, sizeof(buf),
               &slices);
    /* Greedy word wrap: each line <= 21 chars */
    for (uint8_t i = 0u; i < slices.count; ++i) {
        assert(strlen(slices.lines[i]) <= 21u);
    }
    /* Reassembled (with single spaces between lines) should match the original */
    char joined[128];
    joined[0] = '\0';
    for (uint8_t i = 0u; i < slices.count; ++i) {
        if (i > 0u)
            strcat(joined, " ");
        strcat(joined, slices.lines[i]);
    }
    assert(strcmp(joined, "This is a longer string that needs to wrap across lines") == 0);

    /* Hard break on a single word longer than max */
    qview_wrap("Supercalifragilisticexpialidocious", 10u, buf, sizeof(buf), &slices);
    assert(slices.count >= 2u);
    for (uint8_t i = 0u; i < slices.count; ++i) {
        assert(strlen(slices.lines[i]) <= 10u);
    }

    return 0;
}
