FROM nginx:1.25-alpine

# Copy NGINX configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Create SSL certificate directory
RUN mkdir -p /etc/ssl/certs /etc/ssl/private

# For development, generate self-signed certificate
# In production, use proper certificates from Let's Encrypt or CA
RUN apk add --no-cache openssl && \
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/kavalan.key \
    -out /etc/ssl/certs/kavalan.crt \
    -subj "/C=IN/ST=Maharashtra/L=Mumbai/O=Kavalan/CN=api.kavalan.in"

# Expose ports
EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
