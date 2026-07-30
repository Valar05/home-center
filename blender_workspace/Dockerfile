FROM python:3.12-slim-bookworm
ARG BLENDER_VERSION=4.5.12
ARG BLENDER_SHA256=95e3a2dfedba3bd32ca54fc355eac6b15a11986954ccb02815a07535d0120a25
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl xz-utils libgl1 libx11-6 libxi6 libxrender1 libxfixes3 libxxf86vm1 libsm6 libice6 libegl1 libxkbcommon0 libdbus-1-3 libfontconfig1 libfreetype6 ffmpeg && rm -rf /var/lib/apt/lists/*
RUN curl -fsSLo /tmp/blender.tar.xz "https://download.blender.org/release/Blender4.5/blender-${BLENDER_VERSION}-linux-x64.tar.xz"  && echo "${BLENDER_SHA256}  /tmp/blender.tar.xz" | sha256sum -c -  && tar -xJf /tmp/blender.tar.xz -C /opt  && ln -s "/opt/blender-${BLENDER_VERSION}-linux-x64/blender" /usr/local/bin/blender  && rm /tmp/blender.tar.xz
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY service.py executor.py ./
ENV PYTHONUNBUFFERED=1 BLENDER_BIN=/usr/local/bin/blender PORT=8080
CMD ["python", "/app/service.py"]
