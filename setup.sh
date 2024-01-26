#!/bin/bash

USERNAME="karel"
USERPASS="fnN6QxYEGHCb8dhBVozv"
APPLICATION_NAME="dam-zipper"
APPLICATION_PATH="/home/$USERNAME/$APPLICATION_NAME"

# Create a new user
# Note: Automating password entry in this way is not recommended for security reasons.
# It's better to set up SSH keys for authentication.
adduser --disabled-password --gecos "" $USERNAME
echo "$USERNAME:$USERPASS" | sudo chpasswd

# Add user to sudo group
usermod -aG sudo $USERNAME

# Update and upgrade the system
sudo apt update -y
sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv nginx

# Create application directory
sudo mkdir -p $APPLICATION_PATH
sudo chown $USERNAME:$USERNAME $APPLICATION_PATH

# Switch to the application user
# Note: Switching users within a script can be complex. 
# It's better to run the script as the target user or handle permissions adequately.
# su $USERNAME

# The following commands should be run as the application user

# Create a virtual environment
python3 -m venv $APPLICATION_PATH/venv

# Activate the virtual environment
source $APPLICATION_PATH/venv/bin/activate

# Clone your application repository (or copy your application files to this directory)
git clone <your-repo-url> $APPLICATION_PATH

# Install your application's dependencies
pip install -r $APPLICATION_PATH/requirements.txt

# Install rclone
curl -s https://rclone.org/install.sh | sudo bash

# Configure uWSGI as a System Service
sudo mkdir -p /etc/uwsgi/sites

# Write the configuration file
sudo bash -c "cat > /etc/uwsgi/sites/$APPLICATION_NAME.ini" <<EOF
[uwsgi]
project = $APPLICATION_NAME
username = $USERNAME
base = $APPLICATION_PATH

chdir = %(base)
home = %(base)/venv
module = wsgi:app

master = true
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

# Start and enable uWSGI service
sudo systemctl daemon-reload
sudo systemctl start uwsgi
sudo systemctl enable uwsgi

# Configure Nginx to proxy requests to your Flask application
# (Assuming you have set up the domain and Nginx configuration)

# Allow traffic on Nginx ports (80 and 443)
sudo ufw allow 'Nginx Full'

# Allow traffic on flask port (5000) - DEBUG ONLY
sudo ufw allow 5000

