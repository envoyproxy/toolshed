{
  sha: $sha,
  ancestor: $ancestor,
  tags: $tags,
  latest: $latest,
  behind: (if $behind == "null" then null else ($behind | tonumber) end)
}
