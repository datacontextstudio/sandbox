FROM node:26-slim
WORKDIR /app

RUN npm install -g pnpm

COPY package.json ./
RUN pnpm install

COPY . .

EXPOSE 5174
CMD ["pnpm", "dev", "--host"]
