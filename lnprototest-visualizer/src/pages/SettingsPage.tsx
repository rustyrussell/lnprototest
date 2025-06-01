import React from 'react';
import {
  Container,
  Header,
  SpaceBetween,
  FormField,
  Input,
  Select,
  Checkbox,
  Button,
  Box
} from '@cloudscape-design/components';

const SettingsPage: React.FC = () => {
  return (
    <Container
      header={
        <Header
          variant="h2"
          description="Configure connection settings for lnprototest"
        >
          Settings
        </Header>
      }
    >
      <SpaceBetween size="l">
        <FormField
          label="LDK Implementation"
          description="Select which Lightning implementation to use"
        >
          <Select
            selectedOption={{ label: "LDK", value: "ldk" }}
            options={[
              { label: "LDK", value: "ldk" },
              { label: "c-lightning", value: "c-lightning" },
              { label: "LND", value: "lnd" }
            ]}
            onChange={() => {}}
          />
        </FormField>
        
        <FormField
          label="API Endpoint"
          description="URL for the lnprototest API"
        >
          <Input
            value="http://localhost:8000/api"
            onChange={() => {}}
          />
        </FormField>
        
        <FormField
          label="Connection Timeout (ms)"
          description="Maximum time to wait for a connection"
        >
          <Input
            type="number"
            value="5000"
            onChange={() => {}}
          />
        </FormField>
        
        <FormField
          label="Message Timeout (ms)"
          description="Maximum time to wait for a message response"
        >
          <Input
            type="number"
            value="2000"
            onChange={() => {}}
          />
        </FormField>
        
        <FormField
          label="Node Configuration"
        >
          <SpaceBetween size="m">
            <Checkbox
              checked={true}
              onChange={() => {}}
            >
              Enable automatic responses
            </Checkbox>
            
            <Checkbox
              checked={true}
              onChange={() => {}}
            >
              Log all messages
            </Checkbox>
            
            <Checkbox
              checked={false}
              onChange={() => {}}
            >
              Strict BOLT compliance
            </Checkbox>
          </SpaceBetween>
        </FormField>
        
        <Box textAlign="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button>Reset to Defaults</Button>
            <Button variant="primary">Save Settings</Button>
          </SpaceBetween>
        </Box>
      </SpaceBetween>
    </Container>
  );
};

export default SettingsPage;