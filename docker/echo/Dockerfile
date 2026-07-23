FROM rust:slim-trixie@sha256:5c6f46a6e4472ab1ca7ba7d494e6677f2f219ebc02f32025d3986f057635ec9c AS download
RUN apt update \
    && apt install -y \
         ca-certificates curl jq yq
COPY rust/echo echo
COPY docker-assets.yaml .
RUN export ARCH=$(dpkg --print-architecture) \
    && XARCH=$(uname -m) \
    && cat docker-assets.yaml | yq > docker-assets.json \
    && RELEASE_TAG=$(cat docker-assets.json \
       | jq -C -r '.assets["toolshed-echo"]["release-tag"]') \
    && SHA=$(cat docker-assets.json \
       | jq -C -r --arg arch $ARCH '.assets["toolshed-echo"].sha256[$arch]') \
    && VERSION=$(cat docker-assets.json \
       | jq -C -r '.assets["toolshed-echo"].version') \
    && echo "$SHA $VERSION $RELEASE_TAG" \
    && DEST=/output/echo \
    && ASSET_NAME="echo-${VERSION}-${ARCH}" \
    && ASSET_URL="https://github.com/envoyproxy/toolshed/releases/download/${RELEASE_TAG}/${ASSET_NAME}" \
    && CHECKSUM_URL="https://github.com/envoyproxy/toolshed/releases/download/${RELEASE_TAG}/checksums.txt.asc" \
    && mkdir -p "$(dirname "${DEST}")" \
    && curl -fsSL "${ASSET_URL}" -o "${DEST}" \
    && curl -fsSL "${CHECKSUM_URL}" -o "checksums.txt.asc" \
    && sed -n '/^-----BEGIN PGP SIGNED MESSAGE-----/,/^-----BEGIN PGP SIGNATURE-----/p' \
         "${RUNNER_TEMP}/checksums.txt.asc" \
       | sed '1,/^$/d' \
       | sed '/^-----BEGIN PGP SIGNATURE-----/,$d' \
       > "checksums.txt" \
    && ( \
          cd "$(dirname "${DEST}")" && \
          grep " ${ASSET_NAME}"'$' "${RUNNER_TEMP}/checksums.txt" \
          | sed "s| ${ASSET_NAME}"'$'"| $(basename "${DEST}")|" \
          | sha256sum -c - \
        ) \
    && cp -a /lib/${XARCH}-linux-gnu/libgcc_s.so.1 /output/libgcc_s.so.1


FROM gcr.io/distroless/base-nossl-debian13:nonroot@sha256:202758b50b32f2505ae15f2cb35558d04bbeb95a33f92e9bb6124079978a7612
COPY --chmod=0755 --from=download /output/echo /usr/local/bin/toolshed-echo
COPY docker/echo/config.yaml /home/nonroot/config.yaml
COPY --from=download /output/libgcc_s.so.1 /lib/libgcc_s.so.1
EXPOSE 8787
ENTRYPOINT ["/usr/local/bin/toolshed-echo", "-c", "/home/nonroot/config.yaml"]
