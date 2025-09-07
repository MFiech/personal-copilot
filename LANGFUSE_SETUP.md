# 🔗 Langfuse Integration Setup

This guide explains how to set up Langfuse integration for PM Co-Pilot, following the same pattern as the podcast-analyzer project.

## 🎯 Quick Setup

### 1. Run Langfuse Externally

Langfuse runs as an **external service** (not in Docker Compose), making it simple and reusable across projects.

#### Option A: Docker (Recommended)
```bash
# Run Langfuse with SQLite (simple setup)
docker run -d \
  --name langfuse \
  -p 4000:3000 \
  -e DATABASE_URL="file:./data/langfuse.db" \
  -v langfuse-data:/app/data \
  langfuse/langfuse:2
```

#### Option B: Docker with PostgreSQL (Production)
```bash
# Start PostgreSQL
docker run -d \
  --name langfuse-db \
  -e POSTGRES_USER=langfuse \
  -e POSTGRES_PASSWORD=langfuse \
  -e POSTGRES_DB=langfuse \
  -p 5432:5432 \
  postgres:15

# Start Langfuse
docker run -d \
  --name langfuse \
  -p 4000:3000 \
  -e DATABASE_URL="postgresql://langfuse:langfuse@host.docker.internal:5432/langfuse" \
  -e NEXTAUTH_SECRET="your-secret-key" \
  -e SALT="your-salt" \
  langfuse/langfuse:2
```

### 2. Configure Environment Variables

Add to your `.env` file:

```bash
# Langfuse Configuration
LANGFUSE_ENABLED=true
LANGFUSE_HOST=http://localhost:4000
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key
```

### 3. Set Up API Keys

1. Visit http://localhost:4000
2. Create an account
3. Go to **Settings → API Keys**
4. Create new keys and update your `.env` file

### 4. Initialize Prompts

```bash
cd backend
python scripts/setup_langfuse_prompts.py
```

## 🔧 How It Works

### Docker Integration
- **PM Co-Pilot Backend**: Runs in Docker
- **Langfuse**: Runs externally on host machine
- **Connection**: Uses `host.docker.internal:4000` for Docker → Host communication

### Automatic Host Detection
The service automatically detects the environment:
- **Local development**: `http://localhost:4000`
- **Docker container**: `http://host.docker.internal:4000`

### Graceful Degradation
If Langfuse is unavailable:
- ✅ App continues normally
- ✅ Falls back to hardcoded prompts
- ✅ No functionality is lost

## 🚀 Usage

Once configured, Langfuse automatically tracks:
- 📋 **Prompts**: Centralized prompt management
- 🔗 **Sessions**: Grouped conversations
- 📊 **Traces**: Detailed request/response logs
- 💰 **Costs**: Token usage and costs

Visit http://localhost:4000 to view your data!

## 🔍 Troubleshooting

### Connection Refused Errors
If you see connection errors in Docker logs:

1. **Check if Langfuse is running**:
   ```bash
   curl http://localhost:4000/api/public/health
   ```

2. **Disable Langfuse temporarily**:
   ```bash
   # Add to .env
   LANGFUSE_ENABLED=false
   ```

3. **Restart your backend**:
   ```bash
   docker-compose restart pm-copilot-backend
   ```

### Common Issues
- **Port conflicts**: Make sure port 4000 is available
- **Docker networking**: Ensure `host.docker.internal` is accessible
- **API keys**: Verify your keys are correctly set in `.env`

## 🎉 Success

When working correctly, you'll see:
```
✅ Langfuse service initialized successfully
```

And no more "Connection refused" errors in your Docker logs!
