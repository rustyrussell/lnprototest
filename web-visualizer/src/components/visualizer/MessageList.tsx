import React, { useState } from 'react';
import { 
  Box,
  Container,
  Header,
  Tabs,
  SpaceBetween,
  Button,
  Input,
  Select,
  Table,
  TextFilter
} from '@cloudscape-design/components';
import { useStore } from '../../store';
import { Message, MessageCategory } from '../../types';

const MessageList: React.FC = () => {
  const availableMessages = useStore(state => state.availableMessages);
  const selectedMessage = useStore(state => state.selectedMessage);
  const selectMessage = useStore(state => state.selectMessage);
  const sendMessage = useStore(state => state.sendMessage);
  const connectionState = useStore(state => state.connectionState);
  
  const [filterText, setFilterText] = useState('');
  const [activeCategory, setActiveCategory] = useState<MessageCategory | 'all'>('all');

  const filteredMessages = availableMessages.filter(message => {
    const matchesFilter = message.name.toLowerCase().includes(filterText.toLowerCase()) ||
                          message.description.toLowerCase().includes(filterText.toLowerCase());
    const matchesCategory = activeCategory === 'all' || message.category === activeCategory;
    
    return matchesFilter && matchesCategory;
  });

  const handleSendMessage = async () => {
    if (selectedMessage && connectionState === 'connected') {
      await sendMessage(selectedMessage);
      selectMessage(null);
    }
  };

  return (
    <Container
      header={
        <Header
          variant="h2"
          description="Select a message to send to the Lightning node"
        >
          Message Catalog
        </Header>
      }
    >
      <SpaceBetween size="l">
        <Tabs
          tabs={[
            {
              id: 'all',
              label: 'All',
              content: (
                <Box padding={{ top: 'l' }}>
                  <TextFilter
                    filteringText={filterText}
                    onChange={({ detail }) => setFilterText(detail.filteringText)}
                    placeholder="Find messages"
                  />
                </Box>
              )
            },
            {
              id: 'connection',
              label: 'Connection',
              content: null
            },
            {
              id: 'channel',
              label: 'Channel',
              content: null
            },
            {
              id: 'commitment',
              label: 'Commitment',
              content: null
            },
            {
              id: 'routing',
              label: 'Routing',
              content: null
            }
          ]}
          onChange={({ detail }) => setActiveCategory(detail.activeTabId as MessageCategory | 'all')}
        />
        
        <Table
          items={filteredMessages}
          trackBy="id"
          selectionType="single"
          selectedItems={selectedMessage ? [selectedMessage] : []}
          onSelectionChange={({ detail }) => {
            selectMessage(detail.selectedItems[0] as Message);
          }}
          columnDefinitions={[
            {
              id: 'name',
              header: 'Message',
              cell: item => item.name,
              sortingField: 'name'
            },
            {
              id: 'description',
              header: 'Description',
              cell: item => item.description
            },
            {
              id: 'category',
              header: 'Category',
              cell: item => item.category.charAt(0).toUpperCase() + item.category.slice(1)
            }
          ]}
          empty={
            <Box textAlign="center" color="inherit">
              <b>No messages</b>
              <Box padding={{ bottom: 's' }} variant="p" color="inherit">
                No messages match the current filter.
              </Box>
            </Box>
          }
        />
        
        <Box textAlign="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button 
              disabled={!selectedMessage || connectionState !== 'connected'} 
              variant="primary"
              onClick={handleSendMessage}
            >
              Send Message
            </Button>
          </SpaceBetween>
        </Box>
      </SpaceBetween>
    </Container>
  );
};

export default MessageList;