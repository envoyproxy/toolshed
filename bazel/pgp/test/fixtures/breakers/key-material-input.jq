([.pathFragments[].id] | max) as $f0
| ([.artifacts[].id] | max) as $a0
| ([.depSetOfFiles[].id] | max) as $d0
| ($f0 + 1) as $f1
| ($f0 + 2) as $f2
| ($f0 + 3) as $f3
| ($a0 + 1) as $art
| ($d0 + 1) as $ds
| .pathFragments += [
    {"id": $f1, "label": ".gnupg"},
    {"id": $f2, "label": "private-keys-v1.d", "parentId": $f1},
    {"id": $f3, "label": "DEADBEEF.key", "parentId": $f2}
  ]
| .artifacts += [{"id": $art, "pathFragmentId": $f3}]
| .depSetOfFiles += [{"id": $ds, "directArtifactIds": [$art]}]
| (.actions | map(.mnemonic == "OpenPGPSign") | index(true)) as $idx
| .actions[$idx].inputDepSetIds += [$ds]
