FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates curl git jq nodejs npm \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
COPY . /workspace
ENV PATH="/workspace/tools/install-harness/fakes/bin:${PATH}"
ENV HOME_CENTER_PAIRING_FAKE=1

CMD ["node", "tools/home_center_install_contract_test.mjs"]
