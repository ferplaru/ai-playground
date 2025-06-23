# Quick Start Guide

Get your AI Development Playground running in 5 minutes!

## Prerequisites

- Docker and Docker Compose installed
- GitHub account with repositories containing Dockerfile/docker-compose files
- OpenAI API key (optional, for AI applications)

## Step 1: Setup

1. **Clone and navigate to the project**
   ```bash
   git clone <your-repo-url>
   cd ai-development-playground
   ```

2. **Create environment file**
   ```bash
   cp env.example .env
   ```

3. **Edit the environment file**
   ```bash
   # Open .env in your editor and set:
   AUTH_PASSWORD=your_secure_password
   GITHUB_TOKEN=your_github_token
   GITHUB_USERNAME=your_github_username
   OPENAI_API_KEY=your_openai_key  # Optional
   ```

## Step 2: Deploy

Run the deployment script:
```bash
./scripts/deploy.sh
```

This will:
- Check Docker installation
- Build and start all services
- Show you the access URLs

## Step 3: Access

- **Dashboard**: http://localhost:3000
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Step 4: Use

1. **Login** with your password
2. **Browse** your GitHub repositories with Docker support
3. **Deploy** any app with one click
4. **Test** your AI applications
5. **Stop** apps when done (auto-stops after 15 minutes of inactivity)

## Example AI Applications

The `examples/` folder contains sample applications you can deploy:

- **Simple Chatbot**: Basic OpenAI-powered chat interface
- **More coming soon...**

## Troubleshooting

### Common Issues

**"Docker not available"**
```bash
# Install Docker Desktop or Docker Engine
# Start Docker service
```

**"Port already in use"**
```bash
# Stop existing services
./scripts/deploy.sh stop
# Or change ports in docker-compose.yml
```

**"Authentication failed"**
```bash
# Check your .env file
# Ensure AUTH_PASSWORD is set correctly
```

### Useful Commands

```bash
# View logs
./scripts/deploy.sh logs

# Restart services
./scripts/deploy.sh restart

# Stop everything
./scripts/deploy.sh stop

# Clean up (removes all data)
./scripts/deploy.sh cleanup
```

## Next Steps

1. **Add your own AI applications** to GitHub with Dockerfile
2. **Deploy to cloud** (see `docs/DEPLOYMENT.md`)
3. **Customize the platform** for your needs
4. **Share with colleagues** (they can access with the same password)

## Support

- Check the logs: `./scripts/deploy.sh logs`
- Review the full documentation in `docs/`
- Open an issue if you encounter problems

---

**Happy AI Development! 🚀** 