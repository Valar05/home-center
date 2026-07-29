FROM node:22-bookworm-slim
WORKDIR /app
COPY build-index.mjs service.mjs ./
RUN chmod 0444 build-index.mjs service.mjs
ENV NODE_ENV=production
USER node
CMD ["node", "service.mjs"]
