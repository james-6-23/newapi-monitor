import React from 'react'
import { Routes, Route } from 'react-router-dom'
import { Layout } from 'antd'
import AppLayout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Top from './pages/Top'
import Heatmap from './pages/Heatmap'
import Anomalies from './pages/Anomalies'

const { Content } = Layout

function App() {
  return (
    <AppLayout>
      <Content style={{ margin: '24px 16px', padding: 24, minHeight: 280 }}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/top" element={<Top />} />
          <Route path="/heatmap" element={<Heatmap />} />
          <Route path="/anomalies" element={<Anomalies />} />
        </Routes>
      </Content>
    </AppLayout>
  )
}

export default App
