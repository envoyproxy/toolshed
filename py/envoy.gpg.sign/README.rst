
envoy.gpg.sign
==============

GPG signing util used in Envoy proxy's CI

Usage
-----

::

    envoy.gpg.sign --maintainer-name "Foo" --maintainer-email foo@example.com \
        --out signed.tar packages.tar

Supported package types: ``bin``, ``deb``, ``rpm``.
Pass ``--type deb`` (or ``rpm`` / ``bin``) to limit signing to one type;
omit ``--type`` to sign all types found in the tarball.
