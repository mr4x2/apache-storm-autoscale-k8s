FROM node:18

RUN mkdir -p /app/

WORKDIR /app/

COPY package.json .

RUN npm install

COPY . .
