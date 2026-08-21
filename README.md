# 🛒 E-Commerce Market Sniper & Monitoring Service

A high-performance, asynchronous Telegram bot engineered for real-time automated monitoring of clothing market listings. Built with Python and PostgreSQL to ensure rapid data extraction and persistent storage.

### 💼 Business Value
Tracking market deals manually is slow and inefficient, causing buyers and resellers to miss out on profitable opportunities. This bot acts as a real-time sniper, instantly detecting new listings and price drops, delivering them directly to the user's workflow.

### 🚀 Key Features
* **Real-time Monitoring:** Asynchronous architecture tracks market price fluctuations instantly.
* **Advanced Sniper Logic:** Automatically detects new deals, filtering out irrelevant noise.
* **Persistent Storage:** Utilizes PostgreSQL via asyncpg for secure, fast storage of user preferences and search history.
* **Production-Ready:** Fully containerized, optimized for 24/7 high-availability deployment.

### 🛠 Tech Stack
* **Core:** Python 3.12, aiogram 3.x (Asyncio)
* **Database:** PostgreSQL (SQLAlchemy + asyncpg)
* **Deployment:** Render (integrated with UptimeRobot for 24/7 reliability)

### 📋 Getting Started

1. Clone the repository: 
   ```bash
   git clone [https://github.com/yourusername/your-repo-name.git](https://github.com/yourusername/your-repo-name.git)
Install dependencies:

Bash
pip install -r requirements.txt
Configure your .env file:


BOT_TOKEN=your_token
ADMIN_ID=your_id
DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname
Run the application:

Bash
python main.py
