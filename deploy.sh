#!/bin/bash
# deploy.sh
# Escrito para despliegues en VPS (Ubuntu 22.04)

echo "--- Iniciando Despliegue de Cuaderno de Campo ---"

# 1. Asegurar dependencias de Python
sudo apt update
sudo apt install -y python3-pip python3-venv nginx

# 2. Configurar entorno Python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn

# 3. Inicializar Base de Datos (si no existe)
python db.py

# 4. Configurar Gunicorn Service
sudo cat > /etc/systemd/system/cuaderno.service << EOF
[Unit]
Description=Gunicorn instance to serve Cuaderno de Campo
After=network.target

[Service]
User=$USER
Group=www-data
WorkingDirectory=$(pwd)/backend
Environment="PATH=$(pwd)/venv/bin"
ExecStart=$(pwd)/venv/bin/gunicorn --workers 3 --bind unix:cuaderno.sock -m 007 wsgi:app

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl start cuaderno
sudo systemctl enable cuaderno

# 5. Configurar NGINX
sudo cp ../deploy/nginx.conf /etc/nginx/sites-available/cuaderno
sudo ln -sf /etc/nginx/sites-available/cuaderno /etc/nginx/sites-enabled
sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl restart nginx

echo "Despliegue completado con éxito en el puerto 80"
