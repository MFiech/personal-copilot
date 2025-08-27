# Docker Setup for PM Co-Pilot Backend

This guide helps you run the PM Co-Pilot backend using Docker Desktop, making it much easier to start/stop the application and view logs.

## Prerequisites

1. **Docker Desktop** - Make sure Docker Desktop is installed and running
2. **Environment Variables** - Create a `.env` file in the project root with your API keys

## Quick Start

### 1. Environment Setup ✅

**Great news!** Your `.env` file has been automatically created with your existing API keys from `backend/.env`. The database configuration has been updated to work with Docker (`host.docker.internal:27017`).

If you need to modify any settings, edit the `.env` file in the project root directory.

### 2. Start Your Backend

**🖱️ Option 1: Using Docker Desktop UI (Recommended)**

1. Open **Docker Desktop**
2. Go to **Images** tab → Build the image first:
   ```bash
   docker-compose build pm-copilot-backend
   ```
3. Go to **Containers** tab
4. You'll see `pm-copilot-backend` - click the **▶️ Start** button
5. Click on the container name to view **real-time logs**

**⌨️ Option 2: Using Command Line**

```bash
# Start the backend service
docker-compose up pm-copilot-backend

# Or run in detached mode (background)  
docker-compose up -d pm-copilot-backend

# View logs
docker-compose logs -f pm-copilot-backend

# Stop the service
docker-compose down
```

### 3. Access Your Application

- **Backend API**: http://localhost:5001
- **Health Check**: http://localhost:5001/health
- **Docker Desktop**: View logs, restart, and manage containers through the Docker Desktop interface

## Development Workflow

### Hot Reload

The Docker setup includes volume mounting, so your code changes will be reflected immediately without rebuilding the container.

### Viewing Logs

**Through Docker Desktop:**
1. Open Docker Desktop
2. Go to **Containers** tab
3. Click on `pm-copilot-backend`
4. View real-time logs in the **Logs** tab
5. Use the **🔍 search** and **⬇️ download** features for log management

**Through Command Line:**
```bash
# Follow logs in real-time
docker-compose logs -f pm-copilot-backend

# View last 100 lines
docker-compose logs --tail=100 pm-copilot-backend
```

### Building and Rebuilding

```bash
# Rebuild the container after dependency changes
docker-compose build pm-copilot-backend

# Force rebuild (no cache)
docker-compose build --no-cache pm-copilot-backend

# Rebuild and start
docker-compose up --build pm-copilot-backend
```

## Database Configuration

### Option 1: Use Existing Local MongoDB
If you have MongoDB running locally, use:
```
MONGO_URI=mongodb://host.docker.internal:27017
```

### Option 2: Use MongoDB in Docker
Uncomment the MongoDB service in `docker-compose.yml` and use:
```
MONGO_URI=mongodb://mongodb:27017
```

## Troubleshooting

### Container Won't Start
1. Check that all required environment variables are set in `.env`
2. Ensure MongoDB is accessible (try the health check endpoint)
3. Check Docker Desktop logs for specific error messages

### Can't Connect to MongoDB
- If using local MongoDB: Ensure it's running and accessible
- Use `host.docker.internal` instead of `localhost` in `MONGO_URI`
- Check MongoDB logs for connection issues

### Port Already in Use
```bash
# Check what's using port 5001
lsof -i :5001

# Kill the process if needed
kill -9 <PID>
```

### Reset Everything
```bash
# Stop and remove containers, networks, and volumes
docker-compose down -v

# Remove the backend image
docker rmi pm-copilot/backend:latest

# Rebuild from scratch
docker-compose up --build pm-copilot-backend
```

## Benefits of This Setup

1. **Easy Start/Stop**: Use Docker Desktop interface or simple commands
2. **Log Management**: Centralized, searchable logs through Docker Desktop
3. **Isolation**: No conflicts with other Python environments
4. **Consistency**: Same environment across different machines
5. **Quick Reset**: Easy to reset to clean state
6. **Hot Reload**: Code changes reflected immediately during development

## Next Steps

- Add frontend service to `docker-compose.yml` for full-stack development
- Set up CI/CD pipeline using these Docker configurations
- Add production-ready configurations for deployment
