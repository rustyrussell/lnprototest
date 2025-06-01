import { create } from 'zustand';
import { apiClient, MessageResponse } from '../api/client';

export type MessageCategory = 'connection' | 'channel' | 'commitment' | 'routing';
export type ConnectionState = 'disconnected' | 'connecting' | 'connected';

export interface AvailableMessage {
  id: string;
  name: string;
  description: string;
  category: MessageCategory;
  type: string;
  content?: Record<string, any>;
}

interface Message {
  id: string;
  from: string;
  to: string;
  type: string;
  content: Record<string, any>;
  timestamp: number;
}

interface State {
  connected: boolean;
  connectionState: ConnectionState;
  messages: Message[];
  selectedMessage: AvailableMessage | null;
  availableMessages: AvailableMessage[];
  
  // Actions
  connect: () => Promise<void>;
  sendMessage: (type: string, content?: Record<string, any>) => Promise<void>;
  selectMessage: (message: AvailableMessage | null) => void;
  setConnectionState: (state: ConnectionState) => void;
  resetLogs: () => void;
  initializeConnection: () => Promise<void>;
  setMessages: (messages: Message[]) => void;
}

// Predefined available messages
const defaultAvailableMessages: AvailableMessage[] = [
  // Connection Messages
  {
    id: 'init',
    name: 'Init',
    description: 'Initialize connection with peer',
    category: 'connection',
    type: 'init',
    content: {
      globalfeatures: "00",
      features: "01"
    }
  },
  {
    id: 'ping',
    name: 'Ping',
    description: 'Send ping to peer',
    category: 'connection',
    type: 'ping',
    content: {
      num_pong_bytes: 1,
      ignored: '00'
    }
  },
  {
    id: 'pong',
    name: 'Pong',
    description: 'Response to ping message',
    category: 'connection',
    type: 'pong',
    content: {
      ignored: '00'
    }
  },
  {
    id: 'error',
    name: 'Error',
    description: 'Send error message to peer',
    category: 'connection',
    type: 'error',
    content: {
      channel_id: '0000000000000000000000000000000000000000000000000000000000000000',
      data: 'Test error message'
    }
  },

  // Channel Messages
  {
    id: 'open_channel',
    name: 'Open Channel',
    description: 'Request to open a new channel',
    category: 'channel',
    type: 'open_channel',
    content: {
      // To be implemented
    }
  },
  {
    id: 'accept_channel',
    name: 'Accept Channel',
    description: 'Accept a channel opening request',
    category: 'channel',
    type: 'accept_channel',
    content: {
      // To be implemented
    }
  },
  {
    id: 'funding_created',
    name: 'Funding Created',
    description: 'Channel funding transaction created',
    category: 'channel',
    type: 'funding_created',
    content: {
      // To be implemented
    }
  },

  // Commitment Messages
  {
    id: 'commitment_signed',
    name: 'Commitment Signed',
    description: 'Sign a new commitment transaction',
    category: 'commitment',
    type: 'commitment_signed',
    content: {
      // To be implemented
    }
  },
  {
    id: 'revoke_and_ack',
    name: 'Revoke and Acknowledge',
    description: 'Revoke previous commitment transaction and acknowledge new one',
    category: 'commitment',
    type: 'revoke_and_ack',
    content: {
      // To be implemented
    }
  },

  // Routing Messages
  {
    id: 'channel_announcement',
    name: 'Channel Announcement',
    description: 'Announce a new channel to the network',
    category: 'routing',
    type: 'channel_announcement',
    content: {
      // To be implemented
    }
  },
  {
    id: 'node_announcement',
    name: 'Node Announcement',
    description: 'Announce node information to the network',
    category: 'routing',
    type: 'node_announcement',
    content: {
      // To be implemented
    }
  },
  {
    id: 'channel_update',
    name: 'Channel Update',
    description: 'Update channel routing policies',
    category: 'routing',
    type: 'channel_update',
    content: {
      // To be implemented
    }
  }
];

export const useStore = create<State>((set, get) => ({
  connected: false,
  connectionState: 'disconnected',
  messages: [],
  selectedMessage: null,
  availableMessages: defaultAvailableMessages,

  connect: async () => {
    try {
      set({ connectionState: 'connecting' });
      const response = await apiClient.connect();
      const newMessages = response.messages.map(msg => ({
        id: Math.random().toString(36).substr(2, 9),
        ...msg,
        timestamp: Date.now()
      }));
      
      set(state => ({ 
        connected: true,
        connectionState: 'connected',
        messages: [...state.messages, ...newMessages]
      }));
    } catch (error) {
      console.error('Connection error:', error);
      set({ 
        connected: false,
        connectionState: 'disconnected'
      });
    }
  },

  sendMessage: async (type, content) => {
    try {
      const response = await apiClient.sendMessage(type, content);
      const newMessages = response.messages.map(msg => ({
        id: Math.random().toString(36).substr(2, 9),
        ...msg,
        timestamp: Date.now()
      }));
      
      set(state => ({ 
        messages: [...state.messages, ...newMessages]
      }));
    } catch (error) {
      console.error('Send message error:', error);
    }
  },

  selectMessage: (message) => set({ selectedMessage: message }),
  
  setConnectionState: (state) => set({ connectionState: state }),
  
  resetLogs: () => set({ messages: [] }),
  
  initializeConnection: async () => {
    try {
      set({ connectionState: 'connecting' });
      const response = await apiClient.connect();
      const newMessages = response.messages.map(msg => ({
        id: Math.random().toString(36).substr(2, 9),
        ...msg,
        timestamp: Date.now()
      }));
      
      set(state => ({ 
        connected: true,
        connectionState: 'connected',
        messages: [...state.messages, ...newMessages]
      }));
    } catch (error) {
      console.error('Connection initialization error:', error);
      set({ 
        connected: false,
        connectionState: 'disconnected'
      });
    }
  },

  setMessages: (messages: Message[]) => set({ messages })
}));