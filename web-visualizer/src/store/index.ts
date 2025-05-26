import { create } from 'zustand';
import { 
  Node, 
  Message, 
  MessageLog, 
  ConnectionState 
} from '../types';
import { defaultMessages } from '../data/messages';

interface State {
  // Nodes
  nodes: Node[];
  
  // Messages
  availableMessages: Message[];
  selectedMessage: Message | null;
  
  // Connection
  connectionState: ConnectionState;
  
  // Message Logs
  messageLogs: MessageLog[];
  
  // Actions
  selectMessage: (message: Message | null) => void;
  sendMessage: (message: Message) => Promise<void>;
  setConnectionState: (state: ConnectionState) => void;
  resetLogs: () => void;
}

export const useStore = create<State>((set, get) => ({
  // Initial nodes
  nodes: [
    {
      id: 'runner',
      type: 'runner',
      label: 'Runner',
      position: { x: 100, y: 200 }
    },
    {
      id: 'ldk',
      type: 'ldk',
      label: 'LDK',
      position: { x: 400, y: 200 }
    }
  ],
  
  // Available messages from data
  availableMessages: defaultMessages,
  
  // No message selected initially
  selectedMessage: null,
  
  // Initial connection state
  connectionState: 'disconnected',
  
  // Empty message logs
  messageLogs: [],
  
  // Actions
  selectMessage: (message) => set({ selectedMessage: message }),
  
  sendMessage: async (message) => {
    // In a real implementation, this would call the API
    // For now, we'll simulate a response
    
    const messageLog: MessageLog = {
      id: `log-${Date.now()}`,
      timestamp: Date.now(),
      source: 'runner',
      target: 'ldk',
      message,
      status: 'sent'
    };
    
    set((state) => ({
      messageLogs: [...state.messageLogs, messageLog]
    }));
    
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Simulate response based on message type
    if (message.type === 'init') {
      // Update connection state
      set({ connectionState: 'connected' });
      
      // Add response message
      const responseLog: MessageLog = {
        id: `log-${Date.now()}`,
        timestamp: Date.now(),
        source: 'ldk',
        target: 'runner',
        message: {
          ...message,
          id: `response-${message.id}`
        },
        status: 'received'
      };
      
      set((state) => ({
        messageLogs: [...state.messageLogs, responseLog]
      }));
    }
  },
  
  setConnectionState: (state) => set({ connectionState: state }),
  
  resetLogs: () => set({ messageLogs: [] })
}));