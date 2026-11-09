# Generic dependency/CVE version parsing and comparison.
#
# API: parse/1 returns {main, pre, build, string} for numeric versions, an opaque
# {string} object otherwise, and null for "*" (or a missing/null version).
# cmp/2 returns -1, 0, or 1 for parsed objects; eq/2, lt/2, lte/2, gt/2, and
# gte/2 expose boolean comparisons. cmp_pre/2 compares prerelease identifier
# arrays, with [] denoting a final release. Numeric prerelease identifiers sort
# before alphabetic identifiers; build metadata does not affect comparisons.
#
# bazel/version.jq is a separate string-based API: version_key/0,
# compare_versions/2, sort_versions/0, and latest_version/0 order Bazel registry
# versions, tolerating arbitrary alphabetic/numeric token runs, including .bcr
# suffixes. CVE CPE ranges instead need structured parse results and explicit
# inclusive/exclusive bound comparisons. The APIs are not interchangeable:
# cmp(parse("1"); parse("1.0.0")) == 0, and
# eq(parse("1.2.3+build.1"); parse("1.2.3+build.2")) == true here.
# A future unification could define Bazel's version_key in terms of parse and
# retain a single comparison implementation, or move its token-run tolerance
# into parse's opaque fallback. Either approach must reconcile normalized
# releases and ignored build suffixes with existing Bazel registry ordering.
# Such unification is deliberately out of scope for this CVE scanner port.

def cmp_pre(a; b):
  if a == [] and b == [] then 0
  elif a == [] then 1
  elif b == [] then -1
  else
    reduce range(0; ([(a | length), (b | length)] | max)) as $i (0;
      if . != 0 then .
      elif $i >= (a | length) then -1
      elif $i >= (b | length) then 1
      else
        a[$i] as $ai
        | b[$i] as $bi
        | ($ai | test("^[0-9]+$")) as $an
        | ($bi | test("^[0-9]+$")) as $bn
        | if $an and $bn then
            if ($ai | tonumber) < ($bi | tonumber) then -1
            elif ($ai | tonumber) > ($bi | tonumber) then 1
            else 0 end
          elif $an then -1
          elif $bn then 1
          elif $ai == $bi then 0
          elif $ai < $bi then -1
          else 1 end
      end)
  end;

def cmp(v1; v2):
  v1 as $a | v2 as $b
  | if $a.main? and $b.main? then
      reduce range(0; 3) as $i (0;
        if . != 0 then .
        elif $a.main[$i] < $b.main[$i] then -1
        elif $a.main[$i] > $b.main[$i] then 1
        else 0 end)
      | if . != 0 then . else cmp_pre($a.pre; $b.pre) end
    elif $a.string == $b.string then 0
    elif $a.string < $b.string then -1
    else 1 end;

def eq(v1; v2): cmp(v1; v2) == 0;
def lt(v1; v2): cmp(v1; v2) < 0;
def lte(v1; v2): cmp(v1; v2) <= 0;
def gt(v1; v2): cmp(v1; v2) > 0;
def gte(v1; v2): cmp(v1; v2) >= 0;

def parse(v):
  (v // "*") as $v
  | if $v == "*" then null
    else
      ($v | capture("^(?<main>[0-9]+(?:\\.[0-9]+){0,2})(?:-(?<pre>[^+]+))?(?:\\+(?<build>.+))?$")? // null) as $m
      | if $m == null then {string: $v}
        else
          ($m.main
           + (if $m.pre == null then "" else "-" + $m.pre end)
           + (if $m.build == null then "" else "+" + $m.build end)) as $reconstructed
          | if $reconstructed != $v then {string: $v}
            else
              {main: ($m.main | (split(".") | map(tonumber) + [0, 0, 0])[0:3]),
               pre: (if $m.pre == null then [] else $m.pre | split(".") end),
               build: (if $m.build == null then [] else $m.build | split(".") end),
               string: $v}
            end
        end
    end;
