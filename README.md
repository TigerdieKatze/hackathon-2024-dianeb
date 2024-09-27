# Project Overview

This project is a Python-based bot that interacts with a game server to participate in guessing games. It uses socket.io for communication with the server and includes logic for making strategic guesses based on previous game data.

## Prerequisites

- Docker
- Python 3.9

## Setup and Configuration

1. **Clone the repository**

   Clone the project repository to your local environment:
   ```bash
   git clone https://github.com/TigerdieKatze/hackathon2024
   cd hackathon2024
   ```

2. **Install dependencies**

   If running locally, install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configuration**

   You need to create a `config.json` file with the following structure:
   ```json
   {
       "SECRET": "<YOUR_SECRET>",
       "LOG_LEVEL": "INFO"
   }
   ```
   - Replace `<YOUR_SECRET>` with the authentication token for connecting to the game server.

4. **File System Setup**

   Ensure that the necessary directories are created:
   - `data/`: Stores the wordlist and result logs.
   - `config/`: Contains configuration files like `config.json`.

## Running the Bot Locally

1. Start the bot by running the following command:
   ```bash
   python main.py
   ```

## Docker Deployment

1. **Build the Docker image**

   To run the bot in a Docker container, build the Docker image:
   ```bash
   docker build -t bot .
   ```

2. **Run the bot with Docker Compose**

   You can run the bot using Docker Compose. Ensure the `docker-compose.yml` file is set up correctly:
   ```yaml
   services:
     bot:
       build: .
       volumes:
         - ./data:/app/data
         - ./config:/app/config
       restart: unless-stopped
   ```

   Then start the service:
   ```bash
   docker-compose up
   ```

## Logging

Logs are written to `data/logs/bot.log`. The log level is configurable via the `config.json` file under the `LOG_LEVEL` key. Available levels are `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL`.