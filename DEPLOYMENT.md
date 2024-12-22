# Deployment Guide

This guide explains how to deploy the McLemore Auction Tools application on DigitalOcean.

## Prerequisites

1. A DigitalOcean account
2. A domain name pointing to your DigitalOcean droplet
3. SSH access to your droplet

## Initial Server Setup

1. Create a new Ubuntu droplet on DigitalOcean
2. SSH into your droplet:
   ```bash
   ssh root@your_server_ip
   ```

3. Create a new user:
   ```bash
   adduser mclemore
   usermod -aG sudo mclemore
   ```

4. Set up SSH keys for the new user
5. Disable root SSH access

## Installing Dependencies

1. Update package list and install system dependencies:
   ```bash
   sudo apt update
   sudo apt upgrade -y
   sudo apt install python3-pip python3-venv nginx supervisor -y
   ```

## Application Setup

1. Clone the repository:
   ```bash
   cd /var/www
   git clone https://github.com/willtmc/MAC-Tools-by-WTM.git mclemore
   cd mclemore
   ```

2. Create and activate virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   nano .env  # Edit with your actual values
   ```

## Gunicorn Setup

1. Create a Gunicorn systemd service file:
   ```bash
   sudo nano /etc/systemd/system/mclemore.service
   ```

2. Add the following content:
   ```ini
   [Unit]
   Description=McLemore Auction Tools
   After=network.target

   [Service]
   User=mclemore
   Group=www-data
   WorkingDirectory=/var/www/mclemore
   Environment="PATH=/var/www/mclemore/venv/bin"
   ExecStart=/var/www/mclemore/venv/bin/gunicorn --workers 3 --bind unix:mclemore.sock -m 007 wsgi:app

   [Install]
   WantedBy=multi-user.target
   ```

3. Start and enable the service:
   ```bash
   sudo systemctl start mclemore
   sudo systemctl enable mclemore
   ```

## Nginx Setup

1. Create an Nginx configuration file:
   ```bash
   sudo nano /etc/nginx/sites-available/mclemore
   ```

2. Add the following configuration:
   ```nginx
   server {
       listen 80;
       server_name tools.mclemoreauction.com;

       location / {
           include proxy_params;
           proxy_pass http://unix:/var/www/mclemore/mclemore.sock;
       }

       location /static {
           alias /var/www/mclemore/static;
       }
   }
   ```

3. Enable the site:
   ```bash
   sudo ln -s /etc/nginx/sites-available/mclemore /etc/nginx/sites-enabled
   sudo nginx -t
   sudo systemctl restart nginx
   ```

## SSL Setup with Certbot

1. Install Certbot:
   ```bash
   sudo apt install certbot python3-certbot-nginx -y
   ```

2. Obtain SSL certificate:
   ```bash
   sudo certbot --nginx -d tools.mclemoreauction.com
   ```

## Background Tasks Setup

1. Set up Supervisor for background tasks:
   ```bash
   sudo nano /etc/supervisor/conf.d/mclemore_tasks.conf
   ```

2. Add configurations for each background task:
   ```ini
   [program:mclemore_monitor]
   command=/var/www/mclemore/venv/bin/python /var/www/mclemore/scripts/monitor.py
   directory=/var/www/mclemore
   user=mclemore
   autostart=true
   autorestart=true
   stderr_logfile=/var/log/mclemore/monitor.err.log
   stdout_logfile=/var/log/mclemore/monitor.out.log

   [program:mclemore_daily_report]
   command=/var/www/mclemore/venv/bin/python /var/www/mclemore/scripts/daily_report.py
   directory=/var/www/mclemore
   user=mclemore
   autostart=true
   autorestart=true
   stderr_logfile=/var/log/mclemore/daily_report.err.log
   stdout_logfile=/var/log/mclemore/daily_report.out.log

   [program:mclemore_dbx_token]
   command=/var/www/mclemore/venv/bin/python /var/www/mclemore/scripts/dbx_token_refresh.py
   directory=/var/www/mclemore
   user=mclemore
   autostart=true
   autorestart=true
   stderr_logfile=/var/log/mclemore/dbx_token.err.log
   stdout_logfile=/var/log/mclemore/dbx_token.out.log
   ```

3. Create log directory and update permissions:
   ```bash
   sudo mkdir -p /var/log/mclemore
   sudo chown -R mclemore:mclemore /var/log/mclemore
   ```

4. Update Supervisor:
   ```bash
   sudo supervisorctl reread
   sudo supervisorctl update
   ```

## Maintenance

### Updating the Application

1. Pull latest changes:
   ```bash
   cd /var/www/mclemore
   git pull origin main
   ```

2. Update dependencies:
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Restart services:
   ```bash
   sudo systemctl restart mclemore
   sudo supervisorctl restart all
   ```

### Monitoring

- Check application status:
  ```bash
  sudo systemctl status mclemore
  ```

- Check Nginx status:
  ```bash
  sudo systemctl status nginx
  ```

- Check background tasks:
  ```bash
  sudo supervisorctl status
  ```

- View logs:
  ```bash
  sudo journalctl -u mclemore
  tail -f /var/log/mclemore/*.log
  ```
