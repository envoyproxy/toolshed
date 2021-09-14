
pytooling_verify_distribution(
    name="check_modules",
    build_artefacts=["{package}:build_artefacts"],
    verifier=["//tools/verify:check_modules"],
)

pytooling_verify_distribution(
    name="check_metadata",
    build_artefacts=["{package}:build_artefacts"],
    verifier=["//tools/verify:check_metadata"],
)

pytooling_verify_distribution(
    name="check_dependencies",
    build_artefacts=["{package}:build_artefacts"],
    verifier=["//tools/verify:check_dependencies"],
)
