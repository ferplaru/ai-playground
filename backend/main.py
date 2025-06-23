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
import subprocess

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Development Playground API", version="1.0.0")

# CORS middleware
frontend_origin = os.getenv("FRONTEND_ORIGIN")
if not frontend_origin:
    frontend_origin = "http://91.99.196.35:3000"
    print(f"[CORS] FRONTEND_ORIGIN not set, using default: {frontend_origin}")
else:
    print(f"[CORS] Using FRONTEND_ORIGIN from env: {frontend_origin}")

# Fallback to '*' if still not set
if not frontend_origin:
    frontend_origin = "*"
    print("[CORS] WARNING: No frontend origin set, using '*'")

print(f"[CORS] Final allow_origins: {frontend_origin}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
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
    """Initialize Docker client using CLI approach instead of Python SDK"""
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
        
        # Test Docker CLI directly
        print("\n--- Testing Docker CLI ---")
        try:
            import subprocess
            import json
            
            # First test if docker command works at all
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print(f"✓ Docker CLI available: {result.stdout.strip()}")
            else:
                print(f"✗ Docker CLI not available: {result.stderr}")
                return None
            
            # Test docker version with JSON format
            result = subprocess.run(['docker', 'version', '--format', 'json'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                try:
                    version_info = json.loads(result.stdout)
                    print(f"✓ Docker CLI test successful!")
                    print(f"  Docker version: {version_info.get('Server', {}).get('Version', 'unknown')}")
                    print(f"  API version: {version_info.get('Server', {}).get('ApiVersion', 'unknown')}")
                    
                    # Return a CLI-based client wrapper
                    return DockerCLIClient()
                except json.JSONDecodeError as e:
                    print(f"✗ Docker version returned invalid JSON: {result.stdout}")
                    print(f"  JSON error: {e}")
                    
                    # Try without JSON format as fallback
                    result = subprocess.run(['docker', 'version'], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        print(f"✓ Docker CLI works (non-JSON format): {result.stdout[:100]}...")
                        return DockerCLIClient()
                    else:
                        print(f"✗ Docker version failed: {result.stderr}")
                        return None
            else:
                print(f"✗ Docker version failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            print("✗ Docker CLI test timed out")
            return None
        except Exception as e:
            print(f"✗ Docker CLI test failed: {e}")
            return None
        
    except Exception as e:
        logger.error(f"Failed to initialize Docker client: {e}")
        return None

class DockerCLIClient:
    """Docker client that uses CLI commands instead of Python SDK"""
    
    def __init__(self):
        self.docker_cmd = ['docker']
    
    def version(self):
        """Get Docker version information"""
        try:
            # Try JSON format first
            result = subprocess.run(self.docker_cmd + ['version', '--format', 'json'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    pass  # Fall back to non-JSON format
            
            # Fallback to non-JSON format
            result = subprocess.run(self.docker_cmd + ['version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Parse the text output manually
                lines = result.stdout.strip().split('\n')
                version_info = {'Client': {}, 'Server': {}}
                
                current_section = None
                for line in lines:
                    if line.startswith('Client:'):
                        current_section = 'Client'
                    elif line.startswith('Server:'):
                        current_section = 'Server'
                    elif ':' in line and current_section:
                        key, value = line.split(':', 1)
                        version_info[current_section][key.strip()] = value.strip()
                
                return version_info
            else:
                raise Exception(f"Docker version failed: {result.stderr}")
        except Exception as e:
            raise Exception(f"Failed to get Docker version: {e}")
    
    def containers(self):
        """Return a containers manager"""
        return ContainerManagerCLI(self.docker_cmd)
    
    def images(self):
        """Return an images manager"""
        return ImageManagerCLI(self.docker_cmd)

class ContainerManagerCLI:
    """Container manager using CLI commands"""
    
    def __init__(self, docker_cmd):
        self.docker_cmd = docker_cmd
    
    def run(self, image, name=None, ports=None, detach=False, environment=None, 
            mem_limit=None, cpu_period=None, cpu_quota=None, restart_policy=None):
        """Run a container using CLI"""
        try:
            cmd = self.docker_cmd + ['run']
            
            if name:
                cmd.extend(['--name', name])
            
            if ports:
                for port_mapping in ports.items():
                    container_port = port_mapping[0]
                    host_port = port_mapping[1]
                    if host_port is None:
                        cmd.extend(['-p', container_port])
                    else:
                        cmd.extend(['-p', f"{host_port}:{container_port}"])
            
            if detach:
                cmd.append('-d')
            
            if environment:
                for key, value in environment.items():
                    cmd.extend(['-e', f"{key}={value}"])
            
            if mem_limit:
                cmd.extend(['--memory', mem_limit])
            
            if cpu_period and cpu_quota:
                cmd.extend(['--cpu-period', str(cpu_period), '--cpu-quota', str(cpu_quota)])
            
            if restart_policy:
                cmd.extend(['--restart', restart_policy['Name']])
            
            cmd.append(image)
            
            print(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                container_id = result.stdout.strip()
                return ContainerCLI(self.docker_cmd, container_id)
            else:
                raise Exception(f"Failed to run container: {result.stderr}")
                
        except Exception as e:
            raise Exception(f"Failed to run container: {e}")
    
    def get(self, container_id):
        """Get a container by ID"""
        return ContainerCLI(self.docker_cmd, container_id)
    
    def list(self, all=False):
        """List containers"""
        try:
            # Try JSON format first
            cmd = self.docker_cmd + ['ps']
            if all:
                cmd.append('-a')
            cmd.extend(['--format', 'json'])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                try:
                    containers = []
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            containers.append(json.loads(line))
                    return containers
                except json.JSONDecodeError:
                    pass  # Fall back to non-JSON format
            
            # Fallback to non-JSON format
            cmd = self.docker_cmd + ['ps']
            if all:
                cmd.append('-a')
            cmd.extend(['--format', 'table {{.ID}}\t{{.Image}}\t{{.Command}}\t{{.CreatedAt}}\t{{.Status}}\t{{.Ports}}\t{{.Names}}'])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                containers = []
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                for line in lines:
                    if line.strip():
                        parts = line.split('\t')
                        if len(parts) >= 7:
                            containers.append({
                                'Id': parts[0],
                                'Image': parts[1],
                                'Command': parts[2],
                                'CreatedAt': parts[3],
                                'Status': parts[4],
                                'Ports': parts[5],
                                'Names': parts[6]
                            })
                return containers
            else:
                raise Exception(f"Failed to list containers: {result.stderr}")
                
        except Exception as e:
            raise Exception(f"Failed to list containers: {e}")

class ContainerCLI:
    """Container wrapper using CLI commands"""
    
    def __init__(self, docker_cmd, container_id):
        self.docker_cmd = docker_cmd
        self.id = container_id
    
    def reload(self):
        """Reload container information"""
        # No-op for CLI version, info is fetched on demand
        pass
    
    def stop(self, timeout=10):
        """Stop the container"""
        try:
            cmd = self.docker_cmd + ['stop', '--time', str(timeout), self.id]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
            
            if result.returncode != 0:
                raise Exception(f"Failed to stop container: {result.stderr}")
                
        except Exception as e:
            raise Exception(f"Failed to stop container: {e}")
    
    def remove(self):
        """Remove the container"""
        try:
            cmd = self.docker_cmd + ['rm', self.id]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                raise Exception(f"Failed to remove container: {result.stderr}")
                
        except Exception as e:
            raise Exception(f"Failed to remove container: {e}")
    
    @property
    def ports(self):
        """Get container port mappings"""
        try:
            cmd = self.docker_cmd + ['port', self.id]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            print(f"[DockerCLI] docker port output: {result.stdout}")
            if result.returncode == 0:
                ports = {}
                for line in result.stdout.strip().split('\n'):
                    if line:
                        # Example: 8000/tcp -> 0.0.0.0:49153
                        parts = line.split(' -> ')
                        if len(parts) == 2:
                            container_port = parts[0]
                            host_mapping = parts[1]
                            if ':' in host_mapping:
                                host_ip, host_port = host_mapping.rsplit(':', 1)
                                ports[container_port] = [{
                                    'HostPort': host_port,
                                    'HostIp': host_ip
                                }]
                            else:
                                ports[container_port] = [{
                                    'HostPort': '',
                                    'HostIp': host_mapping
                                }]
                print(f"[DockerCLI] Parsed ports: {ports}")
                return ports
            else:
                print(f"[DockerCLI] Failed to get ports: {result.stderr}")
                return {}
                
        except Exception as e:
            print(f"Failed to get container ports: {e}")
            return {}

class ImageManagerCLI:
    """Image manager using CLI commands"""
    
    def __init__(self, docker_cmd):
        self.docker_cmd = docker_cmd
    
    def pull(self, image):
        """Pull an image"""
        try:
            cmd = self.docker_cmd + ['pull', image]
            print(f"Running pull command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                raise Exception(f"Failed to pull image: {result.stderr}")
            else:
                print(f"✓ Successfully pulled image: {image}")
                
        except Exception as e:
            print(f"✗ Failed to pull image: {e}")
            raise Exception(f"Failed to pull image {image}: {e}")

# Initialize Docker client
docker_client = init_docker_client()
if docker_client:
    try:
        # Test the client
        version = docker_client.version()
        print(f"✓ Docker client test successful! API version: {version.get('Server', {}).get('ApiVersion', 'unknown')}")
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

class BuildRequest(BaseModel):
    app_name: str
    repository: str

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

# Fix MongoDB ObjectId serialization
print('[DEBUG] fix_mongo_obj loaded')
def fix_mongo_obj(obj):
    obj = dict(obj)
    if "_id" in obj:
        obj["_id"] = str(obj["_id"])
    print(f"[Mongo] Fixed object: {obj}")
    return obj

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
            print(f"=== DEPLOYING APP: {app_name} ===")
            print(f"Repository: {repository}")
            print(f"Port: {port}")
            print(f"Client type: {type(self.client)}")
            
            # Generate unique container name
            container_name = f"ai-playground-{app_name}-{int(time.time())}"
            print(f"Container name: {container_name}")
            
            # Determine if we need to build the image or pull it
            image_name = f"{repository}:latest"
            
            # Check if it's a public image or needs building
            if "/" in repository and not repository.startswith("localhost/"):
                # Try to pull first, if it fails, build from GitHub
                try:
                    print(f"Attempting to pull public image: {image_name}")
                    await self._pull_image(image_name)
                except Exception as e:
                    print(f"Pull failed, building from GitHub: {e}")
                    image_name = await self._build_from_github(repository, app_name)
            else:
                # Local image, try to pull
                await self._pull_image(image_name)
            
            # Debug: Check if client has containers attribute
            print(f"Client has containers attribute: {hasattr(self.client, 'containers')}")
            if hasattr(self.client, 'containers'):
                print(f"Containers attribute type: {type(self.client.containers)}")
                if callable(self.client.containers):
                    print("Containers is callable, calling it...")
                    containers_manager = self.client.containers()
                    print(f"Containers manager type: {type(containers_manager)}")
                else:
                    print("Containers is not callable, using directly...")
                    containers_manager = self.client.containers
                    print(f"Containers manager type: {type(containers_manager)}")
            else:
                print("Client does not have containers attribute!")
                raise Exception("Docker client does not have containers manager")
            
            # Run the container
            print(f"Running container with image: {image_name}")
            try:
                container = containers_manager.run(
                    image=image_name,
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
                print(f"✓ Container started successfully")
                print(f"Container type: {type(container)}")
                print(f"Container ID: {container.id}")
            except Exception as e:
                print(f"✗ Failed to run container: {e}")
                raise Exception(f"Failed to run container: {e}")
            
            # Get the assigned port
            print("Getting container port mapping...")
            try:
                container.reload()
                ports = container.ports
                print(f"Container ports: {ports}")
                # Find the first non-empty host port
                host_port = ''
                for port_key, port_list in ports.items():
                    if port_list and port_list[0]['HostPort']:
                        host_port = port_list[0]['HostPort']
                        break
                print(f"Assigned host port: {host_port}")
            except Exception as e:
                print(f"✗ Failed to get container ports: {e}")
                raise Exception(f"Failed to get container port mapping: {e}")
            
            # Store container info
            self.active_containers[app_name] = {
                "container_id": container.id,
                "container_name": container_name,
                "host_port": host_port,
                "started_at": datetime.now(),
                "last_accessed": datetime.now()
            }
            print(f"✓ Stored container info for {app_name}")
            
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
            print(f"✓ Saved deployment history to MongoDB")
            
            # When constructing URLs for deployed apps, use the public host
            PUBLIC_HOST = os.getenv("PUBLIC_HOST", "91.99.196.35")
            print(f"[URL] PUBLIC_HOST is: {PUBLIC_HOST}")
            url = f"http://{PUBLIC_HOST}:{host_port}"
            print(f"[URL] Constructed app URL: {url}")
            
            logger.info(f"Deployed {app_name} on port {host_port}")
            
            return {
                "status": "success",
                "app_name": app_name,
                "url": url,
                "container_id": container.id
            }
            
        except Exception as e:
            logger.error(f"Failed to deploy {app_name}: {e}")
            print(f"✗ Deployment failed for {app_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")
    
    async def _pull_image(self, image_name: str):
        """Pull a Docker image"""
        print(f"Pulling image: {image_name}")
        try:
            # Debug: Check if client has images attribute
            print(f"Client has images attribute: {hasattr(self.client, 'images')}")
            if hasattr(self.client, 'images'):
                print(f"Images attribute type: {type(self.client.images)}")
                if callable(self.client.images):
                    print("Images is callable, calling it...")
                    images_manager = self.client.images()
                    print(f"Images manager type: {type(images_manager)}")
                else:
                    print("Images is not callable, using directly...")
                    images_manager = self.client.images
                    print(f"Images manager type: {type(images_manager)}")
            else:
                print("Client does not have images attribute!")
                raise Exception("Docker client does not have images manager")
            
            images_manager.pull(image_name)
            print(f"✓ Successfully pulled image: {image_name}")
        except Exception as e:
            print(f"✗ Failed to pull image: {e}")
            raise Exception(f"Failed to pull image {image_name}: {e}")
    
    async def _build_from_github(self, repository: str, app_name: str) -> str:
        """Build Docker image from GitHub repository"""
        try:
            print(f"=== BUILDING IMAGE FROM GITHUB: {repository} ===")
            
            # Create a unique build context directory
            import tempfile
            import shutil
            
            build_dir = tempfile.mkdtemp(prefix=f"ai-playground-{app_name}-")
            print(f"Build directory: {build_dir}")
            
            # Clone the repository
            import subprocess
            
            clone_cmd = ['git', 'clone', f'https://github.com/{repository}.git', build_dir]
            print(f"Cloning repository: {' '.join(clone_cmd)}")
            
            result = subprocess.run(clone_cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                raise Exception(f"Failed to clone repository: {result.stderr}")
            
            print(f"✓ Repository cloned successfully")
            
            # Build the Docker image
            image_name = f"ai-playground-{app_name}:latest"
            build_cmd = ['docker', 'build', '-t', image_name, build_dir]
            print(f"Building image: {' '.join(build_cmd)}")
            
            result = subprocess.run(build_cmd, capture_output=True, text=True, timeout=600)
            if result.returncode != 0:
                raise Exception(f"Failed to build image: {result.stderr}")
            
            print(f"✓ Image built successfully: {image_name}")
            
            # Clean up build directory
            shutil.rmtree(build_dir)
            print(f"✓ Cleaned up build directory")
            
            return image_name
            
        except Exception as e:
            print(f"✗ Failed to build from GitHub: {e}")
            raise Exception(f"Failed to build image from GitHub {repository}: {e}")
    
    async def stop_app(self, app_name: str) -> Dict[str, Any]:
        """Stop and remove an application container"""
        try:
            print(f"=== STOPPING APP: {app_name} ===")
            
            if app_name not in self.active_containers:
                print(f"✗ App {app_name} not found in active containers")
                raise HTTPException(status_code=404, detail="App not found")
            
            container_info = self.active_containers[app_name]
            print(f"Container info: {container_info}")
            
            # Debug: Check if client has containers attribute
            print(f"Client has containers attribute: {hasattr(self.client, 'containers')}")
            if hasattr(self.client, 'containers'):
                print(f"Containers attribute type: {type(self.client.containers)}")
                if callable(self.client.containers):
                    print("Containers is callable, calling it...")
                    containers_manager = self.client.containers()
                    print(f"Containers manager type: {type(containers_manager)}")
                else:
                    print("Containers is not callable, using directly...")
                    containers_manager = self.client.containers
                    print(f"Containers manager type: {type(containers_manager)}")
            else:
                print("Client does not have containers attribute!")
                raise Exception("Docker client does not have containers manager")
            
            print(f"Getting container: {container_info['container_id']}")
            container = containers_manager.get(container_info["container_id"])
            print(f"Container type: {type(container)}")
            
            print("Stopping container...")
            container.stop(timeout=10)
            print("✓ Container stopped")
            
            print("Removing container...")
            container.remove()
            print("✓ Container removed")
            
            # Update MongoDB
            await update_deployment_stop(app_name, datetime.now())
            print("✓ Updated MongoDB deployment record")
            
            del self.active_containers[app_name]
            print(f"✓ Removed {app_name} from active containers")
            
            logger.info(f"Stopped and removed {app_name}")
            
            return {"status": "success", "message": f"{app_name} stopped successfully"}
            
        except Exception as e:
            logger.error(f"Failed to stop {app_name}: {e}")
            print(f"✗ Failed to stop {app_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Stop failed: {str(e)}")
    
    async def get_app_status(self, app_name: str) -> Dict[str, Any]:
        """Get the status of an application"""
        print(f"=== GETTING STATUS FOR: {app_name} ===")
        
        if app_name in self.active_containers:
            container_info = self.active_containers[app_name]
            print(f"Container info: {container_info}")
            
            try:
                # Debug: Check if client has containers attribute
                print(f"Client has containers attribute: {hasattr(self.client, 'containers')}")
                if hasattr(self.client, 'containers'):
                    print(f"Containers attribute type: {type(self.client.containers)}")
                    if callable(self.client.containers):
                        print("Containers is callable, calling it...")
                        containers_manager = self.client.containers()
                        print(f"Containers manager type: {type(containers_manager)}")
                    else:
                        print("Containers is not callable, using directly...")
                        containers_manager = self.client.containers
                        print(f"Containers manager type: {type(containers_manager)}")
                else:
                    print("Client does not have containers attribute!")
                    raise Exception("Docker client does not have containers manager")
                
                print(f"Getting container: {container_info['container_id']}")
                container = containers_manager.get(container_info["container_id"])
                print(f"Container type: {type(container)}")
                
                return {
                    "status": "running",
                    "url": f"http://localhost:{container_info['host_port']}",
                    "started_at": container_info["started_at"],
                    "last_accessed": container_info["last_accessed"]
                }
            except Exception as e:
                print(f"✗ Container not found, removing from active list: {e}")
                # Container not found, remove from active list
                del self.active_containers[app_name]
                return {"status": "stopped"}
        
        print(f"App {app_name} not in active containers, status: stopped")
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

@app.post("/build", dependencies=[Depends(verify_auth)])
async def build_image(build_request: BuildRequest):
    """Build a Docker image from GitHub repository"""
    if not docker_client:
        raise HTTPException(status_code=500, detail="Docker not available")
    
    try:
        # Build the image
        image_name = await container_manager._build_from_github(
            build_request.repository,
            build_request.app_name
        )
        
        return {
            "status": "success",
            "app_name": build_request.app_name,
            "repository": build_request.repository,
            "image_name": image_name,
            "message": f"Image {image_name} built successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to build image for {build_request.app_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Build failed: {str(e)}")

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

@app.get("/running", dependencies=[Depends(verify_auth)])
async def get_running_apps():
    """List all currently running containers started by this platform"""
    running = []
    for app_name, info in container_manager.active_containers.items():
        running.append({
            "app_name": app_name,
            "container_id": info["container_id"],
            "host_port": info["host_port"],
            "started_at": info["started_at"],
            "last_accessed": info["last_accessed"]
        })
    print(f"[Running] Active containers: {running}")
    return {"running": running}

@app.get("/history", dependencies=[Depends(verify_auth)])
async def get_deployment_history():
    history = await fetch_deployment_history(limit=20)
    # Fix ObjectId serialization
    history = [fix_mongo_obj(item) for item in history]
    # Add running apps
    running = []
    for app_name, info in container_manager.active_containers.items():
        running.append({
            "app_name": app_name,
            "container_id": info["container_id"],
            "host_port": info["host_port"],
            "started_at": info["started_at"],
            "last_accessed": info["last_accessed"]
        })
    print(f"[History] Active containers: {running}")
    return {"deployments": history, "running": running}

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
            docker_status["api_version"] = version.get("Server", {}).get("ApiVersion", "unknown")
            docker_status["docker_version"] = version.get("Server", {}).get("Version", "unknown")
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