import re
from collections import defaultdict
from urllib.parse import urlparse

import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


EMAIL_REGEX = re.compile(
    r"""(?ix)                        # ignore case, verbose
    \b
    [A-Z0-9._%+\-]+                 # local part
    @
    (?:[A-Z0-9\-]+\.)+              # domain labels
    [A-Z]{2,24}                     # TLD
    \b
    """
)

class EmailSpider(CrawlSpider):
    name = "email_spider"

    # Default settings (can be overridden via -s at runtime)
    custom_settings = {
        # be polite
        "ROBOTSTXT_OBEY": False,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 0.1,  # Reduced from 0.5
        "AUTOTHROTTLE_MAX_DELAY": 2.0,    # Reduced from 5.0
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 8.0,  # Target concurrent requests
        "CONCURRENT_REQUESTS": 16,
        # Timeout settings
        "DOWNLOAD_TIMEOUT": 10,  # Reduced from 20
        "RETRY_TIMES": 1,  # Reduced retries
        "RANDOMIZE_DOWNLOAD_DELAY": 0.2,  # Add some randomization
        # avoid non-HTML
        "HTTPCACHE_ENABLED": False,
        # useful when you want consistent output ordering
        "FEED_EXPORT_ENCODING": "utf-8",
    }

    # Crawl rules — follow in-scope links and parse pages for emails
    rules = (
        Rule(
            LinkExtractor(
                allow=(),  # you can pass allow patterns via -a allow=regex1,regex2
                deny_extensions=set(LinkExtractor().deny_extensions) | {"pdf", "jpg", "jpeg", "png", "gif", "svg", "webp", "zip", "mp4", "avi", "mov", "mp3"},
                unique=True,
            ),
            callback="parse_page",
            follow=True,
        ),
    )

    def __init__(
        self,
        start_urls=None,
        allowed_domains=None,
        allow=None,
        max_depth=None,
        max_pages_per_domain=200,
        contact_bias=True,
        *args,
        **kwargs,
    ):
        """
        Args you can pass with -a:
          - start_urls: comma-separated URLs to start from (required)
          - allowed_domains: comma-separated domains (optional; auto-inferred from start_urls if omitted)
          - allow: comma-separated regex patterns to prioritize (e.g., 'contact,about,legal,privacy')
          - max_depth: limit crawl depth (you can also use -s DEPTH_LIMIT=2)
          - max_pages_per_domain: stop following links after N pages per domain
          - contact_bias: 'true'/'false' — prioritize likely contact pages in scheduling
        """
        super().__init__(*args, **kwargs)

        if not start_urls:
            raise ValueError("You must pass -a start_urls=https://example.com (comma-separated for multiple).")

        self.start_urls = [u.strip() for u in start_urls.split(",") if u.strip()]

        if allowed_domains:
            self.allowed_domains = [d.strip().lower() for d in allowed_domains.split(",") if d.strip()]
        else:
            # infer from start_urls
            self.allowed_domains = list({urlparse(u).hostname for u in self.start_urls if urlparse(u).hostname})

        # optional depth limit (can also be set via -s DEPTH_LIMIT=)
        if max_depth is not None:
            try:
                self.max_depth = int(max_depth)
            except ValueError:
                self.max_depth = None
        else:
            self.max_depth = None

        # per-domain page cap
        self.max_pages_per_domain = int(max_pages_per_domain)

        # optional allow patterns to bias contact pages
        self.allow_patterns = [p.strip() for p in allow.split(",")] if allow else []
        self.contact_bias = str(contact_bias).lower() in {"1", "true", "yes", "y"}

        # internal counters
        self._pages_per_domain = defaultdict(int)

        # prepare a biased LinkExtractor if allow patterns provided
        if self.allow_patterns:
            self.contact_extractor = LinkExtractor(allow=self.allow_patterns, unique=True)
        else:
            self.contact_extractor = None

    def _request_allowed(self, url):
        host = urlparse(url).hostname or ""
        # enforce allowed_domains
        if self.allowed_domains and not any(host.endswith(d) for d in self.allowed_domains):
            return False
        # enforce per-domain limit
        if self._pages_per_domain[host] >= self.max_pages_per_domain:
            return False
        return True

    def _schedule_request(self, request, depth):
        if self.max_depth is not None and depth > self.max_depth:
            return None
        if not self._request_allowed(request.url):
            return None
        return request

    def _requests_to_follow(self, response):
        """Override CrawlSpider behavior to enforce depth & per-domain limits + contact bias."""
        if getattr(response, "encoding", None) is None or "text" not in response.headers.get("Content-Type", b"").decode().lower():
            return

        # extract links — first contact-biased links (if configured), then general links
        seen = set()

        def gen_links(le):
            for link in le.extract_links(response):
                if link.url not in seen and self._request_allowed(link.url):
                    seen.add(link.url)
                    yield link

        if self.contact_bias and self.contact_extractor:
            for link in gen_links(self.contact_extractor):
                req = scrapy.Request(link.url, callback=self.parse_page)
                req.meta["depth"] = response.meta.get("depth", 0) + 1
                scheduled = self._schedule_request(req, req.meta["depth"])
                if scheduled:
                    yield scheduled

        # general links via the first (and only) Rule's LinkExtractor
        for rule in self._rules:
            for link in gen_links(rule.link_extractor):
                req = scrapy.Request(link.url, callback=rule.callback)
                req.meta["depth"] = response.meta.get("depth", 0) + 1
                scheduled = self._schedule_request(req, req.meta["depth"])
                if scheduled:
                    yield scheduled

    def parse_start_url(self, response):
        return self.parse_page(response)

    def parse_page(self, response):
        # bump counter per domain
        host = urlparse(response.url).hostname or ""
        self._pages_per_domain[host] += 1

        # collect emails from mailto: and from on-page text
        emails = set()

        # 1) mailto: links
        for href in response.css('a[href^="mailto:"]::attr(href)').getall():
            # strip "mailto:" and any query params after ? (e.g., subject)
            addr = href.split("mailto:", 1)[1].split("?", 1)[0]
            # mailto can include multiple addresses separated by commas
            for part in addr.split(","):
                part = part.strip()
                if EMAIL_REGEX.fullmatch(part):
                    emails.add(part)

        # 2) visible text emails
        text = " ".join(response.css("body *::text").getall())
        for m in EMAIL_REGEX.finditer(text):
            emails.add(m.group(0))

        # optional: normalize common obfuscations like "info [at] example [dot] com"
        obfus_text = text.replace("[at]", "@").replace("(at)", "@").replace(" at ", "@").replace(" [dot] ", ".").replace(" (dot) ", ".")
        for m in EMAIL_REGEX.finditer(obfus_text):
            emails.add(m.group(0))

        if emails:
            yield {
                "page_url": response.url,
                "domain": host,
                "emails": sorted(emails),
            }

        # You could also yield site-level aggregation, but keeping per-page yields is simpler for dedup later.
