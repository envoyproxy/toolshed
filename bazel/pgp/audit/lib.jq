def frag_path($frags):
    . as $id
    | $frags[$id | tostring] as $f
    | if ($f.parentId // null) != null then
          ($f.parentId | frag_path($frags)) + "/" + $f.label
      else
          $f.label
      end;

def depset_artifact_ids($depsets):
    . as $ids
    | ($ids // [])
    | map(
          ($depsets[(. | tostring)] // {}) as $ds
          | (($ds.directArtifactIds // [])
             + (($ds.transitiveDepSetIds // []) | depset_artifact_ids($depsets)))
      )
    | add // [];

def signing_actions($mnemonic):
    [.actions[]? | select(.mnemonic == $mnemonic)];

def action_input_ids($depsets):
    (.inputDepSetIds // []) | depset_artifact_ids($depsets) | unique;

def action_input_paths($depsets; $arts; $frags):
    [action_input_ids($depsets)[]
     | ($arts[(. | tostring)] // empty) as $art
     | select($art.pathFragmentId != null)
     | ($art.pathFragmentId | frag_path($frags))];

def tool_artifact_ids($actions; $configs; $depsets):
    [$actions[]?
     | select(($configs[(.configurationId | tostring)] // {} | .isTool // false) == true)
     | ((.outputIds // [])[]?, (action_input_ids($depsets)[]?))]
    | unique;

def non_tool_input_paths($depsets; $arts; $frags; $tool_ids):
    [action_input_ids($depsets)[]
     | . as $id
     | select(($tool_ids | index($id) | not))
     | ($arts[($id | tostring)] // empty) as $art
     | select($art.pathFragmentId != null)
     | ($art.pathFragmentId | frag_path($frags))];
