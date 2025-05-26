import React, { useEffect, useState } from 'react';
import {
  Container,
  Header,
  StatusIndicator,
  Box,
  SpaceBetween,
  Button
} from '@cloudscape-design/components';
import { Zap, ArrowRight, ArrowLeft } from 'lucide-react';
import { useStore } from '../../store';

const NodeComponent: React.FC<{ label: string, type: string }> = ({ label, type }) => {
  return (
    <div className={`flex flex-col items-center justify-center p-4 rounded-lg border shadow-md ${
      type === 'runner' ? 'bg-blue-50 border-blue-500' : 'bg-yellow-50 border-yellow-500'
    }`}>
      <div className={`w-16 h-16 rounded-full flex items-center justify-center mb-2 ${
        type === 'runner' ? 'bg-blue-100' : 'bg-yellow-100'
      }`}>
        <Zap size={24} className={type === 'runner' ? 'text-blue-500' : 'text-yellow-500'} />
      </div>
      <div className="text-sm font-semibold">{label}</div>
    </div>
  );
};

const MessageFlow: React.FC = () => {
  const nodes = useStore(state => state.nodes);
  const messageLogs = useStore(state => state.messageLogs);
  const connectionState = useStore(state => state.connectionState);
  
  // Animation states for messages
  const [animatingMessages, setAnimatingMessages] = useState<string[]>([]);
  
  // Add animation when new messages are added
  useEffect(() => {
    if (messageLogs.length > 0) {
      const latestMessage = messageLogs[messageLogs.length - 1];
      setAnimatingMessages(prev => [...prev, latestMessage.id]);
      
      // Remove animation after it completes
      setTimeout(() => {
        setAnimatingMessages(prev => prev.filter(id => id !== latestMessage.id));
      }, 1500);
    }
  }, [messageLogs.length]);

  const getConnectionStatusIndicator = () => {
    switch (connectionState) {
      case 'connected':
        return <StatusIndicator type="success">Connected</StatusIndicator>;
      case 'connecting':
        return <StatusIndicator type="in-progress">Connecting</StatusIndicator>;
      case 'disconnected':
        return <StatusIndicator type="stopped">Disconnected</StatusIndicator>;
      case 'error':
        return <StatusIndicator type="error">Connection Error</StatusIndicator>;
      default:
        return <StatusIndicator type="stopped">Disconnected</StatusIndicator>;
    }
  };

  return (
    <Container
      header={
        <Header
          variant="h2"
          description="Visualization of message flow between nodes"
          actions={
            <SpaceBetween direction="horizontal" size="xs">
              {getConnectionStatusIndicator()}
            </SpaceBetween>
          }
        >
          Message Flow
        </Header>
      }
    >
      <Box padding="l">
        <div className="flex flex-col items-center justify-center h-[500px] relative">
          {/* Connection line */}
          <div className="absolute w-[400px] h-[2px] bg-gray-200 top-1/2 transform -translate-y-1/2" />
          
          {/* Nodes */}
          <div className="flex justify-between w-full px-16">
            {nodes.map((node) => (
              <NodeComponent 
                key={node.id} 
                label={node.label} 
                type={node.type} 
              />
            ))}
          </div>
          
          {/* Message animations */}
          <div className="absolute inset-0 pointer-events-none">
            {messageLogs.slice(-5).map((log, index) => {
              const isAnimating = animatingMessages.includes(log.id);
              const fromLeft = log.source === 'runner';
              const yOffset = 50 + (index * 30);
              
              return (
                <div 
                  key={log.id}
                  className={`absolute top-[calc(50%_-_${yOffset}px)] ${fromLeft ? 'left-[120px]' : 'right-[120px]'} 
                             flex items-center ${isAnimating ? 'message-flow-animation' : ''}`}
                  style={{ 
                    transform: `translateY(${yOffset}px)`,
                    opacity: isAnimating ? 1 : 0.7,
                    transition: 'opacity 0.3s ease'
                  }}
                >
                  {fromLeft ? (
                    <>
                      <span className="text-xs font-medium mr-2">{log.message.name}</span>
                      <ArrowRight size={16} className="text-blue-500" />
                    </>
                  ) : (
                    <>
                      <ArrowLeft size={16} className="text-yellow-500" />
                      <span className="text-xs font-medium ml-2">{log.message.name}</span>
                    </>
                  )}
                </div>
              );
            })}
          </div>
          
          {/* Message log display */}
          <div className="absolute bottom-4 left-4 right-4 bg-white border border-gray-200 rounded-md p-2 h-32 overflow-y-auto">
            <div className="text-xs font-semibold mb-2">Message Log</div>
            {messageLogs.length === 0 ? (
              <div className="text-xs text-gray-500">No messages exchanged yet</div>
            ) : (
              messageLogs.map((log) => (
                <div key={log.id} className="text-xs mb-1">
                  <span className="text-gray-500">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                  {' '}
                  <span className={log.source === 'runner' ? 'text-blue-600' : 'text-yellow-600'}>
                    {log.source.toUpperCase()}
                  </span>
                  {' → '}
                  <span className={log.target === 'runner' ? 'text-blue-600' : 'text-yellow-600'}>
                    {log.target.toUpperCase()}
                  </span>
                  {': '}
                  <span className="font-medium">{log.message.name}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </Box>
    </Container>
  );
};

export default MessageFlow;