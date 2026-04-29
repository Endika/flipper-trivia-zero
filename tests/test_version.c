#include "version.h"
#include <assert.h>
#include <string.h>

int main(void) {
    /* APP_VERSION must be defined and equal "0.1.0" at scaffolding time. */
    assert(strcmp(APP_VERSION, "0.1.0") == 0);
    return 0;
}
