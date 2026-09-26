def normalize: sub("/+$"; "") + "/";

def dedupe_preserve:
  reduce .[] as $item ([]; if index($item) == null then . + [$item] else . end);

($extra // [])
+ (split("\n")
   | map(sub("\\s+#.*$"; ""))
   | map(select(test("^\\s*#") | not))
   | map(try capture("^\\s*(?:common|build)(?::[^\\s]+)?\\s+--registry=(?<registry>\\S+)").registry catch empty)
   | map(select(type == "string" and length > 0))
   | map(normalize))
| dedupe_preserve
