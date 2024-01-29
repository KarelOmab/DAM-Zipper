#!/bin/bash
USERNAME="sammy"
APPLICATION_NAME="DAM-Zipper"
APPLICATION_PATH="/home/$USERNAME/$APPLICATION_NAME"

# Fetch the public IPv4 address of the server
SERVER_IP=$(curl -s icanhazip.com)
PORT=5000

# The following commands should be run as the application user
sudo apt install -y python3 python3-pip python3-venv nginx

# Create a virtual environment
python3 -m venv $APPLICATION_PATH/venv

# Activate the virtual environment
source $APPLICATION_PATH/venv/bin/activate

# Install your application's dependencies
pip install -r $APPLICATION_PATH/requirements.txt

# Install rclone
curl -s https://rclone.org/install.sh | sudo bash

# Configure uWSGI as a System Service
sudo mkdir -p /etc/uwsgi/sites

# Write the configuration file
sudo bash -c "cat > /etc/uwsgi/sites/$APPLICATION_NAME.ini" <<EOF
[uwsgi]
uid = sammy
gid = www-data
project = $APPLICATION_NAME
username = $USERNAME
base = $APPLICATION_PATH

chdir = %(base)
home = %(base)/venv
module = wsgi:app

master = true
enable-threads = true
processes = 5

socket = /run/uwsgi/%(project).sock
chmod-socket = 660
vacuum = true

die-on-term = true
EOF

# Write the systemd service file for uWSGI
sudo bash -c "cat > /etc/systemd/system/uwsgi.service" <<EOF
[Unit]
Description=uWSGI Emperor Service

[Service]
ExecStartPre=/bin/bash -c 'mkdir -p /run/uwsgi; chown $USERNAME:www-data /run/uwsgi'
ExecStart=$APPLICATION_PATH/venv/bin/uwsgi --emperor /etc/uwsgi/sites
Restart=always
KillSignal=SIGQUIT
Type=notify
NotifyAccess=all

[Install]
WantedBy=multi-user.target
EOF

# Set proper permissions for the systemd service file
sudo chown root:root /etc/systemd/system/uwsgi.service
sudo chmod 644 /etc/systemd/system/uwsgi.service

# Start and enable uWSGI service
sudo systemctl daemon-reload
sudo systemctl start uwsgi
sudo systemctl enable uwsgi

# Configure Nginx to proxy requests to your Flask application

# Create Nginx server block for the application
NGINX_CONFIG="/etc/nginx/sites-available/$APPLICATION_NAME"
sudo bash -c "cat > $NGINX_CONFIG" <<EOF
server {
    listen 80;
    server_name $SERVER_IP;  # Replace with your domain or IP

    location / {
        include uwsgi_params;
        uwsgi_pass unix:/run/uwsgi/$APPLICATION_NAME.sock;
    }
}
EOF

# Enable the site by creating a symbolic link
sudo ln -s $NGINX_CONFIG /etc/nginx/sites-enabled/

# Reload Nginx to apply the new configuration
sudo systemctl reload nginx

# Allow traffic on Nginx ports (80 and 443)
sudo ufw allow 'Nginx Full'

# Allow traffic on flask port (5000) - DEBUG ONLY
sudo ufw allow $PORT

echo "Test to make sure your uWSGI service is running:"
echo "sudo systemctl status uwsgi"

echo "!!! Finally, DONT FORGET the following !!!"
echo "1. Manually add your rclone configuration(s) <rclone config>"
echo "2. Update your API key (value) in the '.env' file"
