
envoy.gpg.sign
==============

GPG signing util used in Envoy proxy's CI

Usage
-----

Use the ``envoy.gpg.sign`` console script to sign package tarballs.

Supported package types:

* ``bin``
* ``deb``
* ``rpm``

Example:

.. code-block:: console

    envoy.gpg.sign --maintainer-name "Foo" --maintainer-email foo@example.com --out signed.tar packages.tar
