'use client'

import React, { useState, useEffect } from 'react'
import { Play, Square, ExternalLink, Github, Clock, Zap, History } from 'lucide-react'
import axios from 'axios'

interface App {
  name: string
  description: string
  repository: string
  url: string
  language: string
  stars: number
}

interface ActiveApp {
  name: string
  status: string
  url?: string
  started_at?: string
  last_accessed?: string
}

interface DeploymentHistory {
  _id: string
  app_name: string
  repository: string
  container_id: string
  host_port: number
  started_at: string
  stopped_at?: string
  status: string
}

export default function Dashboard() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [password, setPassword] = useState('')
  const [apps, setApps] = useState<App[]>([])
  const [activeApps, setActiveApps] = useState<ActiveApp[]>([])
  const [deploymentHistory, setDeploymentHistory] = useState<DeploymentHistory[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState<'apps' | 'history'>('apps')

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  useEffect(() => {
    // Check if already authenticated
    const token = localStorage.getItem('auth_token')
    if (token) {
      setIsAuthenticated(true)
      fetchApps()
      fetchActiveApps()
      fetchDeploymentHistory()
    }
  }, [])

  const authenticate = async () => {
    try {
      setLoading(true)
      setError('')
      
      const response = await axios.post(`${API_BASE}/auth`, {
        password: password
      })
      
      if (response.data.status === 'success') {
        localStorage.setItem('auth_token', password)
        setIsAuthenticated(true)
        fetchApps()
        fetchActiveApps()
        fetchDeploymentHistory()
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  const fetchApps = async () => {
    try {
      const token = localStorage.getItem('auth_token')
      const response = await axios.get(`${API_BASE}/apps`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setApps(response.data.apps || [])
    } catch (err) {
      console.error('Failed to fetch apps:', err)
    }
  }

  const fetchActiveApps = async () => {
    try {
      const token = localStorage.getItem('auth_token')
      const response = await axios.get(`${API_BASE}/active`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setActiveApps(response.data.active_apps || [])
    } catch (err) {
      console.error('Failed to fetch active apps:', err)
    }
  }

  const fetchDeploymentHistory = async () => {
    try {
      const token = localStorage.getItem('auth_token')
      const response = await axios.get(`${API_BASE}/history`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setDeploymentHistory(response.data.deployments || [])
    } catch (err) {
      console.error('Failed to fetch deployment history:', err)
    }
  }

  const deployApp = async (app: App) => {
    try {
      setLoading(true)
      const token = localStorage.getItem('auth_token')
      
      const response = await axios.post(`${API_BASE}/deploy`, {
        app_name: app.name,
        repository: app.repository,
        port: 8000
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })
      
      if (response.data.status === 'success') {
        fetchActiveApps()
        fetchDeploymentHistory()
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Deployment failed')
    } finally {
      setLoading(false)
    }
  }

  const stopApp = async (appName: string) => {
    try {
      setLoading(true)
      const token = localStorage.getItem('auth_token')
      
      await axios.post(`${API_BASE}/stop/${appName}`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      })
      
      fetchActiveApps()
      fetchDeploymentHistory()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to stop app')
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    localStorage.removeItem('auth_token')
    setIsAuthenticated(false)
    setApps([])
    setActiveApps([])
    setDeploymentHistory([])
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  const getDuration = (startedAt: string, stoppedAt?: string) => {
    const start = new Date(startedAt)
    const end = stoppedAt ? new Date(stoppedAt) : new Date()
    const diff = end.getTime() - start.getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(minutes / 60)
    const remainingMinutes = minutes % 60
    
    if (hours > 0) {
      return `${hours}h ${remainingMinutes}m`
    }
    return `${minutes}m`
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="card w-full max-w-md">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              AI Development Playground
            </h1>
            <p className="text-gray-600">
              Deploy and test your AI applications
            </p>
          </div>
          
          <form onSubmit={(e) => { e.preventDefault(); authenticate(); }}>
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="Enter your password"
                required
              />
            </div>
            
            {error && (
              <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg">
                {error}
              </div>
            )}
            
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full"
            >
              {loading ? 'Authenticating...' : 'Sign In'}
            </button>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center">
              <Zap className="h-8 w-8 text-primary-600 mr-3" />
              <h1 className="text-2xl font-bold text-gray-900">
                AI Development Playground
              </h1>
            </div>
            <button
              onClick={logout}
              className="btn-secondary"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Active Apps */}
        {activeApps.length > 0 && (
          <div className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Active Applications
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {activeApps.map((app) => (
                <div key={app.name} className="card">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-semibold text-gray-900">{app.name}</h3>
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      Running
                    </span>
                  </div>
                  
                  {app.url && (
                    <a
                      href={app.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center text-primary-600 hover:text-primary-700 mb-3"
                    >
                      <ExternalLink className="h-4 w-4 mr-1" />
                      Open App
                    </a>
                  )}
                  
                  <div className="flex space-x-2">
                    <button
                      onClick={() => stopApp(app.name)}
                      disabled={loading}
                      className="btn-secondary flex-1"
                    >
                      <Square className="h-4 w-4 mr-1" />
                      Stop
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="mb-6">
          <nav className="flex space-x-8">
            <button
              onClick={() => setActiveTab('apps')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'apps'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Available Apps
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'history'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <History className="h-4 w-4 inline mr-1" />
              Deployment History
            </button>
          </nav>
        </div>

        {/* Tab Content */}
        {activeTab === 'apps' && (
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Available Applications
            </h2>
            
            {error && (
              <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg">
                {error}
              </div>
            )}
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {apps.map((app) => (
                <div key={app.name} className="card">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="font-semibold text-gray-900">{app.name}</h3>
                      <p className="text-sm text-gray-600 mt-1">
                        {app.description}
                      </p>
                    </div>
                    <a
                      href={app.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-gray-400 hover:text-gray-600"
                    >
                      <Github className="h-5 w-5" />
                    </a>
                  </div>
                  
                  <div className="flex items-center justify-between mb-4">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                      {app.language}
                    </span>
                    <span className="text-sm text-gray-500">
                      ⭐ {app.stars}
                    </span>
                  </div>
                  
                  <button
                    onClick={() => deployApp(app)}
                    disabled={loading}
                    className="btn-primary w-full"
                  >
                    <Play className="h-4 w-4 mr-1" />
                    Deploy
                  </button>
                </div>
              ))}
            </div>
            
            {apps.length === 0 && (
              <div className="text-center py-12">
                <Clock className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500">
                  No applications found. Make sure your GitHub repositories have Dockerfile or docker-compose files.
                </p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'history' && (
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Deployment History
            </h2>
            
            <div className="bg-white shadow overflow-hidden sm:rounded-md">
              <ul className="divide-y divide-gray-200">
                {deploymentHistory.map((deployment) => (
                  <li key={deployment._id} className="px-6 py-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center">
                        <div className="flex-shrink-0">
                          <div className="h-8 w-8 rounded-full bg-primary-100 flex items-center justify-center">
                            <span className="text-sm font-medium text-primary-600">
                              {deployment.app_name.charAt(0).toUpperCase()}
                            </span>
                          </div>
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900">
                            {deployment.app_name}
                          </div>
                          <div className="text-sm text-gray-500">
                            {deployment.repository}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-4">
                        <div className="text-sm text-gray-500">
                          <div>Started: {formatDate(deployment.started_at)}</div>
                          {deployment.stopped_at && (
                            <div>Stopped: {formatDate(deployment.stopped_at)}</div>
                          )}
                          <div>Duration: {getDuration(deployment.started_at, deployment.stopped_at)}</div>
                        </div>
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          deployment.status === 'running' 
                            ? 'bg-green-100 text-green-800' 
                            : 'bg-gray-100 text-gray-800'
                        }`}>
                          {deployment.status}
                        </span>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
              
              {deploymentHistory.length === 0 && (
                <div className="text-center py-12">
                  <History className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-500">
                    No deployment history yet. Deploy your first app to see history here.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
} 