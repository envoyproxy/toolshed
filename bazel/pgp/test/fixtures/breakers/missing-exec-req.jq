.actions |= map(
    if .mnemonic == "OpenPGPSign" then
        .executionInfo |= map(select(.key != "no-cache"))
    else . end)
