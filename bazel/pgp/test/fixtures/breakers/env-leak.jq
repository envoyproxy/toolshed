.actions |= map(
    if .mnemonic == "OpenPGPSign" then
        .environmentVariables = ((.environmentVariables // []) + [{"key": "HOME", "value": "/x"}])
    else . end)
