# actions/gpg/write

Write an encrypted OpenPGP secret key and passphrase to host files for Bazel
`@envoy_toolshed//pgp` signing, and remove them in a post step.

```yaml
- uses: envoyproxy/toolshed/actions/gpg/write@36d1bce326258d62d1b69a469ac3df7e13a040e5
  id: signing
  with:
    key: ${{ secrets.GPG_KEY }}
    passphrase: ${{ secrets.GPG_KEY_PASSWORD }}
- run: |
    bazel build //:signed \
      --@envoy_toolshed//pgp:key_path="${KEY_PATH_FRAGMENT}" \
      --@envoy_toolshed//pgp:passphrase_path="${PASSPHRASE_PATH}"
  env:
    KEY_PATH_FRAGMENT: ${{ steps.signing.outputs.key-path-fragment }}
    PASSPHRASE_PATH: ${{ steps.signing.outputs.passphrase-path }}
```
