# FreeNet VPN Infrastructure & Architecture

Welcome to the FreeNet VPN project. This document provides a high-level overview of our current infrastructure, servers, and services for new developers and agents.

## 🏗 System Architecture

The infrastructure is split into two main geographic regions to provide both stability and local monitoring capabilities.

### 1. Hetzner Hub (Germany/Global)
The primary management hub and entry point for users.

*   **Host**: `178.104.135.156` (Hetzner)
*   **Access**: `ssh -i ~/.ssh/hetzner_vpn aliowka@178.104.135.156`
*   **Core Services**:
    *   **Marzban**: An Xray management panel that handles user accounts, subscription links, and inbound/outbound rules for the VPN.
    *   **Cloudflare WARP**: Installed as a local SOCKS5 proxy (`127.0.0.1:40000`) to provide "clean" IP exits for services that block datacenter ranges (like ChatGPT).
    *   **Nginx Reverse Proxy**: Handles SSL termination and routes traffic to internal services and the Moscow node.
    *   **Docker Stack**: Orchestrated via `docker-compose-vpn.yml`.

### 2. Moscow Monitoring Node (Russia)
A dedicated node located within Russia to perform real-time connectivity checks.

*   **Host**: `94.159.117.222`
*   **Access**: `ssh root@94.159.117.222`
*   **Functionality**:
    *   **Thematic Monitoring Dashboard**: Fully localized Russian dashboard with 5 unique visual skins (Classic, Cyberpanda, Glitch, Ghost, Banana) and a persistent theme switcher.
    *   **Connectivity Monitor**: Runs a Python/HTML dashboard that tests site accessibility.
    *   **Native Sharing**: Mini App includes a "Поделиться" button for viral Telegram sharing.
    *   **Proxy Support**: Bot uses a local SOCKS5 proxy (`1081`) in Moscow to bypass Telegram API blocks.
    *   **Dual-Path Testing**: Every site is checked twice (Direct vs FreeNet).

### 3. Telegram Bot (@FreeNetMonsterBot)
The primary user interface for subscription management.

*   **Role**: Handles automated user onboarding and billing.
*   **Inline Mode**: Specifically optimized for sharing status cards in groups and channels. Type `@FreeNetMonsterBot` in any chat to use.
*   **Localization**: Fully localized in Russian (messages, commands, buttons).
*   **Payments**: Integrated with **Telegram CryptoBot** to support TON and other cryptocurrencies.
*   **Management**: Automated syncing with Marzban to create/renew accounts upon payment or trial request.

---

## 🔐 Configuration & Secrets

*   **Environment Variables**: Stored in `.env` files (e.g., `moscow_monitor_env.txt`). These contain Marzban admin credentials and Telegram bot tokens.
*   **Whitelisting**: `allowed_list.txt` defines which domains the monitoring node is permitted to scan.

---

## 🛰 Routing & Content Unblocking

### ChatGPT / OpenAI Bypass
Since OpenAI filters common datacenter IP ranges (including Hetzner), we use a specialized routing strategy:
1.  **Outbound Proxy**: A system-level Cloudflare WARP service runs in SOCKS5 mode.
2.  **Smart Routing**: Xray is configured to identify requests to `openai.com`, `chatgpt.com`, and related domains.
3.  **Diversion**: These specific requests are diverted to the WARP client, while all other traffic exits through the standard Hetzner IP for maximum performance.

---

## 🛠 Project Components

*   `monitor/`: The main premium monitoring dashboard (Dark Mode, multi-theme system).
*   `monitor/deploy_node.sh`: A "One-Click" automated script to deploy new Xray/Reality nodes on any fresh Ubuntu server.
*   `russia_monitor/`: A lightweight version of the monitor.
*   `free_vpn/`: A Flutter-based mobile application project for Android/iOS users.
*   `nginx_vpn.conf`: Configuration for the Nginx gateway on the Hetzner server.

---

## 🎁 Trial System

We offer a **10GB 1-day trial** to new users.
*   **Trigger**: Can be requested directly from the monitoring dashboard.
*   **Validation**: Uses Telegram Login Widget to prevent abuse (checked via API in the backend).
*   **Reset**: The system allows for renewal every 24 hours if the trial is exhausted.

---

## 🧭 Troubleshooting for Agents

1.  **ChatGPT is not working**: Ensure `warp-cli status` shows "Connected" on the Hetzner node. If not, run `sudo warp-cli connect`.
2.  **Monitor is "Down"**: Check the Python service on the Moscow server. It typically runs on port `8090` via `monitor/server.py`.
3.  **VPN Connection Failure**: Check the Marzban panel status on the Hetzner server and ensure the Xray core is running.
4.  **Bad Content Blocking**: Check `xray_config.json` on the Hetzner node to verify the `WARP` outbound is active and the routing rules are correct.
5.  **Bot Conflict (409 Error)**: This occurs if multiple instances use the same token. Ensure only the Moscow node is running the bot polling. If persistent, revoke the token in BotFather.
6.  **Bot Connection in RU**: Ensure `TELEGRAM_PROXY` is set in the Moscow node's `.env` to bypass API blocks.
