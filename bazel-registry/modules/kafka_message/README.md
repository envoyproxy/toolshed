# kafka_message Bazel Module

This module provides Kafka protocol message definitions (JSON files) from Apache Kafka.

## Overview

The `kafka_message` module extracts the Kafka protocol message definition files from the Apache Kafka source release. These JSON files define the structure of Kafka protocol request and response messages and are used by Envoy's Kafka filter for protocol message parsing and code generation.

## Version

- **Module Version**: 3.9.1.envoy
- **Upstream Version**: Apache Kafka 3.9.1
- **Compatibility**: Bazel >=7.2.1

## Source

The module fetches from:
- URL: https://github.com/apache/kafka/archive/3.9.1.zip
- Strip Prefix: `kafka-3.9.1/clients/src/main/resources/common/message`

This ensures only the protocol message JSON files are included in the module's workspace.

## Usage

Add the module as a dependency in your `MODULE.bazel`:

```starlark
bazel_dep(name = "kafka_message", version = "3.9.1.envoy")
```

## Available Targets

### Request Protocol Files

Access all Kafka request message definitions:

```starlark
filegroup(
    name = "my_requests",
    srcs = ["@kafka_message//:request_protocol_files"],
)
```

This includes 88 files matching `*Request.json` pattern.

### Response Protocol Files

Access all Kafka response message definitions:

```starlark
filegroup(
    name = "my_responses",
    srcs = ["@kafka_message//:response_protocol_files"],
)
```

This includes 88 files matching `*Response.json` pattern.

### All Protocol Files

Access all protocol message definitions (requests, responses, and other files):

```starlark
filegroup(
    name = "my_all_protocol",
    srcs = ["@kafka_message//:all_protocol_files"],
)
```

This includes 186 JSON files in total.

## Example Use Cases

1. **Code Generation**: Use these definitions to generate Kafka protocol serialization/deserialization code
2. **Protocol Testing**: Reference protocol definitions in test data
3. **Documentation**: Extract protocol information for documentation generation

## Contents

The module includes protocol definitions for Kafka APIs such as:
- Produce/Fetch (core messaging)
- Metadata (topic/broker information)
- OffsetCommit/OffsetFetch (consumer groups)
- CreateTopics/DeleteTopics (admin operations)
- And many more...

## Maintainers

- Envoy Proxy Maintainers
- Email: maintainers@envoyproxy.io
- GitHub: @envoyproxy

## License

Apache 2.0 (same as Apache Kafka)
