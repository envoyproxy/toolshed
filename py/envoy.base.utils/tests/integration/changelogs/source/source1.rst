1.20.0 (October 5, 2021)
========================

Incompatible Behavior Changes
-----------------------------
*Changes that are expected to cause an incompatibility if applicable; deployment changes are likely required*

* config: due to the switch to using work-in-progress annotations and warnings to indicate APIs
  subject to change, the following API packages have been force migrated from ``v3alpha`` to ``v3``:
  ``envoy.extensions.access_loggers.open_telemetry.v3``,
  ``envoy.extensions.cache.simple_http_cache.v3``,
  ``envoy.watchdog.v3``. If your production deployment was using one of these APIs, you will be
  forced to potentially vendor the old proto file to continue serving old versions of Envoy.
* config: the ``--bootstrap-version`` CLI flag has been removed, Envoy has only been able to accept v3
  bootstrap configurations since 1.18.0.

Minor Behavior Changes
----------------------
*Changes that may cause incompatibilities for some users, but should not for most*

* client_ssl_auth filter: now sets additional termination details and ``UAEX`` response flag when the client certificate is not in the allowed-list.
* config: configuration files ending in .yml now load as YAML.
* config: configuration file extensions now ignore case when deciding the file type. E.g., .JSON files load as JSON.
