<p align="center">
  <img src="https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white" alt="Django"/>
  <img src="https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram"/>
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Leaflet-199900?style=for-the-badge&logo=leaflet&logoColor=white" alt="Leaflet"/>
</p>

<h1 align="center">🚑 CivicHero</h1>

<p align="center">
  <strong>Emergency Medical Dispatch System</strong><br>
  Connecting 103 dispatchers with nearby volunteer doctors via Telegram
</p>

<p align="center">
  <img src="https://img.shields.io/badge/status-MVP-orange?style=flat-square" alt="Status: MVP"/>
  <img src="https://img.shields.io/badge/version-1.0.0-blue?style=flat-square" alt="Version"/>
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License"/>
</p>

---



░█████╗░██╗██╗░░░██╗██╗░█████╗░██╗░░██╗███████╗██████╗░░█████╗░
██╔══██╗██║██║░░░██║██║██╔══██╗██║░░██║██╔════╝██╔══██╗██╔══██╗
██║░░╚═╝██║╚██╗░██╔╝██║██║░░╚═╝███████║█████╗░░██████╔╝██║░░██║
██║░░██╗██║░╚████╔╝░██║██║░░██╗██╔══██║██╔══╝░░██╔══██╗██║░░██║
╚█████╔╝██║░░╚██╔╝░░██║╚█████╔╝██║░░██║███████╗██║░░██║╚█████╔╝
░╚════╝░╚═╝░░░╚═╝░░░╚═╝░╚════╝░╚═╝░░╚═╝╚══════╝╚═╝░░╚═╝░╚════╝░




## 🎯 About

**CivicHero** is a platform that enables emergency service dispatchers (103) to instantly notify volunteer doctors about urgent calls. Doctors near the patient receive a Telegram notification and can accept the call with a single tap.

### The Problem
Ambulances can't always arrive on time due to traffic congestion and high demand.

### The Solution  
A network of volunteer doctors with a mobile app (Telegram bot) who can provide first aid before the ambulance arrives.

---

## ⚡ Key Features

### 🖥️ For Dispatchers

| Feature | Description |
|---------|-------------|
| 🗺️ Interactive Map | Live map with all active calls and doctor locations |
| 📝 Quick Call Creation | Create emergency calls in seconds |
| 🚦 Threat Levels | Prioritize calls: low → medium → high → critical |
| 👁️ Real-time Tracking | Monitor call status as it progresses |
| 👨‍⚕️ Doctor Monitoring | See all online doctors and their locations |

### 📱 For Doctors

| Feature | Description |
|---------|-------------|
| 📱 Telegram Bot | Simple, familiar interface — no app download needed |
| 📍 Geolocation | Automatic distance calculation to patient |
| ✅ One-tap Response | Accept or decline calls instantly |
| ⏱️ Time Tracking | Travel time and on-site duration timers |
| 🚑 Ambulance Backup | Request emergency backup with one button |
| 📊 Statistics | Track your completed calls and performance |

---

## 🏗️ Architecture

```
┌─────────────────────┐         ┌─────────────────────┐
│   Django Web App    │◄───────►│   Telegram Bot      │
│   (Dispatchers)     │  HTTP   │   (Doctors)         │
│                     │         │                     │
│  • Dashboard        │         │  • aiogram 3.x      │
│  • REST API         │         │  • FSM states       │
│  • Leaflet Maps     │         │  • Inline keyboards │
└─────────┬───────────┘         └──────────┬──────────┘
          │                                │
          └────────────┬───────────────────┘
                       │
              ┌────────▼────────┐
              │    SQLite DB    │
              │                 │
              │  • Doctors      │
              │  • Calls        │
              │  • Responses    │
              └─────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Django 5.x
- Telegram Bot Token

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/civichero.git
cd civichero

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
pip install django asgiref requests

# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser
```

### Running the Application

**Terminal 1 — Django server:**
```bash
python manage.py runserver
```

**Terminal 2 — Telegram bot:**
```bash
python telegram_bot.py
```

📍 Web Dashboard: `http://localhost:8000/`  
🤖 Telegram Bot: Find the bot on Telegram and send `/start`

---

## 📱 Usage

### For Doctors (Telegram)

```
/start      — Start / Main menu
/register   — Register as a new doctor
/test_call  — Create a test call (for development)
```

**Workflow:**
1. 📝 Register via `/register`
2. 🟢 Tap "Online" to start receiving calls
3. 📍 Share your location for distance calculation
4. 🚨 When a call comes in — accept or decline
5. 📍 Upon arrival — tap "I'm on site"
6. ✅ After helping — complete the call with a photo report

### For Dispatchers (Web Dashboard)

1. Open the dispatcher dashboard
2. Click "Create Call"
3. Fill in patient details
4. Click on the map to set location
5. Click "Send to CivicHero"
6. Doctors receive instant notifications!

---

## 📊 Data Models

### Doctor
| Field | Type | Description |
|-------|------|-------------|
| `telegram_id` | BigInt | Unique Telegram ID |
| `first_name`, `last_name` | String | Doctor's full name |
| `phone` | String | Contact phone number |
| `is_online` | Boolean | Availability status |
| `latitude`, `longitude` | Float | Last known location |

### Call
| Field | Type | Description |
|-------|------|-------------|
| `patient_name`, `patient_age` | String/Int | Patient details |
| `illness_description` | Text | Problem description |
| `address` | Text | Call address |
| `threat_level` | Enum | `low` / `medium` / `high` / `critical` |
| `status` | Enum | `created` → `sent_to_doctors` → `accepted` → `on_site` → `completed` |
| `assigned_doctor` | FK | Assigned doctor |

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Dispatcher dashboard with map |
| `GET` | `/api/calls/` | List all calls |
| `POST` | `/api/calls/create/` | Create a new call |
| `POST` | `/api/calls/{id}/assign/` | Send call to doctors |
| `GET` | `/api/doctors/online/` | List online doctors |

**Internal Bot API (port 8001):**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/notify_call` | Notify doctors about a call |
| `GET` | `/health` | Bot health check |

---

## 🛠️ Tech Stack

- **Backend:** Django 5.x, Python 3.11+
- **Bot:** aiogram 3.x (async), aiohttp
- **Database:** SQLite (MVP) → PostgreSQL (prod)
- **Frontend:** Vanilla JS, Leaflet.js
- **Maps:** OpenStreetMap

---

## 📁 Project Structure

```
civichero/
├── config/                 # Django configuration
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── dispatcher/             # Dispatcher application
│   ├── models.py          # Doctor, Call, CallResponse
│   ├── views.py           # API & Dashboard views
│   ├── admin.py           # Admin panel config
│   └── templates/
│       └── dispatcher/
│           └── dashboard.html
├── telegram_bot.py         # Telegram bot for doctors
├── bot_config.py          # Bot configuration
├── requirements.txt
├── manage.py
└── db.sqlite3
```

---

## 🔮 Roadmap

- [ ] 🔐 Dispatcher authentication
- [ ] 📈 Advanced analytics & dashboards  
- [ ] 🗄️ PostgreSQL migration
- [ ] 🔔 Firebase push notifications
- [ ] 📱 Progressive Web App for dispatchers
- [ ] 🌐 Multi-language support (Uzbek, Russian)
- [ ] 🏥 Hospital & clinic integrations

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---
TG BOT: @civicherobot

<p align="center">
  <strong>🇺🇿 Made in Tashkent with ❤️</strong><br>
  <sub>CivicHero — because every second counts</sub>
</p>
