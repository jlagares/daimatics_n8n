# Scraper Service Setup (Debian) — Step-by-Step

## 0) Prereqs
- Script path: `/home/debian/scraper/start_scraper`
- Run as user: `debian`
- Your script is self-contained (it sets up any needed env itself)

---

## 1) Make script executable
```bash
cd /home/debian/scraper
chmod +x start_scraper
```

---

## 2) Create a **systemd user** service
```bash
mkdir -p ~/.config/systemd/user
nano ~/.config/systemd/user/scraper.service
```

Paste:
```ini
[Unit]
Description=Email scraper service
After=network-online.target

[Service]
# Ensure the log directory exists each start
ExecStartPre=/bin/mkdir -p /tmp/scraper

# Run from project dir and capture logs to a single file
WorkingDirectory=/home/debian/scraper
ExecStart=/bin/bash -lc 'exec ./start_scraper >> /tmp/scraper/scraper.log 2>&1'

Restart=always
RestartSec=3
NoNewPrivileges=true

[Install]
WantedBy=default.target
```

> If your script does not need a login shell, replace `ExecStart=...` with:
> `ExecStart=/home/debian/scraper/start_scraper >> /tmp/scraper/scraper.log 2>&1`

---

## 3) Allow user services to run after logout
```bash
sudo loginctl enable-linger debian
```

---

## 4) Start and enable the service
```bash
systemctl --user daemon-reload
systemctl --user enable --now scraper.service
```

---

## 5) Verify it’s running
```bash
systemctl --user status scraper.service
ls -l /tmp/scraper/
tail -n 100 /tmp/scraper/scraper.log
```

---

## 6) Install and configure logrotate for `/tmp`
> `/tmp` is volatile (cleared on some reboots). This keeps logs tidy while they exist.

**Install logrotate:**
```bash
sudo apt update
sudo apt install -y logrotate
```

**Add rotation rule:**
```bash
sudo bash -c 'cat >/etc/logrotate.d/scraper <<EOF
/tmp/scraper/scraper.log {
    daily
    rotate 7
    missingok
    notifempty
    compress
    delaycompress
    copytruncate
    create 0644 debian debian
}
EOF'
```

**Test rotation:**
```bash
sudo logrotate -f /etc/logrotate.d/scraper
ls -l /tmp/scraper/
```

> **Want persistent logs?** Use `/var/log/scraper/scraper.log` instead of `/tmp/...` and:
> ```bash
> sudo mkdir -p /var/log/scraper
> sudo chown debian:debian /var/log/scraper
> ```
> Update `ExecStartPre` and `ExecStart` paths plus the logrotate file accordingly.

---

## 7) Daily workflow — stop / start / restart

**Stop service (leaves it enabled for next boot):**
```bash
systemctl --user stop scraper.service
```

**Start service:**
```bash
systemctl --user start scraper.service
```

**Restart service (after code changes):**
```bash
systemctl --user restart scraper.service
```

**Disable auto-start (won’t start on boot):**
```bash
systemctl --user disable scraper.service
```

**Re-enable auto-start:**
```bash
systemctl --user enable scraper.service
```

**After editing the unit file:**
```bash
systemctl --user daemon-reload
systemctl --user restart scraper.service
```

---

## 8) Logs & troubleshooting

**Follow logs:**
```bash
tail -f /tmp/scraper/scraper.log
```

**Recent systemd journal (user scope):**
```bash
journalctl --user -u scraper.service -n 200 --no-pager
```

**Force log rotation:**
```bash
sudo logrotate -f /etc/logrotate.d/scraper
```

**Check service health:**
```bash
systemctl --user status scraper.service
```

---

## 9) Quick checklist
- [ ] `start_scraper` is executable  
- [ ] `~/.config/systemd/user/scraper.service` exists  
- [ ] `sudo loginctl enable-linger debian` done  
- [ ] Service enabled and active  
- [ ] Logs writing to `/tmp/scraper/scraper.log` (or `/var/log/scraper/scraper.log`)  
- [ ] `logrotate` rule present and tested
