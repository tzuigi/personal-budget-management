#!/bin/bash

# Script pentru configurarea și instalarea certificatului SSL pe EC2
# Trebuie rulat după ce celelalte configurări sunt complete

# Verificăm dacă certbot este instalat
if ! command -v certbot &> /dev/null; then
    echo "Instalare certbot..."
    amazon-linux-extras install epel -y
    yum install -y certbot python2-certbot-nginx
fi

# Obținem certificatul SSL prin Let's Encrypt
# Înlocuiți yourdomain.com cu domeniul real
certbot --nginx -d yourdomain.com -d www.yourdomain.com --non-interactive --agree-tos --email your-email@example.com

# Configurăm reînnoirea automată a certificatelor
echo "0 0,12 * * * root python -c 'import random; import time; time.sleep(random.random() * 3600)' && certbot renew -q" | sudo tee -a /etc/crontab > /dev/null
