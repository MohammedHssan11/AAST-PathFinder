# Stage 1: Build the React app
FROM node:20-alpine AS build

WORKDIR /app

# Copy package files for caching
COPY package*.json ./
RUN npm install

# Copy source and build
COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:stable-alpine

# Copy the build output from the first stage to Nginx's html folder
COPY --from=build /app/dist /usr/share/nginx/html

# Expose port 80 for the web traffic
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]