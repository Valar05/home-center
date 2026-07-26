FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
ENV CODEX_BIN=/usr/bin/codex
RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates curl git gnupg python3 tar gzip \
  && install -m 0755 -d /etc/apt/keyrings \
  && curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /etc/apt/keyrings/cloud.google.gpg \
  && echo "deb [signed-by=/etc/apt/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" > /etc/apt/sources.list.d/google-cloud-sdk.list \
  && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
  && apt-get update \
  && apt-get install -y --no-install-recommends nodejs google-cloud-cli gh \
  && npm install -g @openai/codex \
  && command -v codex \
  && codex --version \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY cloud-worker/package.json /app/cloud-worker/package.json
COPY cloud-worker/src /app/cloud-worker/src

ENTRYPOINT ["node", "/app/cloud-worker/src/cloud_run_worker.mjs"]
