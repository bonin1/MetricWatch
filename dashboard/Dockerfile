# Build stage - just copy the HTML file
FROM nginx:alpine

# Copy the standalone HTML dashboard
COPY public/index.html /usr/share/nginx/html/index.html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
