from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import docker
import asyncio
import os
import json
import time
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from github import Github
import redis
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Development Playground API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "default_password")
print("Loaded AUTH_PASSWORD:", AUTH_PASSWORD)

# Initialize MongoDB client
mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
mongo_client = AsyncIOMotorClient(mongodb_url)
db = mongo_client.ai_playground

# Initialize Docker client
def init_docker_client():
    """Initialize Docker client with comprehensive debugging"""
    try:
        print("=== DOCKER CLIENT INITIALIZATION DEBUG ===")
        print("DOCKER_HOST:", os.environ.get("DOCKER_HOST"))
        print("DOCKER_API_VERSION:", os.environ.get("DOCKER_API_VERSION"))
        print("DOCKER_TLS_VERIFY:", os.environ.get("DOCKER_TLS_VERIFY"))
        print("DOCKER_CERT_PATH:", os.environ.get("DOCKER_CERT_PATH"))
        
        # Check socket paths
        sock_paths = ["/var/run/docker.sock", "/run/docker.sock"]
        for sock_path in sock_paths:
            exists = os.path.exists(sock_path)
            print(f"Checking {sock_path} exists: {exists}")
            if exists:
                try:
                    # Check if socket is accessible
                    stat = os.stat(sock_path)
                    print(f"  Socket mode: {oct(stat.st_mode)}")
                    print(f"  Socket owner: {stat.st_uid}")
                except Exception as e:
                    print(f"  Error checking socket: {e}")
        
        # Try different initialization methods
        client = None
        
        # Method 1: Try explicit unix socket
        print("\n--- Method 1: Explicit unix socket ---")
        try:
            client = docker.DockerClient(base_url='unix:///var/run/docker.sock')
            print("✓ Success with unix:///var/run/docker.sock")
            return client
        except Exception as e:
            print(f"✗ Failed with unix:///var/run/docker.sock: {e}")
        
        # Method 2: Try alternative socket path
        print("\n--- Method 2: Alternative socket path ---")
        try:
            client = docker.DockerClient(base_url='unix:///run/docker.sock')
            print("✓ Success with unix:///run/docker.sock")
            return client
        except Exception as e:
            print(f"✗ Failed with unix:///run/docker.sock: {e}")
        
        # Method 3: Try from_env() with explicit socket
        print("\n--- Method 3: from_env with socket ---")
        try:
            # Temporarily set DOCKER_HOST to unix socket
            old_docker_host = os.environ.get("DOCKER_HOST")
            os.environ["DOCKER_HOST"] = "unix:///var/run/docker.sock"
            client = docker.from_env()
            print("✓ Success with from_env() and DOCKER_HOST=unix:///var/run/docker.sock")
            # Restore original DOCKER_HOST
            if old_docker_host:
                os.environ["DOCKER_HOST"] = old_docker_host
            else:
                os.environ.pop("DOCKER_HOST", None)
            return client
        except Exception as e:
            print(f"✗ Failed with from_env() and DOCKER_HOST: {e}")
            # Restore original DOCKER_HOST
            if old_docker_host:
                os.environ["DOCKER_HOST"] = old_docker_host
            else:
                os.environ.pop("DOCKER_HOST", None)
        
        # Method 4: Try from_env() without any DOCKER_HOST
        print("\n--- Method 4: from_env() without DOCKER_HOST ---")
        try:
            # Ensure DOCKER_HOST is not set
            os.environ.pop("DOCKER_HOST", None)
            client = docker.from_env()
            print("✓ Success with from_env() without DOCKER_HOST")
            return client
        except Exception as e:
            print(f"✗ Failed with from_env() without DOCKER_HOST: {e}")
        
        # Method 5: Try with requests_unixsocket explicitly
        print("\n--- Method 5: Check requests_unixsocket ---")
        try:
            import requests_unixsocket
            print("✓ requests_unixsocket imported successfully")
            
            # Try to get version, but don't fail if it doesn't exist
            try:
                version = getattr(requests_unixsocket, '__version__', 'unknown')
                print(f"✓ requests_unixsocket version: {version}")
            except:
                print("✓ requests_unixsocket version: unknown (no __version__ attribute)")
            
            print("✓ requests_unixsocket is available")
            
            # Try again with explicit unix socket
            client = docker.DockerClient(base_url='unix:///var/run/docker.sock')
            print("✓ Success with requests_unixsocket and unix socket")
            return client
        except ImportError as e:
            print(f"✗ requests_unixsocket not available: {e}")
        except Exception as e:
            print(f"✗ Failed with requests_unixsocket: {e}")
            print(f"  Error type: {type(e).__name__}")
            print(f"  Error details: {str(e)}")
        
        # Method 6: Try with requests and unix socket adapter directly
        print("\n--- Method 6: Direct requests with unix socket ---")
        try:
            import requests_unixsocket
            import requests
            
            # Create a session with unix socket adapter
            session = requests_unixsocket.Session()
            
            # Test the connection directly
            response = session.get('http+unix://%2Fvar%2Frun%2Fdocker.sock/version')
            print(f"✓ Direct socket test successful: {response.status_code}")
            
            # If direct test works, try Docker client again
            client = docker.DockerClient(base_url='unix:///var/run/docker.sock')
            print("✓ Success with direct socket test and Docker client")
            return client
        except ImportError as e:
            print(f"✗ requests_unixsocket not available for direct test: {e}")
        except Exception as e:
            print(f"✗ Failed with direct socket test: {e}")
            print(f"  Error type: {type(e).__name__}")
            print(f"  Error details: {str(e)}")
        
        # Method 7: Try with lower-level APIClient
        print("\n--- Method 7: Lower-level APIClient ---")
        try:
            from docker import APIClient
            
            client = APIClient(base_url='unix:///var/run/docker.sock')
            # Test the connection
            version = client.version()
            print(f"✓ APIClient test successful: {version.get('ApiVersion', 'unknown')}")
            
            # Convert to DockerClient for compatibility
            from docker import DockerClient
            docker_client = DockerClient(base_url='unix:///var/run/docker.sock')
            print("✓ Success with APIClient and converted to DockerClient")
            return docker_client
        except Exception as e:
            print(f"✗ Failed with APIClient: {e}")
            print(f"  Error type: {type(e).__name__}")
            print(f"  Error details: {str(e)}")
        
        print("\n=== ALL METHODS FAILED ===")
        return None
        
    except Exception as e:
        logger.error(f"Failed to initialize Docker client: {e}")
        return None

# Initialize Docker client
docker_client = init_docker_client()
if docker_client:
    try:
        # Test the client
        version = docker_client.version()
        print(f"✓ Docker client test successful! API version: {version.get('ApiVersion', 'unknown')}")
    except Exception as e:
        print(f"✗ Docker client test failed: {e}")
        docker_client = None
else:
    print("✗ Docker client initialization failed completely")

# Initialize Redis for session management
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)

# Initialize GitHub client
github_token = os.getenv("GITHUB_TOKEN")
github_username = os.getenv("GITHUB_USERNAME")
github_client = Github(github_token) if github_token else None

# Pydantic models
class AppInfo(BaseModel):
    name: str
    description: str
    repository: str
    port: int
    status: str = "stopped"
    last_accessed: Optional[datetime] = None

class DeployRequest(BaseModel):
    app_name: str
    repository: str
    port: int = 8000

class AuthRequest(BaseModel):
    password: str

class DeploymentHistory(BaseModel):
    app_name: str
    repository: str
    container_id: str
    host_port: int
    started_at: datetime
    stopped_at: Optional[datetime] = None
    status: str

# Authentication
def verify_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != AUTH_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    return credentials.credentials

# MongoDB operations
async def save_deployment_history(deployment_data: Dict[str, Any]):
    """Save deployment history to MongoDB"""
    try:
        await db.deployments.insert_one(deployment_data)
    except Exception as e:
        logger.error(f"Failed to save deployment history: {e}")

async def update_deployment_stop(app_name: str, stopped_at: datetime):
    """Update deployment record when app is stopped"""
    try:
        await db.deployments.update_one(
            {"app_name": app_name, "stopped_at": None},
            {"$set": {"stopped_at": stopped_at, "status": "stopped"}}
        )
    except Exception as e:
        logger.error(f"Failed to update deployment stop: {e}")

# Renamed to avoid conflict with route
async def fetch_deployment_history(limit: int = 10):
    """Get recent deployment history"""
    try:
        cursor = db.deployments.find().sort("started_at", -1).limit(limit)
        deployments = await cursor.to_list(length=limit)
        return deployments
    except Exception as e:
        logger.error(f"Failed to get deployment history: {e}")
        return []

# Container management
class ContainerManager:
    def __init__(self):
        self.client = docker_client
        self.active_containers = {}
        self.container_info = {}
    
    async def deploy_app(self, app_name: str, repository: str, port: int) -> Dict[str, Any]:
        """Deploy an application from GitHub repository"""
        try:
            # Generate unique container name
            container_name = f"ai-playground-{app_name}-{int(time.time())}"
            
            # Pull and run the container
            container = self.client.containers.run(
                image=f"{repository}:latest",
                name=container_name,
                ports={f'{port}/tcp': None},  # Let Docker assign a random port
                detach=True,
                environment={
                    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
                    "NODE_ENV": "production"
                },
                mem_limit="512m",  # Limit memory usage
                cpu_period=100000,
                cpu_quota=50000,  # Limit CPU usage
                restart_policy={"Name": "no"}
            )
            
            # Get the assigned port
            container.reload()
            host_port = container.ports[f'{port}/tcp'][0]['HostPort']
            
            # Store container info
            self.active_containers[app_name] = {
                "container_id": container.id,
                "container_name": container_name,
                "host_port": host_port,
                "started_at": datetime.now(),
                "last_accessed": datetime.now()
            }
            
            # Save to MongoDB
            deployment_data = {
                "app_name": app_name,
                "repository": repository,
                "container_id": container.id,
                "host_port": host_port,
                "started_at": datetime.now(),
                "status": "running"
            }
            await save_deployment_history(deployment_data)
            
            logger.info(f"Deployed {app_name} on port {host_port}")
            
            return {
                "status": "success",
                "app_name": app_name,
                "url": f"http://localhost:{host_port}",
                "container_id": container.id
            }
            
        except Exception as e:
            logger.error(f"Failed to deploy {app_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")
    
    async def stop_app(self, app_name: str) -> Dict[str, Any]:
        """Stop and remove an application container"""
        try:
            if app_name not in self.active_containers:
                raise HTTPException(status_code=404, detail="App not found")
            
            container_info = self.active_containers[app_name]
            container = self.client.containers.get(container_info["container_id"])
            
            container.stop(timeout=10)
            container.remove()
            
            # Update MongoDB
            await update_deployment_stop(app_name, datetime.now())
            
            del self.active_containers[app_name]
            
            logger.info(f"Stopped and removed {app_name}")
            
            return {"status": "success", "message": f"{app_name} stopped successfully"}
            
        except Exception as e:
            logger.error(f"Failed to stop {app_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Stop failed: {str(e)}")
    
    async def get_app_status(self, app_name: str) -> Dict[str, Any]:
        """Get the status of an application"""
        if app_name in self.active_containers:
            container_info = self.active_containers[app_name]
            try:
                container = self.client.containers.get(container_info["container_id"])
                return {
                    "status": "running",
                    "url": f"http://localhost:{container_info['host_port']}",
                    "started_at": container_info["started_at"],
                    "last_accessed": container_info["last_accessed"]
                }
            except:
                # Container not found, remove from active list
                del self.active_containers[app_name]
                return {"status": "stopped"}
        
        return {"status": "stopped"}
    
    async def update_last_accessed(self, app_name: str):
        """Update the last accessed time for an app"""
        if app_name in self.active_containers:
            self.active_containers[app_name]["last_accessed"] = datetime.now()
    
    async def cleanup_inactive_containers(self):
        """Clean up containers that have been inactive for 15 minutes"""
        current_time = datetime.now()
        inactive_apps = []
        
        for app_name, info in self.active_containers.items():
            time_diff = current_time - info["last_accessed"]
            if time_diff > timedelta(minutes=15):
                inactive_apps.append(app_name)
        
        for app_name in inactive_apps:
            await self.stop_app(app_name)
            logger.info(f"Auto-stopped inactive app: {app_name}")

# Initialize container manager
container_manager = ContainerManager()

# Background task for cleanup
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(cleanup_task())

async def cleanup_task():
    """Background task to clean up inactive containers"""
    while True:
        await asyncio.sleep(60)  # Check every minute
        await container_manager.cleanup_inactive_containers()

# API Routes
@app.post("/auth")
async def authenticate(auth_request: AuthRequest):
    """Simple password authentication"""
    if auth_request.password == AUTH_PASSWORD:
        return {"status": "success", "message": "Authentication successful"}
    else:
        raise HTTPException(status_code=401, detail="Invalid password")

@app.get("/apps", dependencies=[Depends(verify_auth)])
async def get_apps():
    """Get list of available applications from GitHub"""
    if not github_client:
        return {"apps": []}
    
    try:
        user = github_client.get_user()
        repos = user.get_repos()
        
        apps = []
        for repo in repos:
            # Check if repo has dockerfile or docker-compose
            try:
                contents = repo.get_contents("")
                has_docker = any(
                    content.name.lower() in ["dockerfile", "docker-compose.yml", "docker-compose.yaml"]
                    for content in contents
                )
                
                if has_docker:
                    apps.append({
                        "name": repo.name,
                        "description": repo.description or "No description",
                        "repository": repo.full_name,
                        "url": repo.html_url,
                        "language": repo.language,
                        "stars": repo.stargazers_count
                    })
            except:
                continue
        
        return {"apps": apps}
    
    except Exception as e:
        logger.error(f"Failed to fetch GitHub repos: {e}")
        return {"apps": []}

@app.post("/deploy", dependencies=[Depends(verify_auth)])
async def deploy_app(deploy_request: DeployRequest):
    """Deploy an application"""
    if not docker_client:
        raise HTTPException(status_code=500, detail="Docker not available")
    
    # Check if app is already running
    status = await container_manager.get_app_status(deploy_request.app_name)
    if status["status"] == "running":
        return {"status": "already_running", "url": status["url"]}
    
    # Deploy the app
    result = await container_manager.deploy_app(
        deploy_request.app_name,
        deploy_request.repository,
        deploy_request.port
    )
    
    return result

@app.post("/stop/{app_name}", dependencies=[Depends(verify_auth)])
async def stop_app(app_name: str):
    """Stop an application"""
    result = await container_manager.stop_app(app_name)
    return result

@app.get("/status/{app_name}", dependencies=[Depends(verify_auth)])
async def get_app_status(app_name: str):
    """Get the status of an application"""
    # Update last accessed time
    await container_manager.update_last_accessed(app_name)
    
    status = await container_manager.get_app_status(app_name)
    return status

@app.get("/active", dependencies=[Depends(verify_auth)])
async def get_active_apps():
    """Get list of currently active applications"""
    active_apps = []
    for app_name in container_manager.active_containers.keys():
        status = await container_manager.get_app_status(app_name)
        active_apps.append({
            "name": app_name,
            **status
        })
    
    return {"active_apps": active_apps}

@app.get("/history", dependencies=[Depends(verify_auth)])
async def get_deployment_history():
    """Get deployment history"""
    history = await fetch_deployment_history(limit=20)
    return {"deployments": history}

@app.get("/health")
async def health_check():
    """Health check endpoint with detailed Docker debugging"""
    docker_status = {
        "available": docker_client is not None,
        "socket_paths": {},
        "environment": {},
        "client_test": "not_tested"
    }
    
    # Check socket paths
    sock_paths = ["/var/run/docker.sock", "/run/docker.sock"]
    for sock_path in sock_paths:
        exists = os.path.exists(sock_path)
        docker_status["socket_paths"][sock_path] = {
            "exists": exists,
            "accessible": False,
            "mode": None,
            "owner": None
        }
        if exists:
            try:
                stat = os.stat(sock_path)
                docker_status["socket_paths"][sock_path]["accessible"] = True
                docker_status["socket_paths"][sock_path]["mode"] = oct(stat.st_mode)
                docker_status["socket_paths"][sock_path]["owner"] = stat.st_uid
            except Exception as e:
                docker_status["socket_paths"][sock_path]["error"] = str(e)
    
    # Check environment variables
    docker_status["environment"] = {
        "DOCKER_HOST": os.environ.get("DOCKER_HOST"),
        "DOCKER_API_VERSION": os.environ.get("DOCKER_API_VERSION"),
        "DOCKER_TLS_VERIFY": os.environ.get("DOCKER_TLS_VERIFY"),
        "DOCKER_CERT_PATH": os.environ.get("DOCKER_CERT_PATH")
    }
    
    # Test Docker client if available
    if docker_client:
        try:
            version = docker_client.version()
            docker_status["client_test"] = "success"
            docker_status["api_version"] = version.get("ApiVersion", "unknown")
            docker_status["docker_version"] = version.get("Version", "unknown")
        except Exception as e:
            docker_status["client_test"] = f"failed: {str(e)}"
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "docker": docker_status,
        "github_available": github_client is not None,
        "mongodb_available": mongo_client is not None,
        "redis_available": redis_client is not None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 