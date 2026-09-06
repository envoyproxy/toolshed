([.pathFragments[].id] | max) as $f0
| ([.artifacts[].id] | max) as $a0
| ([.depSetOfFiles[].id] | max) as $d0
| ($f0 + 1) as $f1
| ($a0 + 1) as $art
| ($d0 + 1) as $ds
| .pathFragments += [
    {"id": $f1, "label": "signing-key.asc"}
  ]
| .artifacts += [{"id": $art, "pathFragmentId": $f1}]
| .depSetOfFiles += [{"id": $ds, "directArtifactIds": [$art]}]
| (.actions | map(.mnemonic == "OpenPGPSign") | index(true)) as $idx
| .actions[$idx].inputDepSetIds += [$ds]
