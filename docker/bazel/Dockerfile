FROM ubuntu:24.04@sha256:80dd3c3b9c6cecb9f1667e9290b3bc61b78c2678c02cbdae5f0fea92cc6734ab AS base

ARG APT_BASE_PKGS="\
    apt-transport-https \
    curl \
    gnupg \
    language-pack-en-base \
    software-properties-common"
ARG USER_NAME
ARG USER_ID
ARG GROUP_ID
ENV LANGUAGE=en_US:en
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV DEBIAN_FRONTEND=noninteractive
RUN --mount=type=tmpfs,target=/var/cache/apt \
    --mount=type=tmpfs,target=/var/lib/apt/lists \
    <<EOF
set -e
apt-get update
apt-get install -y -qq --no-install-recommends $APT_BASE_PKGS
EOF
RUN <<EOF
set -e
echo 'Acquire::Languages {"none";};' > /etc/apt/apt.conf.d/60language
echo "LANG=\"${LANG}\"" > /etc/default/locale
echo "LANGUAGE=\"${LANGUAGE}\"" >> /etc/default/locale
locale-gen "$LANG"
update-locale "$LANG"
groupmod -g "${GROUP_ID:-${USER_ID:-1000}}" -n "${USER_NAME:-ubuntu}" ubuntu
usermod -g "${GROUP_ID:-${USER_ID:-1000}}" -u "${USER_ID:-1000}" -m -d "/home/${USER_NAME:-ubuntu}" -l "${USER_NAME:-ubuntu}" ubuntu
EOF


FROM base AS bazel
ARG BAZELISK_VERSION=1.10.1
RUN <<EOF
set -e
curl -fsSL --output \
    /usr/local/bin/bazel \
    "https://github.com/bazelbuild/bazelisk/releases/download/v${BAZELISK_VERSION}/bazelisk-linux-$(dpkg --print-architecture)"
chmod +x /usr/local/bin/bazel
EOF


FROM bazel AS full
ARG APT_PKGS
RUN --mount=type=tmpfs,target=/var/cache/apt \
    --mount=type=tmpfs,target=/var/lib/apt/lists \
    <<EOF
set -e
apt-get update
apt-get install -y -qq --no-install-recommends $APT_PKGS
EOF
ARG SETUP=:
COPY --chmod=755 \
    <<EOF /tmp/setup.sh
${SETUP}
EOF
RUN --mount=type=tmpfs,target=/var/cache/apt \
    --mount=type=tmpfs,target=/var/lib/apt/lists \
    <<EOF
/tmp/setup.sh
EXIT_CODE=$?
rm -f /tmp/setup.sh
exit $EXIT_CODE
EOF


FROM full AS extra
ARG EXTRA_APT_PKGS
RUN --mount=type=tmpfs,target=/var/cache/apt \
    --mount=type=tmpfs,target=/var/lib/apt/lists \
    <<EOF
set -e
if [ -n "$EXTRA_APT_PKGS" ]; then
    apt-get update
    apt-get install -y -qq --no-install-recommends $EXTRA_APT_PKGS
fi
EOF
ARG EXTRA_SETUP
COPY --chmod=755 \
    <<EOF /tmp/setup.sh
${EXTRA_SETUP:-:}
EOF
RUN --mount=type=tmpfs,target=/var/cache/apt \
    --mount=type=tmpfs,target=/var/lib/apt/lists \
    <<EOF
/tmp/setup.sh
EXIT_CODE=$?
rm -f /tmp/setup.sh
exit $EXIT_CODE
EOF



FROM full
