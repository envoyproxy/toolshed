# Developer documentation


## Pytooling packages

The pytooling repo originated from the CI tooling in the main Envoy repo.

Gradually the tools are being integrated and refactored, with improved testing and performance.

Broadly the repo is split into 2 types of packages:

<dl>
  <dt>Generic packages that are not specific to Envoy:</dt>
  <dd>These mostly provide Python <code>async</code> functionality and have the <code>aio.</code> namespace prefix.</dd>
  <dt>Envoy-specific packages:</dt>
  <dd>These are specific to Envoy or work to Envoy's specific requirements and have the <code>envoy.</code> namespace prefix.</dd>
</dl>

The packages are published to pypi, and used in Envoy by way of `rules_python`.

Other than libraries there are broadly 2 types of runnable code:

<dl>
  <dt>Runners:</dt>
  <dd>Provide some functionality, such as building documentation, by running through a series of steps, exiting on failure.</dd>
  <dt>Checkers:</dt>
  <dd>Run a series of checks, such as dependency integrity, collecting errors/warning/success metrics as it runs.</dd>
</dl>

The packages are "async-first" making extensive use of Python's `asyncio`.

This allows tasks to be orchestrated efficiently, both for IO-bound tasks, or where necessary by shelling out to a separate process and then handling the IO from the process.

The code also has a high level of coverage with unit tests and makes extensive use of type-hinting and checking.

## Testing and linting with `pants`

The repo makes use of [pants](https://www.pantsbuild.org/) to manage the packages.

A basic introduction to the key tasks is given here, but you are encouraged to view [their documentation](https://www.pantsbuild.org/v2.9/docs).

### Running code tests

To run all code tests, as tested in CI:

```shell
$ ./pants test ::

```

You can also test in an individual package, eg:

```shell
$ ./pants test envoy.dependency.check::

```

### Running code tests with coverage

You can see the current coverage for all tests with:

```shell
$ ./pants test --open-coverage ::

```

Similarly you can see the coverage for a specific package:

```shell
$ ./pants test --open-coverage envoy.dependency.check::

```

### Debugging with code tests

You are strongly encouraged to make use of `breakpoint()` to debug the code.

Inserting a `breakpoint` into either the code under test or the test itself,
allows you to make use of `pdb` to introspect variables and step through and over code.

Assuming relevant `breakpoint`s have been added, you might debug while testing:

```shell
$ ./pants test --debug envoy.dependency.check::

```

### Passing arguments to `pytest`

Sometimes it can be useful to pass arguments to pytest when running tests.

For example, the following would run debug testing for tests containing `checker_cves`

```console

$ ./pants test --debug envoy.dependency.check:: -- -k checker_cves

```

See the [pytest documentation](https://docs.pytest.org/en/latest/how-to/usage.html) for further
information on pytest command line options.

### Linting the code

The repo is linted with `flake8` and the default config.

To lint the entire repo:

```shell
$ ./pants lint ::

```


## Testing code in an Envoy environment with `bazel`

Ordinarily Envoy uses the pytooling code from its published pypi packages.

When working on code in pytooling it is often helpful to test and introspect changes from
an Envoy environment without publishing to pypi.

### Setting up the Envoy <> pytooling environment

There are a couple of changes that need to be made in the Envoy environment.

#### Step 1: add dev requirements

You need to set up the dev requirements for Bazel.

For example to work on the `envoy.dependency.check` package, edit `tools/dev/requirements.txt`
adding the following (adjusted to your environment):

```console
-e file:///src/workspace/pytooling/envoy.dependency.check#egg=envoy.dependency.check&cachebust=000

```

In this example, my pytooling directory is located in `/src/workspace/pytooling`.

Whatever file path that you put here must be accessible to your Envoy environment, so if you are running inside a container,
you may need to mount your pytooling directory to a matching path.

Also note the `cachebust` parameter.

When making changes to your pytooling code Bazel does not know to rebuild the package and will default
to using its cached version. You can change the value of `cachebust` to expire Bazel's cache.

You can also test pytooling (or other Python) code directly from a repo, please see example given
in `tools/dev/requirements.txt`

#### Step 2: use of dev requirements in Bazel

Much of the pytooling code is accessed by Envoy by way of a Python `entry_point`.

It does this using a macro which wraps the `entry_point` from `rules_python`.

Using the example of dependency check, we can edit the `envoy_entry_point` in `tools/dependency/BUILD`.

Firstly, at the top of the file, add:

```starlark

load("@dev_pip3//:requirements.bzl", dev_entry_point = "entry_point")

```

Now we want to update the `check` rule to add the `dev_entry_point`:

```starlark

envoy_entry_point(
    name = "check",
    entry_point = dev_entry_point,
    args = [
        "--repository_locations=$(location //bazel:all_repository_locations)",
        "--cve_config=$(location :cve.yaml)",
    ],
    data = [
        ":cve.yaml",
        "//bazel:all_repository_locations",
    ],
    pkg = "envoy.dependency.check",
)

```

### Running the development code

With the development environment setup we can now run the code from Envoy Bazel.

Assuming we want to test the dependency check rule, as configured in the above example:

```console

$ bazel run //tools/dependency:check

```

When accessing code via `bazel run` you can usually add Python `breakpoint`s and drop
into the code.

This is not the case for `bazel build` or any other code path that run in subprocesses and/or
swallows `stdin`/`stdout`. In this case you may wish to use `remote-pdb` to workaround this limitation,
and debug forking processes.

Additional arguments can be specified on the command line as in the following example:

```console

$ bazel run //tools/dependency:check -- -v debug -c release_dates --github_token=$(cat MYTOKEN)

```
