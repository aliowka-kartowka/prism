# FreeNet VPN — INFRASTRUCTURE & ARCHITECTURE

FreeNet Monster (Честный Мониторинг) is a high-resilience VPN platform and censorship monitor designed specifically for the Russian market.

## 🏗 System Architecture

The infrastructure is split into two main geographic regions (Germany and Russia) to balance high-speed global connectivity with local monitoring capabilities.

### 1. Hetzner Hub (Germany / Global Exit)
The primary management hub and VPN exit point.
*   **Host**: `178.104.135.156` (Hetzner)
*   **Core Services**:
    *   **Marzban**: Xray management panel handling users, subscriptions, and protocols.
    *   **Nginx Reverse Proxy**: Handles SSL termination and protects the backend services. Now configured for **WebSocket proxying** on port 443 to support Cloudflare CDN.
    *   **Cloudflare Proxy**: `vpn.freenet.monster` is proxied via Cloudflare ("Orange Cloud") to mask the Hetzner IP.
    *   **Cloudflare WARP**: Local SOCKS5 proxy (`127.0.0.1:40000`) for "clean" IP exits (e.g., for ChatGPT).

### 2. Moscow Monitoring Node (Russia)
A dedicated node within Russia to perform real-time censorship and connectivity checks.
*   **Host**: `94.159.117.222`
*   **Functionality**:
    *   **Честный Мониторинг Dashboard**: The primary monitoring interface.
    *   **Dual-Path API**: Tests site accessibility via both Direct (RU ISP) and FreeNet (VPN) paths.
    *   **Российские сайты Monitoring**: A specialized list of Russian services (Sber, VK, Gosuslugi) monitored to ensure they bypass the VPN.
    *   **TG Proxy**: Local SOCKS5 proxy on port `1081` to bypass Telegram API blocks.

### 3. Telegram Bot (@FreeNetMonsterBot)
The primary user gateway for trial generation and subscription management.

---

## 🛰 Connectivity Strategies

To ensure maximum resilience against Roskomnadzor (RKN), the platform provides two distinct connection paths:

### 🚀 FreeNet Direct (VLESS REALITY)
*   **Transport**: TCP
*   **Port**: 2053
*   **Best for**: Maximum performance and low latency.
*   **Mechanism**: Uses VLESS REALITY to camouflage as standard HTTPS traffic to `yandex.ru`.

### 🛡️ FreeNet CDN (VLESS WebSocket + Cloudflare)
*   **Transport**: WebSocket (WS)
*   **Port**: 443
*   **Best for**: High-resilience bypass if the main server IP is flagged.
*   **Mechanism**: Traffic is routed through **Cloudflare's edge network**. RKN sees traffic to Cloudflare, not the Hetzner server.

---

## 🛠 Project Components

*   `monitor/`: The main premium monitoring dashboard.
*   `monitor/server.py`: The backend logic for the Moscow node, including VLESS link mapping and label generation.
*   `russia_monitor/`: Lightweight monitoring view.
*   `nginx_vpn.conf`: Configuration files for the Nginx gateway on the Hetzner server.

---

## 🎁 Trial System
*   **10GB / 1 Day**: Automatically provisioned via the dashboard.
*   **Anti-Abuse**: ID-based tracking via Telegram Login Widget.
*   **Renewal**: Accessible every 24 hours to ensure continuous service for trial users.

---

## 🧭 Troubleshooting

1.  **Hetzner IP Blocked**: If `FreeNet Direct` fails, instruct users to switch to the **FreeNet CDN** link.
2.  **CDN Link Failure**: Verify that Nginx on Hetzner is correctly proxying `/vpn-ws` to the local Xray WS inbound on port 2054.
3.  **Russian Sites Slow**: Ensure split-tunneling is active or sites are manually bypassed; Russian state sites (Gosuslugi) may block foreign IP ranges.
