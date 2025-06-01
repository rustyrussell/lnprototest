import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000';

export interface ConnectRequest {
  sourcePrivkey?: string;
  targetPrivkey?: string;
  globalfeatures?: string;
  features?: string;
}

export interface RawMessageRequest {
  type: string;
  connprivkey: string;
  content?: Record<string, any>;
}

export interface MessageResponse {
  type: string;
  content: {
    globalfeatures: string;
    features: string;
  };
}

export interface ConnectResponse {
  sent: MessageResponse;
  received: MessageResponse;
}

const api = {
  // Health check
  checkHealth: () => axios.get(`${API_BASE_URL}/health`),

  // Connect two nodes and perform handshake
  connect: (data: ConnectRequest) => 
    axios.post<ConnectResponse>(`${API_BASE_URL}/connect`, data),

  // Send a raw message
  sendRawMessage: (data: RawMessageRequest) =>
    axios.post<MessageResponse>(`${API_BASE_URL}/raw-msg`, data),
};

export default api; 