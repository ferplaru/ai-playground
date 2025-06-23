# AI Development Playground

A personal platform for deploying and testing AI applications with cost-effective container management.

## Features

- 🔐 Simple password authentication
- 🚀 One-click app deployment from GitHub
- ⏰ Auto-shutdown after 15 minutes of inactivity
- 💰 Cost-effective hosting with automatic resource management
- 🐳 Docker container orchestration
- 📱 Responsive web dashboard
- 📊 Deployment history tracking with MongoDB

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │    │   Container     │
│   (Next.js)     │◄──►│   (FastAPI)     │◄──►│   Orchestrator  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
    ┌─────────┐            ┌─────────┐            ┌─────────┐
    │ Auth    │            │ GitHub  │            │ Docker  │
    │ (Simple)│            │ API     │            │ Engine  │
    └─────────┘            └─────────┘            └─────────┘
         │                       │                       │
         │                       │                       │
    ┌─────────┐            ┌─────────┐            ┌─────────┐
    │ Redis   │            │ MongoDB │            │ Nginx   │
    │ (Cache) │            │ (Data)  │            │ (Proxy) │
    └─────────┘            └─────────┘            └─────────┘
```

## Quick Start

1. Clone this repository
2. Set up environment variables (see `env.example`)
3. Run the deployment script:
   ```bash
   ./scripts/deploy.sh
   ```

## Project Structure

```
├── frontend/          # Next.js dashboard
├── backend/           # FastAPI server
├── docker/           # Docker configurations
├── scripts/          # Deployment scripts
├── examples/         # Sample AI applications
└── docs/             # Documentation
```

## Environment Variables

Create a `.env` file with:

```env
# Authentication
AUTH_PASSWORD=your_secure_password

# GitHub
GITHUB_TOKEN=your_github_token
GITHUB_USERNAME=your_username

# OpenAI API (for AI applications)
OPENAI_API_KEY=your_openai_api_key

# MongoDB
MONGODB_URL=mongodb://localhost:27017

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
```

## Deployment

The platform supports multiple deployment strategies:

1. **Local Development**: Docker Compose
2. **Cloud Deployment**: Railway/Render/Fly.io
3. **Self-hosted**: VPS with Docker

## Cost Optimization

- Auto-shutdown after 15 minutes of inactivity
- Resource limits on containers
- Free tier hosting options
- Efficient container management

## Security

- Simple password authentication
- Container isolation
- No persistent data storage
- Regular security updates

## Contributing

This is a personal project, but feel free to fork and adapt for your own needs. 