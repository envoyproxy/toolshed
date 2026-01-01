def parse(config):
  split(" ")
  | reduce .[] as $arg (
      {args: [], flags: {}, options: {}, _pending: null};

      if ._pending then
        # Previous was an option expecting a value
        # Support repeated options by storing arrays
        if .options[._pending] then
          # Already exists, convert to array or append to array
          if (.options[._pending] | type) == "array" then
            .options[._pending] += [$arg]
          else
            .options[._pending] = [.options[._pending], $arg]
          end
        else
          .options[._pending] = $arg
        end
        | ._pending = null
      elif ($arg | startswith("--") and contains("=")) then
        # --key=value format
        ($arg[2:]) as $rest
        | ($rest | index("=")) as $idx
        | ($rest[:$idx]) as $key
        | ($rest[$idx+1:]) as $value
        # Support repeated options by storing arrays
        | if .options[$key] then
            # Already exists, convert to array or append to array
            if (.options[$key] | type) == "array" then
              .options[$key] += [$value]
            else
              .options[$key] = [.options[$key], $value]
            end
          else
            .options[$key] = $value
          end
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
