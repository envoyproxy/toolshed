include "version";

.registryFileHashes // {}
| keys
| map(select(test("^.+/modules/[^/]+/[^/]+/source\\.json$")))
| map(capture("^(?<registry>.+)/modules/(?<name>[^/]+)/(?<version>[^/]+)/source\\.json$"))
| group_by(.name)
| map((sort_by(.version | version_key)) as $entries
      | if ($entries | length) > 1 then
          error("Multiple source.json entries for module \($entries[0].name): \(($entries | map(.version)) | join(", "))")
        else
          $entries[0]
        end)
| map({
    (.name): {
      module_url: (.registry + "/modules/" + .name + "/" + .version + "/"),
      registry: (.registry + "/"),
      urls: [(.registry + "/modules/" + .name + "/" + .version + "/")],
      version: .version,
    },
  })
| add // {}
