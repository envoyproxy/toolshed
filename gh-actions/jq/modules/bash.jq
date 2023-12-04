def output:
  "
\(.)
echo \"output<<EOF\" >> $GITHUB_OUTPUT
printf \"%s\\n\" \"${OUTPUT}\" >> $GITHUB_OUTPUT
echo \"EOF\" >> $GITHUB_OUTPUT
"
;

def xargs:
  @sh
  | "
COMMANDS=(\(.))
echo \"${COMMANDS[@]}\"
printf \"%s\\n\" \"${COMMANDS[@]}\" | xargs -P4 -I{} bash -c \"{}\" &
wait
"
;
