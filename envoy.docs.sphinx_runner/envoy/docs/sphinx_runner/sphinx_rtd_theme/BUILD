python_sources(
    skip_flake8 = True,
    skip_mypy = True,
    skip_docformatter = True,
    dependencies=[
        ":assets",
    ],
)

resources(
    name="assets",
    sources=[
        "*.html",
        "*.conf",
        "./locale/**/*.po",
        "./locale/**/*.pot",
        "./static/**/*.css",
        "./static/**/*.js",
        "./static/**/*.woff",
        "./static/**/*.woff2",
        "./static/**/*.eot",
        "./static/**/*.ttf",
        "./static/**/*.svg"])
