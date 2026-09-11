.actions |= map(
    if .mnemonic == "OpenPGPSign" then
        .arguments += ["--passphrase=" + $passphrase]
    else . end)
