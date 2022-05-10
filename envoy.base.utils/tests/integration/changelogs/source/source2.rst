1.21.0 (January 12, 2022)
=========================

Incompatible Behavior Changes
-----------------------------
*Changes that are expected to cause an incompatibility if applicable; deployment changes are likely required*

* auto_config: :ref:`auto_config <envoy_v3_api_field_extensions.upstreams.http.v3.HttpProtocolOptions.auto_config>` now verifies that any transport sockets configured via :ref:`transport_socket_matches <envoy_v3_api_field_config.cluster.v3.Cluster.transport_socket_matches>` support ALPN. This behavioral change can be temporarily reverted by setting runtime guard ``envoy.reloadable_features.correctly_validate_alpn`` to false.
* xds: ``*`` became a reserved name for a wildcard resource that can be subscribed to and unsubscribed from at any time. This is a requirement for implementing the on-demand xDSes (like on-demand CDS) that can subscribe to specific resources next to their wildcard subscription. If such xDS is subscribed to both wildcard resource and to other specific resource, then in stream reconnection scenario, the xDS will not send an empty initial request, but a request containing ``*`` for wildcard subscription and the rest of the resources the xDS is subscribed to. If the xDS is only subscribed to wildcard resource, it will try to send a legacy wildcard request. This behavior implements the recent changes in :ref:`xDS protocol <xds_protocol>` and can be temporarily reverted by setting the ``envoy.restart_features.explicit_wildcard_resource`` runtime guard to false.

Minor Behavior Changes
----------------------
*Changes that may cause incompatibilities for some users, but should not for most*

* bandwidth_limit: added :ref:`response trailers <envoy_v3_api_field_extensions.filters.http.bandwidth_limit.v3.BandwidthLimit.enable_response_trailers>` when request or response delay are enforced.
* bandwidth_limit: added :ref:`bandwidth limit stats <config_http_filters_bandwidth_limit>` *request_enforced* and *response_enforced*.
