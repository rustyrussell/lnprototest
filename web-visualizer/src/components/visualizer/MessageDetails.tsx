import React from 'react';
import {
  Container,
  Header,
  CodeEditor,
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

  const messageDetails = JSON.stringify(selectedMessage.payload || {}, null, 2);

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
        <CodeEditor
          language="json"
          value={messageDetails}
          onChange={({ detail }) => {
            // In a real implementation, we'd update the selected message
            // with the edited payload
          }}
          preferences={{ theme: 'light' }}
          ace={{
            tabSize: 2
          }}
        />
      </SpaceBetween>
    </Container>
  );
};

export default MessageDetails;