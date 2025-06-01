import React from 'react';
import {
  Container,
  Header,
  SpaceBetween,
  Tabs,
  Box,
  Link
} from '@cloudscape-design/components';

const DocsPage: React.FC = () => {
  return (
    <Container
      header={
        <Header
          variant="h2"
          description="Documentation for using the Lightning Network Message Flow Visualizer"
        >
          Documentation
        </Header>
      }
    >
      <Tabs
        tabs={[
          {
            id: 'getting-started',
            label: 'Getting Started',
            content: (
              <Box padding={{ top: 'l' }}>
                <SpaceBetween size="l">
                  <div>
                    <h3>Introduction</h3>
                    <p>
                      The Lightning Network Message Flow Visualizer allows you to test and visualize the
                      communication between Lightning Network nodes according to the BOLT specifications.
                    </p>
                  </div>
                  
                  <div>
                    <h3>Quick Start</h3>
                    <ol>
                      <li>Connect to an LDK implementation using the Connect button in the header</li>
                      <li>Select a message from the Message Catalog on the left side</li>
                      <li>Review and optionally edit the message details</li>
                      <li>Click "Send Message" to send it to the node</li>
                      <li>Watch the visual representation of the message flow</li>
                    </ol>
                  </div>
                  
                  <div>
                    <h3>Prerequisites</h3>
                    <ul>
                      <li>lnprototest installed and configured</li>
                      <li>A supported Lightning implementation (LDK, c-lightning, or LND)</li>
                    </ul>
                  </div>
                </SpaceBetween>
              </Box>
            )
          },
          {
            id: 'messages',
            label: 'Message Types',
            content: (
              <Box padding={{ top: 'l' }}>
                <SpaceBetween size="l">
                  <div>
                    <h3>BOLT-01 Connection Messages</h3>
                    <ul>
                      <li><strong>init</strong> - Initializes a connection between nodes</li>
                      <li><strong>error</strong> - Reports an error to the connected peer</li>
                      <li><strong>warning</strong> - Reports a warning to the connected peer</li>
                      <li><strong>ping</strong> - Ping message to check liveness</li>
                      <li><strong>pong</strong> - Pong response to a ping</li>
                    </ul>
                  </div>
                  
                  <div>
                    <h3>BOLT-02 Channel Messages</h3>
                    <ul>
                      <li><strong>open_channel</strong> - Request to open a new payment channel</li>
                      <li><strong>accept_channel</strong> - Accept a channel opening request</li>
                      <li><strong>funding_created</strong> - Sent after creating the funding transaction</li>
                      <li><strong>funding_signed</strong> - Response to the funding_created message</li>
                    </ul>
                  </div>
                  
                  <div>
                    <h3>Advanced Message Types</h3>
                    <p>
                      Additional message types from other BOLTs will be added in future updates.
                      See the <Link href="https://github.com/lightning/bolts" external>BOLT specifications</Link> for more details.
                    </p>
                  </div>
                </SpaceBetween>
              </Box>
            )
          },
          {
            id: 'api',
            label: 'API Reference',
            content: (
              <Box padding={{ top: 'l' }}>
                <SpaceBetween size="l">
                  <div>
                    <h3>REST API Endpoints</h3>
                    <ul>
                      <li><code>GET /api/status</code> - Check the connection status</li>
                      <li><code>POST /api/connect</code> - Connect to a Lightning node</li>
                      <li><code>POST /api/disconnect</code> - Disconnect from a Lightning node</li>
                      <li><code>POST /api/send</code> - Send a message to the connected node</li>
                      <li><code>GET /api/logs</code> - Get message logs</li>
                    </ul>
                  </div>
                  
                  <div>
                    <h3>Example API Request</h3>
                    <pre>
                      {`
POST /api/send
Content-Type: application/json

{
  "type": "init",
  "payload": {
    "globalfeatures": "0x",
    "localfeatures": "0x2082"
  }
}
                      `}
                    </pre>
                  </div>
                </SpaceBetween>
              </Box>
            )
          }
        ]}
      />
    </Container>
  );
};

export default DocsPage;