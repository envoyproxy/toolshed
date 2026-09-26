def base:
  reduce $regs[] as $registry ({}; .[$registry] = (reduce $deps[] as $dep ({}; .[$dep] = null)));

reduce [inputs | {path: input_filename, value: .}][] as $input
  (base;
   ($input.path | capture("/(?<i>[0-9]+)/(?<dep>[^/]+)\\.json$")) as $path
   | .[$regs[$path.i | tonumber]][$path.dep] = $input.value)
