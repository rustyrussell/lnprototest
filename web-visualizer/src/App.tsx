import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { AppLayout, ContentLayout } from '@cloudscape-design/components';
import AppNavigation from './components/layout/AppNavigation';
import Header from './components/layout/Header';
import VisualizerPage from './pages/VisualizerPage';
import SettingsPage from './pages/SettingsPage';
import DocsPage from './pages/DocsPage';

function App() {
  const [navigationOpen, setNavigationOpen] = React.useState(true);

  return (
    <AppLayout
      navigation={<AppNavigation />}
      navigationOpen={navigationOpen}
      onNavigationChange={({ detail }) => setNavigationOpen(detail.open)}
      content={
        <ContentLayout header={<Header />}>
          <Routes>
            <Route path="/" element={<VisualizerPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/docs" element={<DocsPage />} />
          </Routes>
        </ContentLayout>
      }
      toolsHide
    />
  );
}

export default App;