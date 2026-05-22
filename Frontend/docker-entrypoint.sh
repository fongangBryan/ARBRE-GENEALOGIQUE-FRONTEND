#!/bin/sh
set -e

DOMAIN=${DOMAIN:-localhost}
CERT="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"

if [ -f "$CERT" ]; then
    envsubst '${DOMAIN}' < /etc/nginx/templates/nginx-https.conf > /etc/nginx/conf.d/default.conf
    echo "[nginx] Mode HTTPS activé pour ${DOMAIN}"
else
    cp /etc/nginx/templates/nginx-http.conf /etc/nginx/conf.d/default.conf
    echo "[nginx] Mode HTTP (certificat absent pour ${DOMAIN})"
fi

exec nginx -g 'daemon off;'
