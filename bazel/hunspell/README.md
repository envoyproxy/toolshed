# Hermetic hunspell (`//hunspell`)

A hermetic [hunspell](https://github.com/hunspell/hunspell) spellchecker with SCOWL's en_US
dictionary, exposed as `//hunspell:toolchain_type`.

`hunspell -a` speaks the ispell pipe protocol (as used by `aspell pipe`): it prints a banner, then
for each input line one result per word (`*` correct, `+ <root>` affixed, `-` compound,
`& <word> <n> <offset>: <suggestions>`, `# <word> <offset>` no suggestions), and a blank line.

## Runtime layout

Each `bins-v*` release publishes `hunspell-<version>-linux-{x86_64,aarch64}.tar.zst`:

- `BUILD.bazel`
- `bin/hunspell`: statically linked against the C++ runtime, built against toolshed's glibc
  2.31 sysroot. No readline/curses, iconv or gettext.
- `share/hunspell/en_US.{aff,dic}`: SCOWL en_US (`dictionary-en`).
- `share/doc/`: hunspell and dictionary licenses.

## Consuming the toolchain

```starlark
hunspell = use_extension("@envoy_toolshed//hunspell:extensions.bzl", "hunspell_prebuilt_extension")
hunspell.setup()
use_repo(hunspell, "hunspell_toolchains")

register_toolchains("@hunspell_toolchains//:all")
```

For `genrule`/`sh_*` consumers, declare the toolchain and use `$(HUNSPELL)` and
`$(HUNSPELL_DICT)` (the dictionary path without extension, for `-d`). The make variables give exec
paths; add the files to the action's inputs too.

For Starlark rules, load `HunspellInfo` and read `ctx.toolchains`:

```starlark
load("@envoy_toolshed//hunspell:defs.bzl", "HUNSPELL_TOOLCHAIN_TYPE", "HunspellInfo")

# In _impl(ctx):
# info = ctx.toolchains[HUNSPELL_TOOLCHAIN_TYPE].hunspell
# info.hunspell, info.affix, info.dictionary, info.dictionary_path, info.runfiles
```

Run it with an empty environment, as
`env - hunspell -a -i utf-8 -d <dictionary_path> -p <personal word list>`. The personal word list
is plain text, one word per line. Clearing the environment matters: even with `-p`, hunspell also
loads `$HOME/.hunspell_<dictionary>` when `HOME` is set, and reads `DICTIONARY`, `DICPATH` and
`WORDLIST`.

## Building

toolshed builds hunspell from source (`@hunspell_src`, an overlay on the upstream release in
`//hunspell/private:hunspell.BUILD.bazel`) for its own tests, registered as a dev-only source
toolchain. `//hunspell/source:hunspell_packages` builds the published tarballs; after a bins
release, set `VERSIONS["hunspell_sha256"]` to enable the prebuilt toolchains.
