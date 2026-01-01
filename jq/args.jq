def parse(config):
  split(" ")
  | reduce .[] as $arg (
      {args: [], flags: {}, options: {}, _pending: null};

      if ._pending then
        # Previous was an option expecting a value
        .options[._pending] = $arg | ._pending = null
      elif ($arg | startswith("--") and contains("=")) then
        # --key=value format
        ($arg[2:]) as $rest
        | ($rest | index("=")) as $idx
        | .options[$rest[:$idx]] = $rest[$idx+1:]
      elif ($arg | startswith("--")) then
        # --flag or --option
        ($arg[2:]) as $name
        | if (config.flags // [] | index($name)) then
            .flags[$name] = true
          else
            ._pending = $name
          end
      elif ($arg | startswith("-")) then
        # -f or -o
        ($arg[1:]) as $name
        | if (config.flags // [] | index($name)) then
            .flags[$name] = true
          else
            ._pending = $name
          end
      else
        # Positional argument
        .args += [$arg]
      end
  )
  | del(._pending);
