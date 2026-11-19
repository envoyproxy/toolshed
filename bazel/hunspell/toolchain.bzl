"""Toolchain for hermetic hunspell spellchecking."""

HunspellInfo = provider(
    doc = "Information about a hunspell implementation and its dictionary.",
    fields = {
        "affix": "File: the dictionary's `.aff` affix file.",
        "dictionary": "File: the dictionary's `.dic` word list.",
        "dictionary_path": "str: path to pass to `hunspell -d` (the `.dic` path without extension).",
        "hunspell": "File: the `hunspell` executable (supports the ispell `-a` pipe protocol).",
        "runfiles": "runfiles needed to run `hunspell` with the dictionary.",
    },
)

def _strip_ext(file, ext):
    if not file.path.endswith(ext):
        fail("%s must end with %s" % (file.path, ext))
    return file.path[:-len(ext)]

def _hunspell_toolchain_impl(ctx):
    executable = ctx.attr.hunspell[DefaultInfo].files_to_run.executable
    if not executable:
        fail("`hunspell` (%s) does not provide an executable" % ctx.attr.hunspell.label)
    affix = ctx.file.affix
    dictionary = ctx.file.dictionary
    dictionary_path = _strip_ext(dictionary, ".dic")
    if _strip_ext(affix, ".aff") != dictionary_path:
        fail("`affix` (%s) and `dictionary` (%s) must share a path prefix" % (affix.path, dictionary.path))

    runfiles = ctx.runfiles(files = [executable, affix, dictionary])
    runfiles = runfiles.merge(ctx.attr.hunspell[DefaultInfo].default_runfiles)

    return [
        platform_common.ToolchainInfo(
            hunspell = HunspellInfo(
                affix = affix,
                dictionary = dictionary,
                dictionary_path = dictionary_path,
                hunspell = executable,
                runfiles = runfiles,
            ),
        ),
        platform_common.TemplateVariableInfo({
            "HUNSPELL": executable.path,
            "HUNSPELL_DICT": dictionary_path,
        }),
    ]

hunspell_toolchain = rule(
    implementation = _hunspell_toolchain_impl,
    doc = "Declares a hunspell implementation and dictionary for `//hunspell:toolchain_type`.",
    attrs = {
        "affix": attr.label(
            allow_single_file = [".aff"],
            cfg = "exec",
            doc = "The dictionary's `.aff` affix file, alongside `dictionary`.",
            mandatory = True,
        ),
        "dictionary": attr.label(
            allow_single_file = [".dic"],
            cfg = "exec",
            doc = "The dictionary's `.dic` word list.",
            mandatory = True,
        ),
        "hunspell": attr.label(
            cfg = "exec",
            doc = "Executable implementing `hunspell`.",
            executable = True,
            mandatory = True,
        ),
    },
)
