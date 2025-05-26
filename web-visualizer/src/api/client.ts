import { ApiResponse, Message, MessageLog, ConnectionState } from '../types';

// Base API URL - this would be configured from environment or settings
const API_BASE_URL = 'http://localhost:8000/api';

// Helper function for fetch requests
async function fetchWithTimeout(url: string, options: RequestInit = {}, timeout = 5000): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    throw error;
  }
}

// API Client
export const apiClient = {
  // Check connection status
  async getStatus(): Promise<ApiResponse<{ state: ConnectionState }>> {
    try {
      const response = await fetchWithTimeout(`${API_BASE_URL}/status`);
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching status:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  },
  
  // Connect to node
  async connect(implementation: string = 'ldk'): Promise<ApiResponse<{ state: ConnectionState }>> {
    try {
      const response = await fetchWithTimeout(
        `${API_BASE_URL}/connect`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ implementation })
        }
      );
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error connecting:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  },
  
  // Disconnect from node
  async disconnect(): Promise<ApiResponse<{ state: ConnectionState }>> {
    try {
      const response = await fetchWithTimeout(
        `${API_BASE_URL}/disconnect`,
        { method: 'POST' }
      );
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error disconnecting:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  },
  
  // Send message to node
  async sendMessage(message: Message): Promise<ApiResponse<MessageLog>> {
    try {
      const response = await fetchWithTimeout(
        `${API_BASE_URL}/send`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(message)
        }
      );
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error sending message:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  },
  
  // Get message logs
  async getLogs(): Promise<ApiResponse<MessageLog[]>> {
    try {
      const response = await fetchWithTimeout(`${API_BASE_URL}/logs`);
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error fetching logs:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }
};