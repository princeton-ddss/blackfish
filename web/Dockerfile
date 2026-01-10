FROM node:23-bookworm-slim

RUN mkdir -p /app
RUN chown -R node:node /app

WORKDIR /app

COPY package*.json ./
RUN chown -R node:node .

RUN npm install

USER node

COPY --chown=node:node . .

CMD ["npm", "run", "build"]
