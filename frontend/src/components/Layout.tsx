/**
 * 应用布局组件
 */
import React, { useState } from 'react';
import { Layout, Menu, Typography, Avatar, Dropdown, Space, Badge } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  DashboardOutlined,
  TrophyOutlined,
  HeatMapOutlined,
  WarningOutlined,
  UserOutlined,
  SettingOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons';

const { Header, Sider, Content } = Layout;
const { Title } = Typography;

interface AppLayoutProps {
  children: React.ReactNode;
}

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  // 菜单项配置
  const menuItems = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: '总览',
      path: '/dashboard',
    },
    {
      key: '/top',
      icon: <TrophyOutlined />,
      label: 'Top排行',
      path: '/top',
    },
    {
      key: '/heatmap',
      icon: <HeatMapOutlined />,
      label: '热力图',
      path: '/heatmap',
    },
    {
      key: '/anomalies',
      icon: <WarningOutlined />,
      label: '异常中心',
      path: '/anomalies',
    },
  ];

  // 用户菜单
  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人资料',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '系统设置',
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
    },
  ];

  const handleMenuClick = ({ key }: { key: string }) => {
    const item = menuItems.find(item => item.key === key);
    if (item) {
      navigate(item.path);
    }
  };

  const handleUserMenuClick = ({ key }: { key: string }) => {
    switch (key) {
      case 'profile':
        // TODO: 打开个人资料页面
        break;
      case 'settings':
        // TODO: 打开设置页面
        break;
      case 'logout':
        // TODO: 执行退出登录
        break;
    }
  };

  // 获取当前选中的菜单项
  const selectedKeys = [location.pathname === '/' ? '/dashboard' : location.pathname];

  return (
    <Layout className="app-layout" style={{ minHeight: '100vh' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        className="app-sider"
        width={240}
        style={{
          background: '#fff',
          boxShadow: '2px 0 6px rgba(0, 21, 41, 0.05)',
        }}
      >
        {/* Logo区域 */}
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
            padding: collapsed ? 0 : '0 24px',
            borderBottom: '1px solid #f0f0f0',
          }}
        >
          {collapsed ? (
            <Avatar
              size={32}
              style={{ backgroundColor: '#1890ff' }}
              icon={<DashboardOutlined />}
            />
          ) : (
            <Title level={4} style={{ margin: 0, color: '#1890ff' }}>
              NewAPI Monitor
            </Title>
          )}
        </div>

        {/* 导航菜单 */}
        <Menu
          mode="inline"
          selectedKeys={selectedKeys}
          style={{ borderRight: 0, marginTop: 16 }}
          onClick={handleMenuClick}
          items={menuItems}
        />
      </Sider>

      <Layout>
        {/* 顶部导航栏 */}
        <Header
          className="app-header"
          style={{
            background: '#fff',
            padding: '0 24px',
            boxShadow: '0 1px 4px rgba(0, 21, 41, 0.08)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          {/* 左侧：折叠按钮 */}
          <div>
            {React.createElement(
              collapsed ? MenuUnfoldOutlined : MenuFoldOutlined,
              {
                style: { fontSize: 18, cursor: 'pointer' },
                onClick: () => setCollapsed(!collapsed),
              }
            )}
          </div>

          {/* 右侧：用户信息 */}
          <Space size="middle">
            {/* 告警徽章 */}
            <Badge count={0} showZero={false}>
              <WarningOutlined style={{ fontSize: 18, color: '#666' }} />
            </Badge>

            {/* 用户下拉菜单 */}
            <Dropdown
              menu={{
                items: userMenuItems,
                onClick: handleUserMenuClick,
              }}
              placement="bottomRight"
              arrow
            >
              <Space style={{ cursor: 'pointer' }}>
                <Avatar
                  size={32}
                  style={{ backgroundColor: '#87d068' }}
                  icon={<UserOutlined />}
                />
                <span style={{ color: '#666' }}>管理员</span>
              </Space>
            </Dropdown>
          </Space>
        </Header>

        {/* 主内容区域 */}
        <Content
          style={{
            margin: '24px 16px',
            padding: 24,
            minHeight: 280,
            background: '#f0f2f5',
          }}
        >
          {children}
        </Content>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
