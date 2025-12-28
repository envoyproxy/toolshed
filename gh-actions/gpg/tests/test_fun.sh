#!/usr/bin/env bash

generate_test_key() {
    local name="${1:-Test User}"
    local email="${2:-test@example.com}"
    local passphrase="${3:-testpassword123}"

    gpgconf --kill gpg-agent || true
    cat > /tmp/test-key-params <<EOF
%echo Generating test GPG key
Key-Type: RSA
Key-Length: 2048
Subkey-Type: RSA
Subkey-Length: 2048
Name-Real: ${name}
Name-Email: ${email}
Passphrase: ${passphrase}
Expire-Date: 0
%commit
%echo Done
EOF

    gpg --batch --gen-key /tmp/test-key-params
}

export_secret_key() {
    local email="${1:-test@example.com}"
    local passphrase="${2:-testpassword123}"

    gpg --batch --yes --pinentry-mode loopback \
        --passphrase "${passphrase}" \
        --armor --export-secret-keys "${email}"
}

clear_keyring() {
    local email="${1:-test@example.com}"

    local fpr
    fpr=$(gpg --list-secret-keys --with-colons "${email}" | \
        awk -F: '/^fpr:/ { print $10; exit }')

    if [[ -n "$fpr" ]]; then
        gpg --batch --yes --delete-secret-and-public-key "$fpr" || true
    fi
}

test_fingerprint_output() {
    local fingerprint="${1}"

    if [[ -z "$fingerprint" ]]; then
        echo "fail:Fingerprint output is empty" >> "$TEST_OUTPUT"
        return 1
    elif [[ ! "$fingerprint" =~ ^[A-F0-9]{40}$ ]]; then
        echo "fail:Fingerprint format is invalid: $fingerprint" >> "$TEST_OUTPUT"
        return 1
    else
        echo "success:Fingerprint output is valid: $fingerprint" >> "$TEST_OUTPUT"
        return 0
    fi
}

test_passphrase_output() {
    local passphrase="${1}"
    local expected="${2}"

    if [[ -z "$passphrase" ]]; then
        echo "fail:Passphrase output is empty" >> "$TEST_OUTPUT"
        return 1
    elif [[ -n "$expected" && "$passphrase" != "$expected" ]]; then
        echo "fail:Passphrase output is incorrect: $passphrase" >> "$TEST_OUTPUT"
        return 1
    else
        echo "success:Passphrase output is correct" >> "$TEST_OUTPUT"
        return 0
    fi
}

test_key_in_keyring() {
    local fingerprint="${1}"

    if gpg --list-secret-keys | grep -q "$fingerprint"; then
        echo "success:GPG key is in keyring" >> "$TEST_OUTPUT"
        return 0
    else
        echo "fail:GPG key not found in keyring" >> "$TEST_OUTPUT"
        return 1
    fi
}
