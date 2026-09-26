def split_first_dash:
  if contains("-") then
    capture("^(?<release>[^-]*)(?:-(?<prerelease>.*))?$")
  else
    {release: ., prerelease: null}
  end;

def token_runs:
  [scan("[A-Za-z]+|[0-9]+")]
  | map(if test("^[0-9]+$") then [0, tonumber] else [1, .] end);

def side_key($side):
  if ($side // "") == "" then [] else ($side | split(".") | map(token_runs) | add) end;

def version_key:
  split_first_dash as $parts
  | [side_key($parts.release), (if $parts.prerelease == null then 1 else 0 end), side_key($parts.prerelease)];

def compare_versions($a; $b):
  ($a | version_key) as $ka
  | ($b | version_key) as $kb
  | if $ka < $kb then -1 elif $ka > $kb then 1 else 0 end;

def sort_versions: sort_by(version_key);

def latest_version: if length == 0 then null else sort_versions | last end;
