FROM nginx:1.27-alpine

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

# Copy our custom config
COPY docker/nginx/nginx.conf /etc/nginx/conf.d/smart-home-app.conf

EXPOSE 80 443
