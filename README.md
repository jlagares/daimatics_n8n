# Email Scraper API

A powerful email scraping service built with Scrapy and FastAPI that extracts email addresses from websites.

## Features

- 🕷️ **Advanced Web Scraping**: Built on Scrapy framework for robust web crawling
- 🚀 **FastAPI Integration**: RESTful API interface for easy integration
- 📧 **Email Detection**: Finds emails in mailto links, visible text, and obfuscated formats
- 🔍 **Progress Tracking**: Real-time progress logging and statistics
- 🎯 **Smart Crawling**: Contact page bias and depth/domain limits
- ⚡ **Performance Optimized**: Configurable concurrency and throttling

## Project Structure

```
daimatics_n8n/
├── email_scraper/           # Scrapy project directory
│   ├── email_scraper/       # Scrapy package
│   │   ├── spiders/         # Scrapy spiders
│   │   │   └── email_spider.py  # Main email scraping spider
│   │   ├── settings.py      # Scrapy settings
│   │   └── ...
│   └── scrapy.cfg          # Scrapy configuration
├── src/                    # FastAPI application
│   ├── scraper_api.py      # Main API application
│   └── ...
├── venv/                   # Virtual environment
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/jlagares/daimatics_n8n.git
cd daimatics_n8n
```

### 2. Set Up Virtual Environment

**On Windows:**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**On Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Verify Scrapy Installation

```bash
scrapy version
```

You should see output like:
```
Scrapy 2.11.0 - no active project
```

### 5. Test the Scrapy Spider

Navigate to the email_scraper directory and test the spider:

```bash
cd email_scraper
scrapy crawl email_spider -a start_urls=https://daimatics.agency -o test_emails.json
```

### 6. Start the FastAPI Server

From the project root:

```bash
cd src
python scraper_api.py
```

The API will be available at:
- **Main API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## API Usage

### Health Check

```bash
curl -X GET "http://localhost:8000/health"
```

### Basic Email Scraping

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://daimatics.agency"}'
```

### Advanced Scraping with Parameters

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://daimatics.agency",
    "max_depth": 3,
    "max_pages_per_domain": 20,
    "contact_bias": true,
    "allow_patterns": "contact,about"
  }'
```

### PowerShell Commands (Windows)

**Health Check:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health" -Method GET
```

**Basic Scraping:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/scrape" -Method POST -ContentType "application/json" -Body '{"url": "https://daimatics.agency"}'
```

**Advanced Scraping:**
```powershell
$body = @{
    url = "https://daimatics.agency"
    max_depth = 3
    max_pages_per_domain = 20
    contact_bias = $true
    allow_patterns = "contact,about"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/scrape" -Method POST -ContentType "application/json" -Body $body
```

## API Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | string (URL) | **required** | Target website URL to scrape |
| `max_depth` | integer | 2 | Maximum crawl depth |
| `max_pages_per_domain` | integer | 50 | Maximum pages to scrape per domain |
| `contact_bias` | boolean | true | Prioritize contact/about pages |
| `allowed_domains` | string | auto-detected | Comma-separated list of allowed domains |
| `allow_patterns` | string | none | Comma-separated patterns to prioritize |

## API Response Format

```json
{
  "success": true,
  "url": "https://daimatics.agency/",
  "emails_found": [
    {
      "page_url": "https://daimatics.agency",
      "domain": "daimatics.agency",
      "emails": ["hola@daimatics.agency"],
      "depth": 0,
      "mailto_count": 0,
      "text_count": 1,
      "obfuscated_count": 0,
      "timestamp": 1697287234.567
    }
  ],
  "total_unique_emails": 1,
  "unique_emails": ["hola@daimatics.agency"],
  "pages_scraped": 15,
  "error": null
}
```

## Direct Scrapy Usage

You can also use the Scrapy spider directly without the API:

### Basic Usage

```bash
cd email_scraper
scrapy crawl email_spider -a start_urls=https://example.com -o emails.json
```

### With Custom Parameters

```bash
scrapy crawl email_spider \
  -a start_urls=https://example.com \
  -a max_depth=3 \
  -a max_pages_per_domain=50 \
  -a contact_bias=true \
  -a allow=contact,about \
  -o emails.json
```

### Performance Optimization

For faster scraping (use with caution):

```bash
scrapy crawl email_spider \
  -a start_urls=https://example.com \
  -s CONCURRENT_REQUESTS=32 \
  -s CONCURRENT_REQUESTS_PER_DOMAIN=8 \
  -s DOWNLOAD_DELAY=0.1 \
  -s ROBOTSTXT_OBEY=False \
  -o emails.json
```

## Configuration

### Scrapy Settings

Key settings in `email_scraper/email_scraper/settings.py`:

- `ROBOTSTXT_OBEY`: Respect robots.txt (default: False for speed)
- `CONCURRENT_REQUESTS`: Number of concurrent requests (default: 16)
- `DOWNLOAD_DELAY`: Delay between requests (default: 0.1s)
- `AUTOTHROTTLE_ENABLED`: Auto-adjust delays (default: True)

### FastAPI Configuration

The API server can be configured by modifying `src/scraper_api.py`:

- **Host/Port**: Change in `uvicorn.run()` call
- **Timeout**: Modify `subprocess.run(timeout=300)`
- **Logging**: Adjust logging levels and formats

## Troubleshooting

### Virtual Environment Issues

If you get "Virtual environment Python not found" errors:

1. Ensure you're in the correct directory
2. Activate the virtual environment
3. Verify Python path: `which python` (Linux/Mac) or `where python` (Windows)

### Common Issues

**"Module not found" errors:**
```bash
pip install --upgrade -r requirements.txt
```

**Permission denied (Linux/Mac):**
```bash
chmod +x scripts/*.sh
```

**Scrapy not found:**
```bash
pip install scrapy
scrapy version
```

## Debian/Ubuntu Deployment

### System Requirements

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python and essential tools
sudo apt install -y python3 python3-pip python3-venv python3-dev
sudo apt install -y build-essential libxml2-dev libxslt1-dev libffi-dev libssl-dev
sudo apt install -y curl git nginx supervisor

# Install optional tools
sudo apt install -y htop tree nano
```

### Deployment Steps

#### 1. Create Deployment User

```bash
# Create a dedicated user for the application
sudo adduser scraper
sudo usermod -aG sudo scraper

# Switch to the scraper user
sudo su - scraper
```

#### 2. Clone and Setup Project

```bash
# Clone the repository
git clone https://github.com/jlagares/daimatics_n8n.git
cd daimatics_n8n

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Verify installation
scrapy version
```

#### 3. Test the Application

```bash
# Test Scrapy spider
cd email_scraper
scrapy crawl email_spider -a start_urls=https://httpbin.org/html -o test.json
cat test.json

# Test FastAPI server
cd ../src
python scraper_api.py &

# Test API endpoints
curl http://localhost:8000/health
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://httpbin.org/html"}'

# Stop the test server
pkill -f "python scraper_api.py"
```

#### 4. Production Configuration with Supervisor

Create a supervisor configuration:

```bash
sudo nano /etc/supervisor/conf.d/email-scraper-api.conf
```

Add the following configuration:

```ini
[program:email-scraper-api]
command=/home/scraper/daimatics_n8n/venv/bin/python /home/scraper/daimatics_n8n/src/scraper_api.py
directory=/home/scraper/daimatics_n8n/src
user=scraper
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/email-scraper-api.log
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=5
environment=PATH="/home/scraper/daimatics_n8n/venv/bin"
```

Enable and start the service:

```bash
# Update supervisor
sudo supervisorctl reread
sudo supervisorctl update

# Start the service
sudo supervisorctl start email-scraper-api

# Check status
sudo supervisorctl status email-scraper-api

# View logs
sudo tail -f /var/log/email-scraper-api.log
```

#### 5. Nginx Reverse Proxy (Optional)

Create Nginx configuration:

```bash
sudo nano /etc/nginx/sites-available/email-scraper-api
```

Add the following configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }
}
```

Enable the site:

```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/email-scraper-api /etc/nginx/sites-enabled/

# Test nginx configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx

# Enable nginx to start on boot
sudo systemctl enable nginx
```

#### 6. Firewall Configuration

```bash
# Enable UFW firewall
sudo ufw enable

# Allow SSH
sudo ufw allow ssh

# Allow HTTP and HTTPS
sudo ufw allow 80
sudo ufw allow 443

# Check status
sudo ufw status
```

#### 7. SSL Certificate with Let's Encrypt (Optional)

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Test auto-renewal
sudo certbot renew --dry-run
```

### Service Management Commands

```bash
# Start/Stop/Restart the service
sudo supervisorctl start email-scraper-api
sudo supervisorctl stop email-scraper-api
sudo supervisorctl restart email-scraper-api

# Check service status
sudo supervisorctl status email-scraper-api

# View real-time logs
sudo tail -f /var/log/email-scraper-api.log

# Check Nginx status
sudo systemctl status nginx

# Restart Nginx
sudo systemctl restart nginx
```

### Environment-Specific Configuration

Create a production configuration file:

```bash
nano ~/daimatics_n8n/src/config.py
```

```python
import os

# Production settings
DEBUG = False
HOST = "0.0.0.0"
PORT = 8000
WORKERS = 4

# Scrapy settings for production
SCRAPY_SETTINGS = {
    "CONCURRENT_REQUESTS": 16,
    "CONCURRENT_REQUESTS_PER_DOMAIN": 4,
    "DOWNLOAD_DELAY": 0.5,
    "RANDOMIZE_DOWNLOAD_DELAY": 0.5,
    "AUTOTHROTTLE_ENABLED": True,
    "AUTOTHROTTLE_START_DELAY": 0.5,
    "AUTOTHROTTLE_MAX_DELAY": 3.0,
    "ROBOTSTXT_OBEY": True,
    "USER_AGENT": "EmailScraper (+http://your-domain.com)",
}
```

### Monitoring and Maintenance

#### Log Rotation

```bash
# Configure log rotation
sudo nano /etc/logrotate.d/email-scraper-api
```

```
/var/log/email-scraper-api.log {
    daily
    missingok
    rotate 30
    compress
    notifempty
    copytruncate
}
```

#### System Resource Monitoring

```bash
# Monitor system resources
htop

# Check disk usage
df -h

# Check memory usage
free -h

# Monitor API process
ps aux | grep scraper_api

# Check open files/connections
sudo netstat -tlnp | grep :8000
```

#### Health Check Script

Create a health check script:

```bash
nano ~/health_check.sh
```

```bash
#!/bin/bash

API_URL="http://localhost:8000/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $API_URL)

if [ $RESPONSE -eq 200 ]; then
    echo "$(date): API is healthy"
else
    echo "$(date): API is down (HTTP $RESPONSE)"
    sudo supervisorctl restart email-scraper-api
fi
```

```bash
chmod +x ~/health_check.sh

# Add to crontab for automatic checks
crontab -e
# Add: */5 * * * * /home/scraper/health_check.sh >> /home/scraper/health_check.log 2>&1
```

### Troubleshooting Debian Deployment

#### Common Issues

**Permission denied errors:**
```bash
# Fix ownership
sudo chown -R scraper:scraper /home/scraper/daimatics_n8n

# Fix permissions
chmod +x /home/scraper/daimatics_n8n/src/scraper_api.py
```

**Virtual environment not found:**
```bash
# Verify virtual environment
ls -la /home/scraper/daimatics_n8n/venv/bin/

# Recreate if necessary
cd /home/scraper/daimatics_n8n
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Service won't start:**
```bash
# Check supervisor logs
sudo supervisorctl tail email-scraper-api

# Check system logs
sudo journalctl -u supervisor

# Manually test the command
cd /home/scraper/daimatics_n8n/src
/home/scraper/daimatics_n8n/venv/bin/python scraper_api.py
```

**Port already in use:**
```bash
# Find process using port 8000
sudo netstat -tlnp | grep :8000
sudo lsof -i :8000

# Kill process if necessary
sudo kill -9 <PID>
```

### Testing on Debian

```bash
# Test from local machine
curl -X GET "http://your-server-ip:8000/health"

# Test with domain (if configured)
curl -X GET "http://your-domain.com/health"

# Test scraping
curl -X POST "http://your-server-ip:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://httpbin.org/html"}'
```

## Development

### Running Tests

```bash
# Test the spider directly
cd email_scraper
scrapy check email_spider

# Test a simple crawl
scrapy crawl email_spider -a start_urls=https://httpbin.org/html -o test.json
```

### Adding Custom Spiders

1. Create a new spider in `email_scraper/email_scraper/spiders/`
2. Follow Scrapy conventions
3. Test with `scrapy crawl spider_name`

## Performance Monitoring

The spider provides detailed logging:

- 📄 **Page visits**: Every page scraped with depth info
- ✉️ **Email discoveries**: Details about found emails
- 🔗 **Link discovery**: Number of links found per page
- 📈 **Progress updates**: Periodic statistics (every 5 seconds)
- 🏁 **Final summary**: Complete statistics when finished

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
- Create an issue on GitHub
- Check the [Scrapy documentation](https://docs.scrapy.org/)
- Check the [FastAPI documentation](https://fastapi.tiangolo.com/)" 

