import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { ConfigProvider, Layout, Menu, Button, Dropdown, theme as antTheme } from 'antd';
import {
  HomeOutlined,
  LineChartOutlined,
  BarChartOutlined,
  SunOutlined,
  MoonOutlined,
  GlobalOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useStore } from '@/store/useStore';

import HomePage from '@/pages/HomePage';
import AnalysisPage from '@/pages/AnalysisPage';
import ResultPage from '@/pages/ResultPage';

const { Header, Content, Footer } = Layout;

function AppNavigation() {
  const { t } = useTranslation();
  const location = useLocation();
  const { theme: appTheme, toggleTheme, language, setLanguage } = useStore();

  const menuItems = [
    { key: '/', icon: <HomeOutlined />, label: <Link to="/">{t('nav.home')}</Link> },
    {
      key: '/analysis',
      icon: <LineChartOutlined />,
      label: <Link to="/analysis">{t('nav.analysis')}</Link>,
    },
    {
      key: '/result',
      icon: <BarChartOutlined />,
      label: <Link to="/result">{t('nav.result')}</Link>,
    },
  ];

  const languageItems = [
    { key: 'zh', label: '中文' },
    { key: 'en', label: 'English' },
  ];

  return (
    <Header
      className="flex items-center justify-between px-6"
      style={{
        background: appTheme === 'dark' ? '#141e30' : '#fff',
        borderBottom: `1px solid ${appTheme === 'dark' ? '#2d3748' : '#e2e8f0'}`,
        position: 'sticky',
        top: 0,
        zIndex: 100,
        height: 64,
        lineHeight: '64px',
      }}
    >
      <div className="flex items-center gap-2">
        <LineChartOutlined
          style={{ fontSize: 22, color: '#2b6cb0' }}
        />
        <span
          className="text-lg font-semibold hidden sm:inline"
          style={{ color: appTheme === 'dark' ? '#e2e8f0' : '#1a365d' }}
        >
          {t('nav.title')}
        </span>
      </div>

      <Menu
        mode="horizontal"
        selectedKeys={[location.pathname]}
        items={menuItems}
        style={{
          flex: 1,
          justifyContent: 'center',
          border: 'none',
          background: 'transparent',
        }}
      />

      <div className="flex items-center gap-2">
        <Dropdown
          menu={{
            items: languageItems,
            onClick: ({ key }) => {
              setLanguage(key as 'zh' | 'en');
              import('./i18n').then((mod) => mod.default.changeLanguage(key));
            },
            selectedKeys: [language],
          }}
        >
          <Button type="text" icon={<GlobalOutlined />} />
        </Dropdown>
        <Button
          type="text"
          icon={appTheme === 'dark' ? <SunOutlined /> : <MoonOutlined />}
          onClick={toggleTheme}
        />
      </div>
    </Header>
  );
}

export default function App() {
  const { theme: appTheme } = useStore();
  const { defaultAlgorithm, darkAlgorithm } = antTheme;

  useEffect(() => {
    document.documentElement.classList.toggle('dark', appTheme === 'dark');
  }, [appTheme]);

  return (
    <ConfigProvider
      theme={{
        algorithm: appTheme === 'dark' ? darkAlgorithm : defaultAlgorithm,
        token: {
          colorPrimary: '#2b6cb0',
          borderRadius: 8,
          fontFamily: '"Noto Sans SC", "Inter", system-ui, sans-serif',
        },
      }}
    >
      <BrowserRouter>
        <Layout className="min-h-screen" style={{ background: 'var(--color-bg)' }}>
          <AppNavigation />
          <Content className="p-4 md:p-8 max-w-7xl mx-auto w-full">
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/analysis" element={<AnalysisPage />} />
              <Route path="/result" element={<ResultPage />} />
            </Routes>
          </Content>
          <Footer
            className="text-center text-sm"
            style={{
              background: 'transparent',
              color: 'var(--color-text-secondary)',
            }}
          >
            DCF Valuation Agent &copy; {new Date().getFullYear()}
          </Footer>
        </Layout>
      </BrowserRouter>
    </ConfigProvider>
  );
}
