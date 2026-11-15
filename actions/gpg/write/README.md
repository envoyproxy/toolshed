# actions/gpg/write

Write an encrypted OpenPGP secret key and passphrase to host files for Bazel
`@envoy_toolshed//pgp` signing, and remove them in a post step.

```yaml
- uses: envoyproxy/toolshed/actions/gpg/write@e817e4dfbeacca47d3babc3d2ce6a4968b640759
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
