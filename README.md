"# Email Scraper API

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
