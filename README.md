# MX-AutoInvoice

MX-AutoInvoice is a lightweight, self-hosted automation system designed to streamline the Mexican "autofacturacion" process. It leverages an **Email-First Strategy** to trigger native invoice dispatches from vendor portals, minimizing local storage and resource overhead.

## Features

- **Telegram Bot Interface:** Control the entire process via a simple Telegram chat.
- **Gemini OCR (Vision):** Uses Google Gemini 2.5 Flash to extract Folio, Total, Vendor, and vendor-specific ticket fields from ticket photos.
- **Email-First Strategy:** Prioritizes triggering "Send to Email" features on vendor portals.
- **Human-in-the-Loop:** Supports manual vendor selection, user confirmation, and fiscal-data mismatch decisions before automation continues.
- **Vendor Learning CLI:** Supports explore, dry-run, and live modes for Codex CLI + Playwright MCP learning workflows.
- **Submission History:** Persistent PostgreSQL-backed history tracking.
- **Dockerized:** Easy deployment with a minimal RAM footprint, optimized for low-resource servers like Dell Optiplex.

## Tech Stack

- **Orchestrator:** Python Telegram Bot
- **Intelligence:** Google Gemini 2.5 Flash API
- **Automation:** DrissionPage (resource-optimized headless browser)
- **Database:** PostgreSQL
- **Infrastructure:** Docker & Docker Compose

## Prerequisites

- Docker and Docker Compose
- A Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- A Google AI Studio API Key (from [aistudio.google.com](https://aistudio.google.com/))
- Access to a PostgreSQL database

## Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Anndres47/mx-autoinvoice.git
   cd mx-autoinvoice
   ```

2. **Configure Environment:**
   Copy `.env.example` to `.env` and fill in your details:
   ```bash
   cp .env.example .env
   ```

3. **Deployment:**
   ```bash
   docker-compose up -d --build
   ```

## Usage

1. Send `/start` to your bot.
2. Upload a clear photo of your retail ticket.
3. Confirm or select the vendor from the list.
4. Verify the extracted data and click **YES** to start automation.
5. If the portal has saved fiscal data that differs from `.env`, choose whether to replace it, keep it, or cancel.
6. Receive your invoice directly in your registered email.

## Vendor Learning

Use `vendor_cli.py` from a local learning environment to inspect or rehearse a vendor recipe before promoting it to the Docker bot:

```bash
python vendor_cli.py walmart --mode explore
python vendor_cli.py oxxo --mode dry-run --folio SAMPLE_FOLIO --total 123.45 --date 2026-01-31
python vendor_cli.py costco --mode dry-run --ticket-order SAMPLE_TICKET_ORDER --total 123.45
```

Keep real ticket data in `.env`, Telegram input, or ignored private fixtures only. `.env.example` must stay generic.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
