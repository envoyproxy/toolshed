def convert_value(value; opt_type):
  if opt_type == "int" then
    (value | tonumber)
  elif opt_type == "bool" then
    (value | ascii_downcase | . == "true" or . == "1" or . == "yes")
  else
    value
  end;

def normalize_config(config):
  (
    if (config.options | type) == "array" then
      config | .options = (reduce .options[] as $opt ({}; . + {($opt): "string"}))
    elif (config.options | type) == "object" then
      config
    else
      config | .options = {}
    end
  ) as $config_with_opts
  | (
    if ($config_with_opts.flags | type) == "array" then
      $config_with_opts | .flags = (reduce .flags[] as $flag ({}; . + {($flag): "bool"}))
    elif ($config_with_opts.flags | type) == "object" then
      $config_with_opts
    else
      $config_with_opts | .flags = {}
    end
  );

def store_value(key; value; opt_type; target):
  (if target == "flags" then "Flag" else "Option" end) as $target_name
  | if (.[target][key]) then
      if opt_type == "array" then
        .[target][key] += [value]
      else
        error("\($target_name) '--\(key)' specified multiple times but is not configured as array type")
      end
    else
      if opt_type == "array" then
        .[target][key] = [value]
      else
        .[target][key] = value
      end
    end;

def handle_pending_value(arg):
  if ._pending_is_flag then
    (._config.flags[._pending] // "bool") as $flag_type
    | (convert_value(arg; $flag_type)) as $converted_value
    | store_value(._pending; $converted_value; $flag_type; "flags")
    | ._pending = null
    | ._pending_is_flag = false
  else
    (._config.options[._pending] // "string") as $opt_type
    | (convert_value(arg; $opt_type)) as $converted_value
    | store_value(._pending; $converted_value; $opt_type; "options")
    | ._pending = null
  end;

def handle_equals_format(key; value):
  if (._config.flags | has(key)) then
    (._config.flags[key] // "bool") as $flag_type
    | (convert_value(value; $flag_type)) as $converted_value
    | store_value(key; $converted_value; $flag_type; "flags")
  else
    (._config.options[key] // "string") as $opt_type
    | (convert_value(value; $opt_type)) as $converted_value
    | store_value(key; $converted_value; $opt_type; "options")
  end;

def handle_flag_or_option(name):
  if (._config.flags | has(name)) then
    (._config.flags[name] // "bool") as $flag_type
    | if $flag_type == "bool" then
        if .flags[name] then
          error("Flag '--\(name)' is a boolean flag and cannot be specified multiple times")
        else
          .flags[name] = true
        end
      else
        ._pending = name
        | ._pending_is_flag = true
      end
  else
    ._pending = name
  end;

def parse(config):
  normalize_config(config) as $normalized_config
  | split(" ")
  | reduce .[] as $arg (
      {args: [], flags: {}, options: {}, _pending: null, _config: $normalized_config};

      if ._pending then
        handle_pending_value($arg)
      elif ($arg | startswith("--") and contains("=")) then
        ($arg[2:]) as $rest
        | ($rest | index("=")) as $idx
        | ($rest[:$idx]) as $key
        | ($rest[$idx+1:]) as $value
        | handle_equals_format($key; $value)
      elif ($arg | startswith("--")) then
        handle_flag_or_option($arg[2:])
      elif ($arg | startswith("-")) then
        handle_flag_or_option($arg[1:])
      else
        .args += [$arg]
      end
  )
  | del(._pending, ._pending_is_flag, ._config);
