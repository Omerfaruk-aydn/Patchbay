FROM node:20-alpine AS base

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

FROM base AS production

RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
