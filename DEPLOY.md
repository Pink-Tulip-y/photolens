# PhotoLens 部署指南

## 方式一：Windows 本地运行（最简单）

```bash
# 1. 安装依赖
pip install -r requirements-prod.txt

# 2. 设置环境变量（可选）
set PORT=5001
set SECRET_KEY=your-random-secret-key

# 3. 启动生产服务器
python run_prod.py
# 或双击 "启动PhotoLens.bat"
```

浏览器访问 `http://localhost:5001`

---

## 方式二：Docker 部署（推荐）

### 本地 Docker
```bash
# 构建并启动
docker compose up -d --build

# 查看日志
docker compose logs -f

# 停止
docker compose down
```

### Railway
```bash
# 1. 安装 Railway CLI
npm i -g @railway/cli

# 2. 登录并部署
railway login
railway init
railway up
```

Railway 会自动检测 Dockerfile 并构建。

### Render
在 [render.com](https://render.com) 创建 Web Service：
- **Runtime**: Docker
- **Repo**: 你的 GitHub 仓库
- **Port**: 5001

### Zeabur（国内友好）
在 [zeabur.com](https://zeabur.com) 创建服务：
- 导入 GitHub 仓库
- 自动检测 Dockerfile
- 国内访问速度快

---

## 方式三：VPS 手动部署

### 1. 上传代码
```bash
scp -r photo-scorer user@your-server:/opt/photo-scorer
```

### 2. 安装依赖
```bash
ssh user@your-server
cd /opt/photo-scorer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-prod.txt
```

### 3. 设置环境变量
```bash
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
export PORT=5001
```

### 4. 启动（gunicorn — Linux）
```bash
gunicorn app:app -w 2 -b 0.0.0.0:5001 --timeout 120
```

### 5. Nginx 反向代理
```nginx
server {
    listen 80;
    server_name your-domain.com;
    client_max_body_size 25M;
    client_body_timeout 120s;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;
    }

    location /static/ {
        alias /opt/photo-scorer/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

### 6. systemd 服务
```ini
[Unit]
Description=PhotoLens
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/photo-scorer
Environment="SECRET_KEY=your-secret-key"
Environment="PORT=5001"
ExecStart=/opt/photo-scorer/venv/bin/gunicorn app:app -w 2 -b 127.0.0.1:5001 --timeout 120
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable photolens --now
```

### 7. HTTPS
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## 方式四：国内云平台

### 阿里云 / 腾讯云 轻量应用服务器
1. 购买服务器（推荐 2核4G）
2. 安装 Ubuntu 22.04
3. 按「方式三」部署
4. **注意：中国大陆服务器需要 ICP 备案**

### 备案流程
1. 购买域名（阿里云万网 / 腾讯云 DNSPod）
2. 实名认证（通常 1-3 个工作日）
3. 提交 ICP 备案（通常 7-20 个工作日）
4. 备案通过后在网站底部添加备案号

---

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PORT` | `5001` | 服务端口 |
| `HOST` | `0.0.0.0` | 绑定地址 |
| `SECRET_KEY` | 随机生成 | Flask 密钥，生产环境务必设置 |
| `FLASK_DEBUG` | `0` | 调试模式（0/1） |
| `THREADS` | `4` | waitress 线程数 |

---

## 定时清理（Linux）

```bash
# crontab: 每小时清理 1 小时前的文件
0 * * * * find /opt/photo-scorer/static/uploads -mmin +60 -delete 2>/dev/null
0 * * * * find /opt/photo-scorer/static/enhanced -mmin +60 -delete 2>/dev/null
0 * * * * find /opt/photo-scorer/static/histograms -mmin +60 -delete 2>/dev/null
0 * * * * find /opt/photo-scorer/static/shares -mmin +1440 -delete 2>/dev/null
```

---

## 健康检查

部署后验证：`curl https://your-domain.com/api/health`
期望返回：`{"status":"ok","timestamp":...}`
