import React from 'react';
import { Grid } from '@cloudscape-design/components';
import MessageList from '../components/visualizer/MessageList';
import MessageFlow from '../components/visualizer/MessageFlow';
import MessageDetails from '../components/visualizer/MessageDetails';

const VisualizerPage: React.FC = () => {
  return (
    <Grid
      gridDefinition={[
        { colspan: { default: 12, xxs: 12, xs: 5, s: 5, m: 4, l: 4, xl: 3 } },
        { colspan: { default: 12, xxs: 12, xs: 7, s: 7, m: 8, l: 8, xl: 9 } }
      ]}
    >
      <div>
        <MessageList />
        <div className="mt-6">
          <MessageDetails />
        </div>
      </div>
      <div>
        <MessageFlow />
      </div>
    </Grid>
  );
};

export default VisualizerPage;