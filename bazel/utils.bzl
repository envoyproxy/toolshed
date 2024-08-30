
def cat(name = "cat", flag = "target"):
    """
    Register the tool like so

    ```starlark

    cat(name = "mycat", flag = "mytarget")

    ```

    This can then be used like so:

    ```console

    $ bazel run //:mycat --//:mytarget=//path/to:target

    ```

    `name` and `flag` are optional and default to `cat` and `target`

    """

    native.genrule(
        name = "empty",
        outs = ["empty.txt"],
        cmd = """
        echo "" > $@
        """
    )

    native.label_flag(
        name = flag,
        build_setting_default = ":empty",
    )

    native.genrule(
        name = "%s_sh" % name,
        outs = ["%s.sh" % name],
        cmd = """
        echo 'cat $${1}' > $@
        chmod +x $@
        """,
        srcs = [":%s" % flag],
    )

    native.sh_binary(
        name = name,
        srcs = ["%s_sh" % name],
        data = [":%s" % flag],
        args = ["$(location :%s)" % flag]
    )
