include "lib";

(INDEX(.targets[]?; .id | tostring)) as $targets
| (INDEX(.pathFragments[]?; .id | tostring)) as $frags
| (INDEX(.depSetOfFiles[]?; .id | tostring)) as $depsets
| (INDEX(.artifacts[]?; .id | tostring)) as $arts
| (INDEX(.configuration[]?; .id | tostring)) as $configs
| signing_actions($mnemonic) as $actions
| tool_artifact_ids(.actions; $configs; $depsets) as $tool_ids
| def target($action):
      (($targets[($action.targetId | tostring)] // {}).label // ($action.targetId // $action.mnemonic | tostring));
  def failure($check; $action; $detail):
      {"check": $check, "target": target($action), "detail": $detail};
  {
    "actions": ($actions | length),
    "failures": (
      ([
        $actions[] as $action
        | $required_exec_reqs[] as $req
        | select(([$action.executionInfo[]?.key] | index($req) | not))
        | failure(1; $action; "missing execution requirement `" + $req + "`")
      ] + [
        $actions[] as $action
        | ($action | action_input_paths($depsets; $arts; $frags)
           | map(select(test($forbidden_inputs_re; "i")))
           | unique) as $bad
        | select($bad | length > 0)
        | failure(2; $action; "input(s) look like key material or passphrases: " + ($bad | join(", ")))
      ] + [
        $actions[] as $action
        | $forbidden_env[] as $env
        | select(([$action.environmentVariables[]?.key] | index($env)) != null)
        | failure(3; $action; "forbidden environment variable `" + $env + "`")
      ] + [
        $actions[] as $action
        | $forbidden_strings[] as $forbidden
        | select(($forbidden | length) > 0)
        | select([$action.arguments[]? | select(contains($forbidden))] | length > 0)
        | failure(4; $action; "forbidden string appears on command line")
      ] + [
        $actions[] as $action
        | ($action.arguments[-1]) as $expected_src
        | ($action | non_tool_input_paths($depsets; $arts; $frags; $tool_ids) | unique) as $non_tool_inputs
        | select($non_tool_inputs != [$expected_src])
        | failure(5; $action; "expected non-tool inputs [" + $expected_src + "], got [" + ($non_tool_inputs | join(", ")) + "]")
      ])
    )
  }
