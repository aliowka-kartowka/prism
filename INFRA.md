# FreeNet VPN — INFRASTRUCTURE & ARCHITECTURE

FreeNet Monster (Честный Мониторинг) is a high-resilience VPN platform and censorship monitor designed specifically for the Russian market.

## 🏗 System Architecture

The infrastructure is split into two main geographic regions (Germany and Russia) to balance high-speed global connectivity with local monitoring capabilities.

### 1. Hetzner Hub (Germany / Global Exit)
The primary management hub and VPN exit point.
*   **Host**: `178.104.135.156` (Hetzner)
*   **Core Services**:
    *   **Marzban**: Xray management panel handling users, subscriptions, and protocols.
    *   **Nginx Reverse Proxy**: Handles SSL termination and protects the backend services. Configured for **WebSocket proxying** on port 443 to support Cloudflare CDN.
    *   **Cloudflare Proxy**: `vpn.freenet.monster` is proxied via Cloudflare to mask the Hetzner IP.
    *   **Cloudflare WARP**: Local SOCKS5 proxy (`127.0.0.1:40000`) for "clean" IP exits (e.g., for ChatGPT).

### 2. Moscow Monitoring Node (Russia)
A dedicated node within Russia to perform real-time censorship and connectivity checks, now acting as a subscription mirror.
*   **Host**: `94.159.117.222`
*   **Functionality**:
    *   **Честный Мониторинг Dashboard**: Located at `/var/www/monitor`.
    *   **Moscow Mirror**: Proxies `http://94.159.117.222/sub/` requests directly to the back-end, bypassing domain-level blocks (SNI/DNS).
    *   **Dual-Path API**: Tests site accessibility via both Direct (RU ISP) and FreeNet (VPN) paths.
    *   **Smart Header Validation**: `check_url` logic now verifies domain-specific headers (`Server: gws`, `facebook`, `cloudflare`) to detect and report ISP splash-page interception.

---

## 🛰 Connectivity Strategies

To ensure maximum resilience against Roskomnadzor (RKN), the platform provides multiple connection paths and automated routing:

### 🛡️ Subscription Delivery (Anti-Block)
*   **Primary Link**: `https://vpn.freenet.monster/sub/<token>` (Cloudflare CDN)
*   **Moscow Mirror**: `http://94.159.117.222/sub/<token>` (Raw IP fallback for Russia)
*   **Telegram Base64**: Raw VLESS config string provided directly in the bot response for "Import from Clipboard". This is the most resilient method as it requires zero domain resolution.

### 🚀 FreeNet Direct (VLESS REALITY)
*   **Transport**: TCP (Port 2053)
*   **Best for**: Maximum performance and low latency. Uses REALITY to camouflage as standard HTTPS traffic to `yandex.ru`.

### 🛡️ FreeNet CDN (VLESS WebSocket + Cloudflare)
*   **Transport**: WebSocket (Port 443 via TLS)
*   **Best for**: High-resilience bypass if the main server IP is flagged. Traffic is masked by Cloudflare's edge network.

### ✨ Sing-box Automatic Split-Tunneling
*   **Configuration**: Automated JSON served via `/api/config/singbox/<username>`.
*   **Mechanism**: Automatically routes domestic Russian traffic (`geoip:ru`, `geosite:ru`, `.ru` domains) to **Direct** (local ISP), avoiding VPN latency and potential blocks from Russian state sites.

---

## 🛠 Project Components

*   `monitor/`: The main premium monitoring dashboard.
*   `monitor/server.py`: The backend logic, now including the **Sing-box JSON generator** and **Telegram Authentication** validation.
*   `deploy_monitor.sh`: Automated deployment script to sync changes across both Moscow and Hetzner nodes.

---

## 💰 Monetization & Subscriptions (Stripe)
*   **Stripe Integration**: Automated via Stripe Payment Links and Webhooks.
*   **Webhooks**: `/webhook/stripe` endpoint handles `checkout.session.completed` and `customer.subscription.*` events.
*   **Automation**: The server automatically updates Marzban users:
    *   **Activation**: `data_limit = 0` (Unlimited), `status = active`, `note = PREMIUM_USER`.
    *   **Deactivation**: `status = disabled` on payment failure or cancellation.
*   **Pricing Tiers**:
    *   **Monster Pack**: $6.99 / 30 Days.
    *   **Monster Guard**: $14.99 / 90 Days (Popular).
    *   **Monster Legend**: $49.99 / 1 Year (VIP).

---

## 🎁 Trial System
*   **No-Card Trial**: 1 Day of full access without providing payment details.
*   **Activation**: Direct link to Telegram Bot (`?start=trial`) for instant provisioning.
*   **Limits**: 10GB for 24 hours. Renewable daily to ensure continuous access for potential subscribers.

---

## 🧭 Troubleshooting

1.  **Hetzner IP Blocked**: Instruct users to switch to the **FreeNet CDN** link or use the **Sing-box Automatic** config which includes both paths.
2.  **DNS Failures**: The Sing-box config uses a dual-DNS strategy: `1.1.1.1` (via VPN) for global sites and `8.8.8.8` (Direct) for Russian domains to avoid corruption.
3.  **Bot Redirect Errors**: The old bot-redirect flow has been deprecated in favor of the in-browser Telegram Login flow.

---

## 📊 Monitoring Pipeline — Full Architecture

> Documented 2026-04-22 after debugging session that fixed the "all sites blocked" issue.

### How `/api/check` Requests Flow

```
Browser (freenet.monster)
  │
  │  GET /api/check?url=<site>&use_vpn=<bool>
  ▼
Hetzner server.py   ← IS_MOSCOW_NODE=false (proxy mode)
  │
  │  Proxies ALL checks to Moscow node
  │  GET http://94.159.117.222:8090/api/check?url=<site>&use_vpn=<bool>
  ▼
Moscow server.py    ← IS_MOSCOW_NODE=true (execution mode)
  │
  ├─── use_vpn=false ──► Direct Russian ISP connection
  │                       (shows what's genuinely blocked in Russia)
  │
  └─── use_vpn=true ───► SOCKS5 proxy at 127.0.0.1:1081
                            │
                            ▼
                         Xray client (xray.service)
                         /usr/local/etc/xray/config.json
                            │  Shadowsocks tunnel
                            ▼
                         Hetzner port 1080 (Marzban Shadowsocks TCP inbound)
                            │
                            ▼
                         Target site (exits from Hetzner/Germany)
                         (shows what's accessible via FreeNet VPN)
```

### How `/api/status` (Batch Results) Flow

```
Moscow RKNMonitorThread  (runs every 5 min)
  │  Checks priority domains + random sample
  │  Stores in CHECK_RESULTS['moscow']['results']
  │
  ├─► POSTs to https://freenet.monster/api/update   (MASTER_URL env var)
  │   → Hetzner merges into its CHECK_RESULTS['moscow']
  │
  └─► Also available locally at http://94.159.117.222:8090/api/status

Browser fetchs /api/status on page load
  → updateGridFromStatus() reads CHECK_RESULTS['moscow']['results']
  → If data present: updates all badge statuses and EXITS EARLY
    (no individual /api/check calls are made for the main grid)
  → Individual /api/check calls only happen for the latency graph
```

---

## 🖥 Service Inventory

### Hetzner (`178.104.135.156`)

| Service | Process | Port | Notes |
|---------|---------|------|-------|
| Nginx (reverse proxy) | `nginx` | 80, 443 | SSL termination, WebSocket proxy |
| Marzban (via Docker) | `xray` in Docker | host network | Panel at `vpn.freenet.monster/dashboard` |
| Marzban API | `python` | 127.0.0.1:8080 | Internal only |
| Xray (Marzban's) | `xray` pid≈833092 | 1080, 127.0.0.1:13904 | Shadowsocks TCP + gRPC API |
| FreeNet Monitor | `python3` | 0.0.0.0:8090 | `/var/www/monitor/server.py` |
| Stripe Webhook | `/webhook/stripe` | 8090 | Auto-activates Marzban users |

### Moscow (`94.159.117.222`)

| Service | Process | Port | Notes |
|---------|---------|------|-------|
| FreeNet Monitor | `python3` | 0.0.0.0:8090 | `/var/www/monitor/server.py` |
| Xray VPN Client | `xray` (xray.service) | 127.0.0.1:1081 | SOCKS5 → Shadowsocks to Hetzner:1080 |

### Moscow Environment (`/var/www/monitor/.env`)
```
MASTER_URL=https://freenet.monster
IS_MOSCOW_NODE=true
```

### Hetzner Systemd Service
```
/etc/systemd/system/freenet-monitor.service
WorkingDirectory=/var/www/monitor
ExecStart=/usr/bin/python3 /var/www/monitor/server.py
Environment=STRIPE_SECRET_KEY=sk_...
Environment=STRIPE_WEBHOOK_SECRET=whsec_...
```

### Moscow Systemd Service
```
/etc/systemd/system/freenet-monitor.service
WorkingDirectory=/var/www/monitor
ExecStart=/usr/bin/python3 /var/www/monitor/server.py
EnvironmentFile=-/var/www/monitor/.env
```

### Moscow Xray VPN Client Config
```
/usr/local/etc/xray/config.json   (managed by xray.service)
```
Protocol: **Shadowsocks** (NOT VLESS REALITY — see gotchas below)
- Inbound: SOCKS5 on `127.0.0.1:1081`
- Outbound: Shadowsocks → `178.104.135.156:1080`
- User: `test_monitor` (Marzban)
- Method: `chacha20-ietf-poly1305`

---

## ⚠️ Key Gotchas (Lessons Learned)

### 1. VLESS REALITY Port 2053 Is NOT Externally Accessible
Despite being in `xray_config.json` (the Marzban template), **port 2053 is never bound to the host**. Marzban's runtime Xray config only exposes the inbounds it tracks internally. The only externally-accessible Xray inbound is:
- **Shadowsocks TCP on port 1080** (`Shadowsocks TCP` tag in Marzban)

> The `xray_config.json` / `xray_config_final.json` files in `/var/www/monitor/` are **server-side templates**, NOT client connection configs.

### 2. Marzban Inbound Registration vs. Xray Config
Marzban tracks inbounds separately from the raw Xray config:
- `GET /api/inbounds` is the source of truth for what Marzban actually manages
- VLESS inbounds in `xray_config.json` may not appear in `/api/inbounds` if not registered
- Assigning inbounds to users requires using the **Marzban-registered inbound tag names**, not the Xray tag names

### 3. CHECK_RESULTS Must Be a Dict, Not a List
`server.py` initializes `CHECK_RESULTS = {}` (dict). It must always stay a dict:
```python
CHECK_RESULTS['moscow'] = {
    "timestamp": <float>,
    "results": {"https://site.com": "up"|"down", ...}
}
```
Treating it as a list (e.g., `CHECK_RESULTS.append(...)`) causes a silent `AttributeError` and freezes results at the initial placeholder state.

### 4. Frontend Exits Early if /api/status Returns Data
`updateGridFromStatus()` returns `true` when the status API has any data, causing `startChecks()` to skip individual `/api/check` calls. This means:
- The main grid always reflects batch results from Moscow (updated every 5 min)
- Individual `/api/check` calls only happen for the latency graph overlay

### 5. Deployment: Two Servers, Two Roles
Always deploy `server.py` to **both** servers — they run the same file but behave differently based on `IS_MOSCOW_NODE`:
```bash
# Deploy to Hetzner
rsync -avz monitor/server.py vpn:/var/www/monitor/
ssh vpn "systemctl restart freenet-monitor"

# Deploy to Moscow
rsync -avz monitor/server.py aliowka@94.159.117.222:/home/aliowka/workspace/monitor/
ssh root@94.159.117.222 "systemctl restart freenet-monitor"
```

### 6. Marzban test_monitor User
- **Username**: `test_monitor`
- **Purpose**: Used by the Moscow Xray client to route VPN monitoring checks through Marzban
- **Inbound**: `Shadowsocks TCP` (assigned via Marzban admin API)
- **Subscription**: `https://vpn.freenet.monster/sub/dGVzdF9tb25pdG9yLDE3NzY4ODM4NjkuCzSyAODzn`
- **Admin creds**: `aliowka` / `VpnAdmin123!` at `http://127.0.0.1:8080` (Hetzner internal)
