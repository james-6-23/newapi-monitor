/**
 * Top排行页面
 */
import React, { useState, useMemo } from 'react';
import { Card, Row, Col, Segmented, Space, message } from 'antd';
import { useQuery } from '@tanstack/react-query';
import dayjs from 'dayjs';
import * as echarts from 'echarts';

import Chart from '@/components/Chart';
import DataTable from '@/components/DataTable';
import RangeFilter, { TimeRange } from '@/components/RangeFilter';
import { getTop, exportCsv, TopBy, Metric, getByLabel, getMetricLabel, formatNumber, formatQuota } from '@/api/stats';

const Top: React.FC = () => {
  // 状态管理
  const [timeRange, setTimeRange] = useState<TimeRange>({
    start: dayjs().subtract(24, 'hour').valueOf(),
    end: dayjs().valueOf(),
  });
  const [by, setBy] = useState<TopBy>('user');
  const [metric, setMetric] = useState<Metric>('tokens');

  // 获取Top数据
  const {
    data: topData,
    isLoading,
    refetch,
    error,
  } = useQuery({
    queryKey: ['top', timeRange.start, timeRange.end, by, metric],
    queryFn: () => getTop({
      start_ms: timeRange.start,
      end_ms: timeRange.end,
      by,
      metric,
      limit: 50,
    }),
  });

  // 图表配置
  const chartOption: echarts.EChartsOption = useMemo(() => {
    if (!topData?.data) return {};

    const data = topData.data.slice(0, 20); // 只显示前20名

    return {
      title: {
        text: `Top 20 ${getByLabel(by)} - ${getMetricLabel(metric)}`,
        left: 'center',
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow',
        },
        formatter: (params: any) => {
          const item = params[0];
          const dataItem = data[item.dataIndex];
          return `
            <div>
              <strong>${item.name}</strong><br/>
              ${getMetricLabel(metric)}: <strong>${formatNumber(item.value)}</strong><br/>
              请求数: ${formatNumber(dataItem.reqs)}<br/>
              Token数: ${formatNumber(dataItem.tokens)}<br/>
              配额: ${formatQuota(dataItem.quota_sum)}
            </div>
          `;
        },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        top: '10%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: data.map((item: any) => {
          if (by === 'user') return item.username || `用户${item.user_id}`;
          if (by === 'token') return item.token_name || `Token${item.token_id}`;
          if (by === 'model') return item.model_name;
          if (by === 'channel') return item.channel_name || `通道${item.channel_id}`;
          return '';
        }),
        axisLabel: {
          rotate: 45,
          interval: 0,
        },
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          formatter: (value: number) => formatNumber(value),
        },
      },
      series: [
        {
          type: 'bar',
          data: data.map((item: any) => item[metric]),
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#83bff6' },
              { offset: 0.5, color: '#188df0' },
              { offset: 1, color: '#188df0' },
            ]),
          },
          emphasis: {
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: '#2378f7' },
                { offset: 0.7, color: '#2378f7' },
                { offset: 1, color: '#83bff6' },
              ]),
            },
          },
        },
      ],
    };
  }, [topData, by, metric]);

  // 表格列配置
  const columns = useMemo(() => {
    const baseColumns = [
      {
        title: '排名',
        key: 'rank',
        width: 80,
        render: (_: any, __: any, index: number) => index + 1,
      },
    ];

    if (by === 'user') {
      baseColumns.push({
        title: '用户',
        key: 'user',
        render: (record: any) => record.username || `用户${record.user_id}`,
      });
    } else if (by === 'token') {
      baseColumns.push({
        title: 'Token',
        key: 'token',
        render: (record: any) => record.token_name || `Token${record.token_id}`,
      });
    } else if (by === 'model') {
      baseColumns.push({
        title: '模型',
        dataIndex: 'model_name',
        key: 'model_name',
      });
    } else if (by === 'channel') {
      baseColumns.push({
        title: '通道',
        key: 'channel',
        render: (record: any) => record.channel_name || `通道${record.channel_id}`,
      });
    }

    baseColumns.push(
      {
        title: '请求数',
        dataIndex: 'reqs',
        key: 'reqs',
        render: (value: number) => formatNumber(value),
        sorter: (a: any, b: any) => a.reqs - b.reqs,
      },
      {
        title: 'Token数',
        dataIndex: 'tokens',
        key: 'tokens',
        render: (value: number) => formatNumber(value),
        sorter: (a: any, b: any) => a.tokens - b.tokens,
      },
      {
        title: '配额消耗',
        dataIndex: 'quota_sum',
        key: 'quota_sum',
        render: (value: number) => formatQuota(value),
        sorter: (a: any, b: any) => a.quota_sum - b.quota_sum,
      }
    );

    return baseColumns;
  }, [by]);

  // 处理导出
  const handleExport = async () => {
    try {
      const blob = await exportCsv({
        query_type: 'top',
        start_ms: timeRange.start,
        end_ms: timeRange.end,
        by,
        metric,
      });
      
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `top_${by}_${metric}_${dayjs().format('YYYYMMDD_HHmmss')}.csv`;
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
        extraFilters={
          <Space>
            <span>维度:</span>
            <Segmented
              options={[
                { label: '用户', value: 'user' },
                { label: 'Token', value: 'token' },
                { label: '模型', value: 'model' },
                { label: '通道', value: 'channel' },
              ]}
              value={by}
              onChange={(value) => setBy(value as TopBy)}
            />
            <span>指标:</span>
            <Segmented
              options={[
                { label: 'Token数', value: 'tokens' },
                { label: '请求数', value: 'reqs' },
                { label: '配额', value: 'quota_sum' },
              ]}
              value={metric}
              onChange={(value) => setMetric(value as Metric)}
            />
          </Space>
        }
      />

      <Row gutter={[16, 16]}>
        {/* 图表 */}
        <Col span={24} lg={12}>
          <Card title="Top排行图表" loading={isLoading}>
            <Chart
              option={chartOption}
              style={{ height: 400 }}
              loading={isLoading}
            />
          </Card>
        </Col>

        {/* 表格 */}
        <Col span={24} lg={12}>
          <DataTable
            title="详细排行"
            columns={columns}
            data={topData?.data || []}
            loading={isLoading}
            pagination={{
              pageSize: 20,
              showSizeChanger: false,
            }}
          />
        </Col>
      </Row>
    </Space>
  );
};

export default Top;
