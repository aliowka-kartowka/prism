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
    *   **Честный Мониторинг Dashboard**: The primary monitoring interface.
    *   **Moscow Mirror**: Proxies `http://94.159.117.222/sub/` requests directly to the back-end, bypassing domain-level blocks (SNI/DNS).
    *   **Dual-Path API**: Tests site accessibility via both Direct (RU ISP) and FreeNet (VPN) paths.
    *   **Robust Monitoring**: `check_url` logic now verifies the `Server: cloudflare` header to detect and report ISP splash-page interception.

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

## 🎁 Trial System
*   **In-Dashboard Activation**: Users click "GET FREE TRIAL" and log in via the **Telegram Login Widget** directly on the site.
*   **Provisioning**: Once authorized, the dashboard immediately displays VLESS links, QR codes, and Sing-box config URLs.
*   **Limits**: 10GB for 24 hours. Renewable daily to ensure continuous access for potential subscribers.

---

## 🧭 Troubleshooting

1.  **Hetzner IP Blocked**: Instruct users to switch to the **FreeNet CDN** link or use the **Sing-box Automatic** config which includes both paths.
2.  **DNS Failures**: The Sing-box config uses a dual-DNS strategy: `1.1.1.1` (via VPN) for global sites and `8.8.8.8` (Direct) for Russian domains to avoid corruption.
3.  **Bot Redirect Errors**: The old bot-redirect flow has been deprecated in favor of the in-browser Telegram Login flow.
