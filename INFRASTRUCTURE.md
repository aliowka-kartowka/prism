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
    *   **Nginx Reverse Proxy**: Handles SSL termination and routes traffic to internal services and the Moscow node.
    *   **Docker Stack**: Orchestrated via `docker-compose-vpn.yml`.

### 2. Moscow Monitoring Node (Russia)
A dedicated node located within Russia to perform real-time connectivity checks.

*   **Host**: `94.159.117.222`
*   **Access**: `ssh root@94.159.117.222`
*   **Functionality**:
    *   **Connectivity Monitor**: Runs a Python/HTML dashboard that tests site accessibility.
    *   **Russian Localization**: Dashboard and Bot content fully localized for RU users.
    *   **Native Sharing**: Mini App includes a "Поделиться" button for viral Telegram sharing.
    *   **Proxy Support**: Bot uses a local SOCKS5 proxy (`1081`) in Moscow to bypass Telegram API blocks.
    *   **Dual-Path Testing**: Every site is checked twice:
        1.  **Direct**: Testing if the site is reachable from a Russian IP without a VPN.
        2.  **FreeNet**: Testing if the site is reachable through an Xray tunnel (SOCKS5 proxy to the Hetzner node).
    *   **API**: Serves endpoints like `/api/check` for real-time status updates and `/api/trial` for trial generation.

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

## 🛠 Project Components

*   `monitor/`: The main premium monitoring dashboard (Dark Mode, Chart.js integrations).
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

1.  **Monitor is "Down"**: Check the Python service on the Moscow server. It typically runs on port `8090` via `monitor/server.py`.
2.  **VPN Connection Failure**: Check the Marzban panel status on the Hetzner server and ensure the Xray core is running.
3.  **Bot Conflict (409 Error)**: This occurs if multiple instances use the same token. Ensure only the Moscow node is running the bot polling. If persistent, revoke the token in BotFather.
4.  **Bot Connection in RU**: Ensure `TELEGRAM_PROXY` is set in the Moscow node's `.env` to bypass API blocks.
