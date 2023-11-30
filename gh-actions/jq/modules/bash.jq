def output:
  "
\(.)
echo \"output<<EOF\" >> $GITHUB_OUTPUT
printf \"%s\\n\" \"${OUTPUT}\" >> $GITHUB_OUTPUT
echo \"EOF\" >> $GITHUB_OUTPUT
"
;
