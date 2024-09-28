# Project Overview

This project is a Python-based bot that interacts with a game server to participate in guessing games. It uses `socket.io` for communication with the server and includes logic for making strategic guesses based on previous game data.

## Prerequisites

- Docker
- Docker Compose

## Setup and Configuration

1. **Clone the repository**

   Clone the project repository to your local environment:
   ```bash
   git clone https://github.com/TigerdieKatze/hackathon2024
   cd hackathon2024
   ```

2. **Configuration**

   Create a `config.json` file with the following structure:
   ```json
   {
       "SECRET": "<YOUR_SECRET>",
       "LOG_LEVEL": "INFO"
   }
   ```
   - Replace `<YOUR_SECRET>` with the authentication token for connecting to the game server.

3. **File System Setup**

   Ensure that the necessary directories are created:
   - `data/`: Stores the wordlist and result logs.
   - `config/`: Contains configuration files like `config.json`.

## Docker Deployment

This project **must** be deployed via Docker.

### Building the Docker Images

1. **Bot Docker Image**

   To run the bot in a Docker container, build the Docker image by navigating to the `bot` directory:
   ```bash
   docker build -t your-bot-image-name ./bot/
   ```

2. **Dashboard Docker Image**

   To build the dashboard for the web interface, navigate to the `dashboard` directory and run:
   ```bash
   docker build -t your-dashboard-image-name ./dashboard/
   ```

### Running with Docker Compose

After building the images, run the following command to deploy both the bot and dashboard containers:

1. Ensure that your `docker-compose.yml` file is correctly set up:

   ```yaml
   services:
     bot:
       build: ./bot/
       volumes:
         - ./data:/app/data
         - ./config:/app/config
       #enviroment:
         #- THREADCOUNT=20
         #- BOT_SECRET=<Secret>
       restart: unless-stopped

     dashboard:
       build: ./dashboard/
       ports:
         - "127.0.0.1:3000:3000"
       restart: unless-stopped
   ```
- THREADCOUNT and BOT_SECRET are optional

2. Start the services:
   ```bash
   docker-compose up -d
   ```

### Accessing the Services

- The bot will be running in the background.
- The dashboard can be accessed via `http://localhost:3000`.

## Logging

Logs are written to `data/logs/bot.log`. The log level is configurable via the `config.json` file under the `LOG_LEVEL` key. Available levels are `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL`.

## Additional Docker Commands

- **To stop the services**:
  ```bash
  docker-compose down
  ```

- **To view logs**:
  ```bash
  docker-compose logs
  ```