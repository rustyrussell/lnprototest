import React, { useState, useCallback, useEffect } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import {
  Container,
  Header,
  StatusIndicator,
  Box,
  SpaceBetween,
  Button,
  Select
} from '@cloudscape-design/components';
import { Zap } from 'lucide-react';
import { useStore } from '../../store';
import MessageLog from './MessageLog';

// Custom Node Component
const CustomNode = ({ data }: { data: any }) => {
  return (
    <div
      className={`flex flex-col items-center justify-center p-2 rounded-lg border shadow-md bg-white/80
        ${data.type === 'runner' ? 'border-blue-500' : 'border-yellow-500'}
        ${data.isConnected ? 'node-connected' : ''}`}
      style={{ pointerEvents: 'all', zIndex: 2 }}
    >
      <div className={`w-16 h-16 rounded-full flex items-center justify-center mb-2 
        ${data.type === 'runner' ? 'bg-blue-100' : 'bg-yellow-100'}`}
      >
        <Zap size={24} className={data.type === 'runner' ? 'text-blue-500' : 'text-yellow-500'} />
      </div>
      <div className="text-sm font-semibold">{data.label}</div>
      <div className="text-xs text-gray-500 mt-1">
        {data.isConnected ? 'Connected' : 'Disconnected'}
      </div>
    </div>
  );
};

const nodeTypes = {
  custom: CustomNode,
};

const MessageFlow: React.FC = () => {
  const connected = useStore(state => state.connected);
  const messages = useStore(state => state.messages);
  const sendMessage = useStore(state => state.sendMessage);
  const availableMessages = useStore(state => state.availableMessages);
  const selectedMessage = useStore(state => state.selectedMessage);
  const selectMessage = useStore(state => state.selectMessage);

  // Initial nodes
  const initialNodes: Node[] = [
    {
      id: 'runner',
      type: 'custom',
      position: { x: 100, y: 100 },
      data: { label: 'Runner', type: 'runner', isConnected: connected },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
    },
    {
      id: 'ldk',
      type: 'custom',
      position: { x: 500, y: 100 },
      data: { label: 'LDK', type: 'ldk', isConnected: connected },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
    },
  ];

  // Initial edges with permanent connection line
  const initialEdges: Edge[] = [
    {
      id: 'connection',
      source: 'runner',
      target: 'ldk',
      type: 'default',
      animated: connected,
      style: {
        stroke: connected ? '#3b82f6' : '#e5e7eb',
        strokeWidth: 2,
        zIndex: 0,
      },
    },
  ];

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Always keep the connection edge present and visible
  React.useEffect(() => {
    setNodes((nds) =>
      nds.map((node) => ({
        ...node,
        data: { ...node.data, isConnected: connected },
      }))
    );

    setEdges((eds) => {
      // Remove any existing connection edge
      const filtered = eds.filter(e => e.id !== 'connection');
      // Add the connection edge at the bottom
      return [
        {
          id: 'connection',
          source: 'runner',
          target: 'ldk',
          type: 'default',
          animated: connected,
          style: {
            stroke: connected ? '#3b82f6' : '#e5e7eb',
            strokeWidth: 2,
            zIndex: 0,
          },
        },
        ...filtered.filter(e => !e.id.startsWith('message-')),
        ...filtered.filter(e => e.id.startsWith('message-')),
      ];
    });
  }, [connected, setNodes, setEdges]);

  // Add message animation edges layered on top of the connection edge
  React.useEffect(() => {
    const lastMessage = messages[messages.length - 1];
    if (lastMessage) {
      const newEdge: Edge = {
        id: `message-${lastMessage.id}`,
        source: lastMessage.from === 'runner' ? 'runner' : 'ldk',
        target: lastMessage.to === 'runner' ? 'runner' : 'ldk',
        type: 'smoothstep',
        animated: true,
        style: {
          stroke: lastMessage.from === 'runner' ? '#3b82f6' : '#eab308',
          strokeWidth: 3,
          zIndex: 2,
        },
      };

      setEdges((eds) => [
        ...eds,
        newEdge
      ]);

      setTimeout(() => {
        setEdges((eds) => eds.filter(e => e.id !== `message-${lastMessage.id}`));
      }, 2000);
    }
  }, [messages, setEdges]);

  useEffect(() => {
    const interval = setInterval(() => {
      fetch('/messages')
        .then(res => res.json())
        .then(data => {
          if (data && data.messages) {
            useStore.getState().setMessages(data.messages);
          }
        });
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleSendMessage = async () => {
    if (selectedMessage && connected) {
      await sendMessage(selectedMessage.type, selectedMessage.content);
      selectMessage(null);
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
              <StatusIndicator type={connected ? "success" : "stopped"}>
                {connected ? "Connected" : "Disconnected"}
              </StatusIndicator>
              {connected && (
                <SpaceBetween direction="horizontal" size="xs">
                  <Select
                    selectedOption={selectedMessage ? {
                      label: selectedMessage.name,
                      value: selectedMessage.id
                    } : null}
                    onChange={({ detail }) => {
                      const message = availableMessages.find(m => m.id === detail.selectedOption.value);
                      selectMessage(message || null);
                    }}
                    options={availableMessages.map(msg => ({
                      label: msg.name,
                      value: msg.id,
                      description: msg.description
                    }))}
                    placeholder="Select a message"
                    filteringType="auto"
                    empty="No messages available"
                  />
                  <Button
                    onClick={handleSendMessage}
                    disabled={!selectedMessage}
                    variant="primary"
                  >
                    Send Message
                  </Button>
                </SpaceBetween>
              )}
            </SpaceBetween>
          }
        >
          Message Flow
        </Header>
      }
    >
      <SpaceBetween size="l">
        <Box padding="l">
          <div style={{ height: 400 }}>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              nodeTypes={nodeTypes}
              fitView
            >
              <Background />
              <Controls />
            </ReactFlow>
          </div>
        </Box>

        {/* Enhanced Message Log */}
        <MessageLog />
      </SpaceBetween>
    </Container>
  );
};

export default MessageFlow;