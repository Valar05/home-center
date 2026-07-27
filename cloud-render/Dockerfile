FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates curl git python3 python3-numpy blender imagemagick libegl1 libgl1-mesa-dri nodejs npm \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app/cloud-render
COPY cloud-render/package*.json /app/cloud-render/
RUN npm ci --omit=dev
COPY cloud-render/src /app/cloud-render/src
COPY functions/artifact_transport.js /app/functions/artifact_transport.js

ENV PORT=8080
CMD ["node", "/app/cloud-render/src/server.mjs"]
