// Base API URL - this would be configured from environment or settings
const API_BASE_URL = 'http://localhost:5000';

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

export interface MessageResponse {
  messages: Array<{
    from: string;
    to: string;
    type: string;
    content: Record<string, any>;
  }>;
}

// API Client
export const apiClient = {
  // Health check
  async getHealth(): Promise<ApiResponse<any>> {
    try {
      const response = await fetchWithTimeout(`${API_BASE_URL}/health`);
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error checking health:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  },

  // Node operations
  async createNode(): Promise<ApiResponse<FlaskNode>> {
    try {
      const response = await fetchWithTimeout(
        `${API_BASE_URL}/nodes`,
        { 
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      return { success: true, data: await response.json() };
    } catch (error) {
      console.error('Error creating node:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  },

  // Connection operations
  async createConnection(sourceNodeId: string, targetNodeId: string): Promise<ApiResponse<FlaskConnection>> {
    try {
      const response = await fetchWithTimeout(
        `${API_BASE_URL}/connections`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ sourceNodeId, targetNodeId })
        }
      );
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      return { success: true, data: await response.json() };
    } catch (error) {
      console.error('Error creating connection:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  },

  // Message operations
  async sendInit(connectionId: string): Promise<ApiResponse<FlaskMessage>> {
    try {
      const response = await fetchWithTimeout(
        `${API_BASE_URL}/send-init`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ 
            connectionId,
            globalfeatures: "00",
            features: "01"
          })
        }
      );
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      return { success: true, data: await response.json() };
    } catch (error) {
      console.error('Error sending init message:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  },

  async getMessageFlow(connectionId: string): Promise<ApiResponse<FlaskMessage[]>> {
    try {
      const response = await fetchWithTimeout(`${API_BASE_URL}/message-flow/${connectionId}`);
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      return { success: true, data: await response.json() };
    } catch (error) {
      console.error('Error getting message flow:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  },

  connect: async () => {
    const response = await fetch(`${API_BASE_URL}/connect`, {
      method: 'POST'
    });
    return response.json() as Promise<MessageResponse>;
  },

  sendMessage: async (type: string, content?: Record<string, any>) => {
    const response = await fetch(`${API_BASE_URL}/raw-msg`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ type, content })
    });
    return response.json() as Promise<MessageResponse>;
  }
};