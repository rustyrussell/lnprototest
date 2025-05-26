import React from 'react';
import { useLocation } from 'react-router-dom';
import { Header as CloudscapeHeader, Button, ButtonDropdown, SpaceBetween } from '@cloudscape-design/components';
import { useStore } from '../../store';
import { Zap } from 'lucide-react';

const Header: React.FC = () => {
  const location = useLocation();
  const connectionState = useStore(state => state.connectionState);
  const setConnectionState = useStore(state => state.setConnectionState);
  const resetLogs = useStore(state => state.resetLogs);

  const getTitle = () => {
    switch (location.pathname) {
      case '/':
        return 'Lightning Network Message Flow Visualizer';
      case '/settings':
        return 'Settings';
      case '/docs':
        return 'Documentation';
      default:
        return 'Lightning Network Message Flow Visualizer';
    }
  };

  const handleConnectionToggle = () => {
    if (connectionState === 'disconnected') {
      setConnectionState('connecting');
      // Simulate connection process
      setTimeout(() => {
        setConnectionState('connected');
      }, 1000);
    } else {
      setConnectionState('disconnected');
      resetLogs();
    }
  };

  const connectionButtonText = 
    connectionState === 'disconnected' ? 'Connect' :
    connectionState === 'connecting' ? 'Connecting...' :
    'Disconnect';

  const connectionButtonVariant = 
    connectionState === 'disconnected' ? 'primary' :
    connectionState === 'connecting' ? 'normal' :
    'normal';

  return (
    <CloudscapeHeader
      variant="h1"
      actions={
        <SpaceBetween direction="horizontal" size="xs">
          <ButtonDropdown
            items={[
              { id: 'ldk', text: 'LDK' },
              { id: 'c-lightning', text: 'c-lightning' },
              { id: 'lnd', text: 'LND' }
            ]}
          >
            Implementation: LDK
          </ButtonDropdown>
          <Button
            variant={connectionButtonVariant}
            onClick={handleConnectionToggle}
            iconName={connectionState === 'connected' ? 'close' : 'add-plus'}
          >
            {connectionButtonText}
          </Button>
        </SpaceBetween>
      }
    >
      <div className="flex items-center">
        <Zap className="mr-2 text-yellow-400" size={24} />
        {getTitle()}
      </div>
    </CloudscapeHeader>
  );
};

export default Header;