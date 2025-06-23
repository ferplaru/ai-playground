# Deployment Guide

This guide covers different deployment options for your AI Development Playground, from local development to production hosting.

## Quick Start (Local Development)

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd ai-development-playground
   ```

2. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

3. **Deploy using the script**
   ```bash
   ./scripts/deploy.sh
   ```

4. **Access the platform**
   - Dashboard: http://localhost:3000
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Cloud Deployment Options

### Option 1: Railway (Recommended - $5/month)

Railway is perfect for this use case with its generous free tier and easy Docker deployment.

1. **Create Railway account**
   - Go to [railway.app](https://railway.app)
   - Sign up with GitHub

2. **Deploy the project**
   ```bash
   # Install Railway CLI
   npm install -g @railway/cli
   
   # Login to Railway
   railway login
   
   # Deploy
   railway up
   ```

3. **Set environment variables**
   - Go to your Railway project dashboard
   - Add all variables from your `.env` file

4. **Configure custom domain** (optional)
   - Add your domain in Railway dashboard
   - Update DNS records

### Option 2: Render (Free tier available)

Render offers a free tier with some limitations.

1. **Create Render account**
   - Go to [render.com](https://render.com)
   - Sign up with GitHub

2. **Create new Web Service**
   - Connect your GitHub repository
   - Choose "Docker" as environment
   - Set build command: `docker-compose up --build`

3. **Configure environment variables**
   - Add all variables from your `.env` file

### Option 3: Fly.io (Generous free tier)

Fly.io offers 3 shared-cpu VMs and 3GB persistent volume storage for free.

1. **Install Fly CLI**
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Create fly.toml**
   ```bash
   fly launch
   ```

3. **Deploy**
   ```bash
   fly deploy
   ```

### Option 4: DigitalOcean App Platform ($5/month)

DigitalOcean provides reliable hosting with good performance.

1. **Create DigitalOcean account**
2. **Create new App**
   - Connect your GitHub repository
   - Choose "Docker" as source
   - Configure environment variables

## Production Considerations

### Security

1. **Use strong passwords**
   - Generate a secure password for `AUTH_PASSWORD`
   - Consider using a password manager

2. **HTTPS/SSL**
   - Most cloud providers offer automatic SSL
   - Configure redirects from HTTP to HTTPS

3. **Environment variables**
   - Never commit `.env` files to version control
   - Use secure environment variable management

### Performance

1. **Resource limits**
   - The platform already includes memory and CPU limits
   - Monitor usage and adjust as needed

2. **Auto-scaling**
   - Consider enabling auto-scaling for high traffic
   - Set appropriate minimum/maximum instances

3. **CDN**
   - Use a CDN for static assets
   - Consider Cloudflare for additional security

### Monitoring

1. **Health checks**
   - The platform includes health check endpoints
   - Configure monitoring for `/health` endpoints

2. **Logs**
   - Set up log aggregation (e.g., Papertrail, Loggly)
   - Monitor for errors and performance issues

3. **Metrics**
   - Track container usage and costs
   - Monitor API response times

## Cost Optimization

### Free Tier Strategies

1. **Railway Free Tier**
   - $5/month for 500 hours
   - Perfect for personal use

2. **Render Free Tier**
   - Free with limitations
   - Good for testing

3. **Fly.io Free Tier**
   - 3 shared-cpu VMs
   - 3GB persistent volume storage

### Cost Monitoring

1. **Set up billing alerts**
   - Most providers offer billing notifications
   - Set limits to prevent unexpected charges

2. **Resource optimization**
   - Use auto-shutdown features
   - Monitor and adjust resource limits

3. **Container management**
   - The platform automatically stops inactive containers
   - Manual cleanup for unused resources

## Troubleshooting

### Common Issues

1. **Docker not available**
   ```bash
   # Check Docker installation
   docker --version
   docker info
   ```

2. **Port conflicts**
   ```bash
   # Check what's using the ports
   lsof -i :3000
   lsof -i :8000
   ```

3. **Environment variables**
   ```bash
   # Verify .env file
   cat .env
   # Check if variables are loaded
   docker-compose config
   ```

### Debug Commands

```bash
# View logs
./scripts/deploy.sh logs

# Restart services
./scripts/deploy.sh restart

# Clean up everything
./scripts/deploy.sh cleanup

# Check service status
docker-compose ps

# Access container shell
docker-compose exec backend bash
```

## Next Steps

1. **Customize the platform**
   - Add your own AI applications
   - Customize the UI/UX
   - Add additional features

2. **Scale up**
   - Add more sophisticated monitoring
   - Implement user management
   - Add analytics and metrics

3. **Security enhancements**
   - Implement proper user authentication
   - Add rate limiting
   - Set up backup strategies

## Support

For issues and questions:
- Check the troubleshooting section
- Review the logs: `./scripts/deploy.sh logs`
- Open an issue in the repository 