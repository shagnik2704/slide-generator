# Deployment Guide: Slide Generator on AWS EC2

This guide details how to host the Slide Generator application on an AWS EC2 instance.

## 1. Prerequisites

- **AWS Account**: You need an active AWS account.
- **Domain Name (Optional)**: If you want a custom domain (e.g., `myslides.com`), purchase it via Route53 or another registrar.

## 2. Launching an EC2 Instance

1.  **Go to EC2 Dashboard** and click **Launch Instance**.
2.  **Name**: `slide-generator-server`
3.  **OS Image**: **Ubuntu Server 22.04 LTS (HVM)** (Free Tier eligible).
4.  **Instance Type**: **t3.small** (Recommended) or `t2.micro` (Free Tier, but might struggle with heavy video generation).
    *   *Note: Video generation and LaTeX compilation can be CPU intensive. `t3.small` provides a good balance.*
5.  **Key Pair**: Create a new key pair (e.g., `slide-gen-key`) and download the `.pem` file. **Keep this safe!**
6.  **Network Settings**:
    *   Allow SSH traffic from **My IP** (for security).
    *   Allow HTTP traffic from the internet.
    *   Allow HTTPS traffic from the internet.
7.  **Storage**: Increase to **20 GB** (LaTeX and video libraries take up space).
8.  **Launch Instance**.

## 3. Connecting to the Server

Open your terminal and run:

```bash
chmod 400 path/to/slide-gen-key.pem
ssh -i path/to/slide-gen-key.pem ubuntu@<YOUR_EC2_PUBLIC_IP>
```

## 4. System Setup & Dependencies

Update the system and install necessary packages.

```bash
sudo apt update && sudo apt upgrade -y

# Install Python, Node.js, FFmpeg, and Nginx
sudo apt install -y python3-pip python3-venv nodejs npm ffmpeg nginx git

# Install TeX Live (Required for LaTeX generation)
# This installs the full distribution to ensure all packages are available.
# Warning: This is large (~4GB) and takes time.
sudo apt install -y texlive-full
```

## 5. Application Setup

### Clone the Repository

```bash
cd ~
git clone <YOUR_GITHUB_REPO_URL> slide-generator
cd slide-generator
```

### Backend Setup

1.  **Create Virtual Environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  **Install Python Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Environment Variables**:
    Create a `.env` file:
    ```bash
    nano .env
    ```
    Paste your variables:
    ```env
    GOOGLE_API_KEY=your_api_key_here
    # Add other keys if necessary
    ```
    Press `Ctrl+X`, `Y`, `Enter` to save.

### Frontend Setup

1.  **Navigate to frontend**:
    ```bash
    cd chatbot-ui
    ```

2.  **Install Dependencies**:
    ```bash
    npm install
    ```

3.  **Build for Production**:
    ```bash
    npm run build
    ```
    This creates a `dist` folder with the static files.

## 6. Configure Nginx (Reverse Proxy)

Nginx will serve the frontend files and forward API requests to the backend.

1.  **Create Config**:
    ```bash
    sudo nano /etc/nginx/sites-available/slide-generator
    ```

2.  **Add Configuration**:
    Replace `your_domain_or_ip` with your EC2 Public IP or Domain.

    ```nginx
    server {
        listen 80;
        server_name your_domain_or_ip;

        # Serve Frontend (Vite Build)
        location / {
            root /home/ubuntu/slide-generator/chatbot-ui/dist;
            index index.html;
            try_files $uri $uri/ /index.html;
        }

        # Proxy API Requests to FastAPI
        location /api {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
        
        # Proxy WebSocket Requests (if used)
        location /ws {
            proxy_pass http://127.0.0.1:8000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
    ```

3.  **Enable Site**:
    ```bash
    sudo ln -s /etc/nginx/sites-available/slide-generator /etc/nginx/sites-enabled/
    sudo rm /etc/nginx/sites-enabled/default  # Remove default config
    sudo nginx -t  # Test configuration
    sudo systemctl restart nginx
    ```

## 7. Run Backend as a Service

Use `systemd` to keep the backend running in the background.

1.  **Create Service File**:
    ```bash
    sudo nano /etc/systemd/system/slide-backend.service
    ```

2.  **Add Configuration**:
    ```ini
    [Unit]
    Description=Slide Generator Backend
    After=network.target

    [Service]
    User=ubuntu
    WorkingDirectory=/home/ubuntu/slide-generator
    EnvironmentFile=/home/ubuntu/slide-generator/.env
    ExecStart=/home/ubuntu/slide-generator/venv/bin/uvicorn server:app --host 127.0.0.1 --port 8000
    Restart=always

    [Install]
    WantedBy=multi-user.target
    ```

3.  **Start Service**:
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl start slide-backend
    sudo systemctl enable slide-backend
    ```

## 8. Final Checks

1.  Visit `http://<YOUR_EC2_PUBLIC_IP>` in your browser.
2.  You should see your app!
3.  Try generating a slide deck to verify that LaTeX and FFmpeg are working correctly on the server.

---

### Troubleshooting

-   **Logs**: Check backend logs with `journalctl -u slide-backend -f`.
-   **Permissions**: Ensure `assets` and `output` directories are writable if the app saves files there.
    ```bash
    chmod -R 755 assets output generated_images audio
    ```
