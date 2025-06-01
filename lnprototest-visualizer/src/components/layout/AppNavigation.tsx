import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { SideNavigation } from '@cloudscape-design/components';

const AppNavigation: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <SideNavigation
      activeHref={location.pathname}
      header={{ text: 'LN Protocol Test', href: '/' }}
      onFollow={e => {
        e.preventDefault();
        navigate(e.detail.href);
      }}
      items={[
        { type: 'link', text: 'Visualizer', href: '/' },
        { type: 'link', text: 'Settings', href: '/settings' },
        { type: 'link', text: 'Documentation', href: '/docs' },
        {
          type: 'section',
          text: 'Resources',
          items: [
          
            { 
              type: 'link', 
              text: 'lnprototest', 
              href: 'https://github.com/rustyrussell/lnprototest', 
              external: true 
            },
            { 
              type: 'link', 
              text: 'LDK Documentation', 
              href: 'https://lightningdevkit.org/', 
              external: true 
            }
          ]
        }
      ]}
    />
  );
};

export default AppNavigation;