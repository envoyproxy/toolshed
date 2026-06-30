# syntax=docker/dockerfile:1.7
ARG ECHO_BIN=toolshed-echo
FROM gcr.io/distroless/static-debian12:nonroot@sha256:d093aa3e30dbadd3efe1310db061a14da60299baff8450a17fe0ccc514a16639
ARG ECHO_BIN
COPY --chmod=755 ${ECHO_BIN} /usr/local/bin/toolshed-echo
COPY config.yaml /home/nonroot/config.yaml
EXPOSE 8787
ENTRYPOINT ["/usr/local/bin/toolshed-echo"]
