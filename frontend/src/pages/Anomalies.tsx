/**
 * 异常中心页面
 */
import React, { useState, useMemo } from 'react';
import { Card, Tabs, Space, Tag, message, Descriptions, Modal } from 'antd';
import { useQuery } from '@tanstack/react-query';
import dayjs from 'dayjs';

import DataTable from '@/components/DataTable';
import RangeFilter, { TimeRange } from '@/components/RangeFilter';
import { getAnomalies, exportCsv, Rule, getRuleLabel } from '@/api/stats';

const { TabPane } = Tabs;

const Anomalies: React.FC = () => {
  // 状态管理
  const [timeRange, setTimeRange] = useState<TimeRange>({
    start: dayjs().subtract(6, 'hour').valueOf(),
    end: dayjs().valueOf(),
  });
  const [activeRule, setActiveRule] = useState<Rule>('burst');
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<any>(null);

  // 获取异常数据
  const {
    data: anomalyData,
    isLoading,
    refetch,
    error,
  } = useQuery({
    queryKey: ['anomalies', timeRange.start, timeRange.end, activeRule],
    queryFn: () => getAnomalies({
      start_ms: timeRange.start,
      end_ms: timeRange.end,
      rule: activeRule,
    }),
  });

  // 表格列配置
  const columns = useMemo(() => {
    switch (activeRule) {
      case 'burst':
        return [
          {
            title: 'Token',
            key: 'token',
            render: (record: any) => record.token_name || `Token${record.token_id}`,
          },
          {
            title: '请求次数',
            dataIndex: 'request_count',
            key: 'request_count',
            render: (value: number) => (
              <Tag color="red">{value}</Tag>
            ),
            sorter: (a: any, b: any) => a.request_count - b.request_count,
          },
          {
            title: '时间窗口',
            dataIndex: 'window_sec',
            key: 'window_sec',
            render: (value: number) => `${value}秒`,
          },
          {
            title: '阈值',
            dataIndex: 'threshold',
            key: 'threshold',
          },
          {
            title: '首次请求',
            dataIndex: 'first_request',
            key: 'first_request',
            render: (value: string) => dayjs(value).format('HH:mm:ss'),
          },
          {
            title: '最后请求',
            dataIndex: 'last_request',
            key: 'last_request',
            render: (value: string) => dayjs(value).format('HH:mm:ss'),
          },
          {
            title: '操作',
            key: 'action',
            render: (record: any) => (
              <a onClick={() => showDetail(record)}>查看详情</a>
            ),
          },
        ];

      case 'multi_user_token':
        return [
          {
            title: 'Token',
            key: 'token',
            render: (record: any) => record.token_name || `Token${record.token_id}`,
          },
          {
            title: '用户数',
            dataIndex: 'user_count',
            key: 'user_count',
            render: (value: number) => (
              <Tag color="orange">{value}</Tag>
            ),
            sorter: (a: any, b: any) => a.user_count - b.user_count,
          },
          {
            title: '阈值',
            dataIndex: 'threshold',
            key: 'threshold',
          },
          {
            title: '用户列表',
            dataIndex: 'users',
            key: 'users',
            render: (value: string) => (
              <div style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {value}
              </div>
            ),
          },
          {
            title: '总请求数',
            dataIndex: 'total_requests',
            key: 'total_requests',
          },
          {
            title: '操作',
            key: 'action',
            render: (record: any) => (
              <a onClick={() => showDetail(record)}>查看详情</a>
            ),
          },
        ];

      case 'ip_many_users':
        return [
          {
            title: 'IP地址',
            dataIndex: 'ip',
            key: 'ip',
          },
          {
            title: '用户数',
            dataIndex: 'user_count',
            key: 'user_count',
            render: (value: number) => (
              <Tag color="volcano">{value}</Tag>
            ),
            sorter: (a: any, b: any) => a.user_count - b.user_count,
          },
          {
            title: '阈值',
            dataIndex: 'threshold',
            key: 'threshold',
          },
          {
            title: '用户列表',
            dataIndex: 'users',
            key: 'users',
            render: (value: string) => (
              <div style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {value}
              </div>
            ),
          },
          {
            title: '总请求数',
            dataIndex: 'total_requests',
            key: 'total_requests',
          },
          {
            title: '操作',
            key: 'action',
            render: (record: any) => (
              <a onClick={() => showDetail(record)}>查看详情</a>
            ),
          },
        ];

      case 'big_request':
        return [
          {
            title: 'Token',
            key: 'token',
            render: (record: any) => record.token_name || `Token${record.token_id}`,
          },
          {
            title: '用户',
            key: 'user',
            render: (record: any) => record.username || `用户${record.user_id}`,
          },
          {
            title: 'Token数量',
            dataIndex: 'token_count',
            key: 'token_count',
            render: (value: number) => (
              <Tag color="purple">{value.toLocaleString()}</Tag>
            ),
            sorter: (a: any, b: any) => a.token_count - b.token_count,
          },
          {
            title: '均值',
            dataIndex: 'mean_tokens',
            key: 'mean_tokens',
            render: (value: number) => value.toFixed(0),
          },
          {
            title: '阈值',
            dataIndex: 'threshold',
            key: 'threshold',
            render: (value: number) => value.toFixed(0),
          },
          {
            title: '时间',
            dataIndex: 'created_at',
            key: 'created_at',
            render: (value: string) => dayjs(value).format('MM-DD HH:mm'),
          },
          {
            title: '操作',
            key: 'action',
            render: (record: any) => (
              <a onClick={() => showDetail(record)}>查看详情</a>
            ),
          },
        ];

      default:
        return [];
    }
  }, [activeRule]);

  // 显示详情
  const showDetail = (record: any) => {
    setSelectedRecord(record);
    setDetailModalVisible(true);
  };

  // 渲染详情内容
  const renderDetailContent = () => {
    if (!selectedRecord) return null;

    switch (activeRule) {
      case 'burst':
        return (
          <Descriptions column={2} bordered>
            <Descriptions.Item label="Token ID">{selectedRecord.token_id}</Descriptions.Item>
            <Descriptions.Item label="Token名称">{selectedRecord.token_name || '未知'}</Descriptions.Item>
            <Descriptions.Item label="请求次数">{selectedRecord.request_count}</Descriptions.Item>
            <Descriptions.Item label="时间窗口">{selectedRecord.window_sec}秒</Descriptions.Item>
            <Descriptions.Item label="阈值">{selectedRecord.threshold}</Descriptions.Item>
            <Descriptions.Item label="首次请求">{dayjs(selectedRecord.first_request).format('YYYY-MM-DD HH:mm:ss')}</Descriptions.Item>
            <Descriptions.Item label="最后请求">{dayjs(selectedRecord.last_request).format('YYYY-MM-DD HH:mm:ss')}</Descriptions.Item>
          </Descriptions>
        );

      case 'multi_user_token':
        return (
          <Descriptions column={2} bordered>
            <Descriptions.Item label="Token ID">{selectedRecord.token_id}</Descriptions.Item>
            <Descriptions.Item label="Token名称">{selectedRecord.token_name || '未知'}</Descriptions.Item>
            <Descriptions.Item label="用户数量">{selectedRecord.user_count}</Descriptions.Item>
            <Descriptions.Item label="阈值">{selectedRecord.threshold}</Descriptions.Item>
            <Descriptions.Item label="总请求数">{selectedRecord.total_requests}</Descriptions.Item>
            <Descriptions.Item label="用户列表" span={2}>{selectedRecord.users}</Descriptions.Item>
          </Descriptions>
        );

      case 'ip_many_users':
        return (
          <Descriptions column={2} bordered>
            <Descriptions.Item label="IP地址">{selectedRecord.ip}</Descriptions.Item>
            <Descriptions.Item label="用户数量">{selectedRecord.user_count}</Descriptions.Item>
            <Descriptions.Item label="阈值">{selectedRecord.threshold}</Descriptions.Item>
            <Descriptions.Item label="总请求数">{selectedRecord.total_requests}</Descriptions.Item>
            <Descriptions.Item label="用户列表" span={2}>{selectedRecord.users}</Descriptions.Item>
          </Descriptions>
        );

      case 'big_request':
        return (
          <Descriptions column={2} bordered>
            <Descriptions.Item label="Token ID">{selectedRecord.token_id}</Descriptions.Item>
            <Descriptions.Item label="Token名称">{selectedRecord.token_name || '未知'}</Descriptions.Item>
            <Descriptions.Item label="用户ID">{selectedRecord.user_id}</Descriptions.Item>
            <Descriptions.Item label="用户名">{selectedRecord.username || '未知'}</Descriptions.Item>
            <Descriptions.Item label="Token数量">{selectedRecord.token_count.toLocaleString()}</Descriptions.Item>
            <Descriptions.Item label="请求时间">{dayjs(selectedRecord.created_at).format('YYYY-MM-DD HH:mm:ss')}</Descriptions.Item>
            <Descriptions.Item label="均值">{selectedRecord.mean_tokens.toFixed(2)}</Descriptions.Item>
            <Descriptions.Item label="标准差">{selectedRecord.std_tokens.toFixed(2)}</Descriptions.Item>
            <Descriptions.Item label="阈值">{selectedRecord.threshold.toFixed(2)}</Descriptions.Item>
            <Descriptions.Item label="σ倍数">{selectedRecord.sigma}</Descriptions.Item>
          </Descriptions>
        );

      default:
        return null;
    }
  };

  // 处理导出
  const handleExport = async () => {
    try {
      const blob = await exportCsv({
        query_type: 'anomalies',
        start_ms: timeRange.start,
        end_ms: timeRange.end,
        rule: activeRule,
      });
      
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `anomalies_${activeRule}_${dayjs().format('YYYYMMDD_HHmmss')}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      message.success('导出成功');
    } catch (error) {
      message.error('导出失败');
    }
  };

  if (error) {
    message.error('数据加载失败');
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      {/* 筛选器 */}
      <RangeFilter
        value={timeRange}
        onChange={setTimeRange}
        onRefresh={() => refetch()}
        onExport={handleExport}
        loading={isLoading}
      />

      {/* 异常规则标签页 */}
      <Card>
        <Tabs
          activeKey={activeRule}
          onChange={(key) => setActiveRule(key as Rule)}
          items={[
            {
              key: 'burst',
              label: `突发频率 ${anomalyData?.rule === 'burst' ? `(${anomalyData.total_count})` : ''}`,
              children: (
                <DataTable
                  columns={columns}
                  data={anomalyData?.data || []}
                  loading={isLoading}
                  showCard={false}
                  emptyText="未检测到突发频率异常"
                />
              ),
            },
            {
              key: 'multi_user_token',
              label: `共享Token ${anomalyData?.rule === 'multi_user_token' ? `(${anomalyData.total_count})` : ''}`,
              children: (
                <DataTable
                  columns={columns}
                  data={anomalyData?.data || []}
                  loading={isLoading}
                  showCard={false}
                  emptyText="未检测到共享Token异常"
                />
              ),
            },
            {
              key: 'ip_many_users',
              label: `同IP多账号 ${anomalyData?.rule === 'ip_many_users' ? `(${anomalyData.total_count})` : ''}`,
              children: (
                <DataTable
                  columns={columns}
                  data={anomalyData?.data || []}
                  loading={isLoading}
                  showCard={false}
                  emptyText="未检测到同IP多账号异常"
                />
              ),
            },
            {
              key: 'big_request',
              label: `超大请求 ${anomalyData?.rule === 'big_request' ? `(${anomalyData.total_count})` : ''}`,
              children: (
                <DataTable
                  columns={columns}
                  data={anomalyData?.data || []}
                  loading={isLoading}
                  showCard={false}
                  emptyText="未检测到超大请求异常"
                />
              ),
            },
          ]}
        />
      </Card>

      {/* 详情弹窗 */}
      <Modal
        title={`${getRuleLabel(activeRule)}异常详情`}
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={null}
        width={800}
      >
        {renderDetailContent()}
      </Modal>
    </Space>
  );
};

export default Anomalies;
