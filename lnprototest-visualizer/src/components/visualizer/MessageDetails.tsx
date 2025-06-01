import React from 'react';
import {
  Container,
  Header,
  Box,
  SpaceBetween
} from '@cloudscape-design/components';
import { useStore } from '../../store';

const MessageDetails: React.FC = () => {
  const selectedMessage = useStore(state => state.selectedMessage);

  if (!selectedMessage) {
    return (
      <Container
        header={
          <Header variant="h2">
            Message Details
          </Header>
        }
      >
        <div className="p-4 text-center text-gray-500">
          Select a message to view its details
        </div>
      </Container>
    );
  }

  const messageContent = {
    type: selectedMessage.type,
    category: selectedMessage.category,
    content: selectedMessage.content || {}
  };

  return (
    <Container
      header={
        <Header
          variant="h2"
          description={selectedMessage.description}
        >
          {selectedMessage.name} Details
        </Header>
      }
    >
      <SpaceBetween size="l">
        <Box variant="code">
          <pre className="bg-gray-800 text-gray-100 p-4 rounded-md overflow-auto">
            {JSON.stringify(messageContent, null, 2)}
          </pre>
        </Box>
      </SpaceBetween>
    </Container>
  );
};

export default MessageDetails;