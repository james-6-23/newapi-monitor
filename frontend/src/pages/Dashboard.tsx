/**
 * Dashboard总览页面
 */
import React, { useState, useMemo } from 'react';
import { Card, Row, Col, Space, message } from 'antd';
import { useQuery } from '@tanstack/react-query';
import dayjs from 'dayjs';
import * as echarts from 'echarts';

import Chart from '@/components/Chart';
import KPICard, { KPIItem } from '@/components/KPICard';
import RangeFilter, { TimeRange } from '@/components/RangeFilter';
import { getSeries, exportCsv, SeriesDataPoint } from '@/api/stats';

const Dashboard: React.FC = () => {
  // 时间范围状态
  const [timeRange, setTimeRange] = useState<TimeRange>({
    start: dayjs().subtract(24, 'hour').valueOf(),
    end: dayjs().valueOf(),
  });

  // 时间粒度（根据时间范围自动调整）
  const slotSec = useMemo(() => {
    const duration = timeRange.end - timeRange.start;
    const hours = duration / (1000 * 60 * 60);
    
    if (hours <= 6) return 300; // 5分钟
    if (hours <= 24) return 900; // 15分钟
    if (hours <= 168) return 3600; // 1小时
    return 14400; // 4小时
  }, [timeRange]);

  // 获取时序数据
  const {
    data: seriesData,
    isLoading,
    refetch,
    error,
  } = useQuery({
    queryKey: ['series', timeRange.start, timeRange.end, slotSec],
    queryFn: () => getSeries({
      start_ms: timeRange.start,
      end_ms: timeRange.end,
      slot_sec: slotSec,
    }),
    refetchInterval: 30000, // 30秒自动刷新
  });

  // 计算KPI指标
  const kpiItems: KPIItem[] = useMemo(() => {
    if (!seriesData?.data) {
      return [
        { title: '总请求数', value: 0, color: '#1890ff' },
        { title: '总Token数', value: 0, color: '#52c41a' },
        { title: '活跃用户数', value: 0, color: '#faad14' },
        { title: 'Token种类数', value: 0, color: '#722ed1' },
      ];
    }

    const totals = seriesData.data.reduce(
      (acc, item) => ({
        reqs: acc.reqs + item.reqs,
        tokens: acc.tokens + item.tokens,
        users: Math.max(acc.users, item.users),
        tokens_cnt: Math.max(acc.tokens_cnt, item.tokens_cnt),
      }),
      { reqs: 0, tokens: 0, users: 0, tokens_cnt: 0 }
    );

    return [
      {
        title: '总请求数',
        value: totals.reqs,
        color: '#1890ff',
        description: '时间范围内的总请求数量',
      },
      {
        title: '总Token数',
        value: totals.tokens,
        color: '#52c41a',
        description: '时间范围内消耗的总Token数量',
      },
      {
        title: '峰值用户数',
        value: totals.users,
        color: '#faad14',
        description: '单个时间段内的最大活跃用户数',
      },
      {
        title: '峰值Token种类',
        value: totals.tokens_cnt,
        color: '#722ed1',
        description: '单个时间段内的最大Token种类数',
      },
    ];
  }, [seriesData]);

  // 生成图表配置
  const chartOption: echarts.EChartsOption = useMemo(() => {
    if (!seriesData?.data) {
      return {};
    }

    const data = seriesData.data;

    return {
      title: {
        text: '流量趋势',
        left: 'left',
        textStyle: {
          fontSize: 16,
          fontWeight: 'normal',
        },
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
        },
        formatter: (params: any) => {
          const time = dayjs(params[0].axisValue).format('YYYY-MM-DD HH:mm');
          let content = `<div style="margin-bottom: 4px;">${time}</div>`;
          
          params.forEach((param: any) => {
            const color = param.color;
            const name = param.seriesName;
            const value = param.value;
            content += `<div style="margin: 2px 0;">
              <span style="display:inline-block;margin-right:5px;border-radius:10px;width:10px;height:10px;background-color:${color};"></span>
              ${name}: <strong>${value.toLocaleString()}</strong>
            </div>`;
          });
          
          return content;
        },
      },
      legend: {
        data: ['请求数', 'Token数', '用户数'],
        top: 30,
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: 80,
        containLabel: true,
      },
      xAxis: {
        type: 'time',
        boundaryGap: false,
        axisLabel: {
          formatter: (value: number) => {
            return dayjs(value).format('HH:mm');
          },
        },
      },
      yAxis: [
        {
          type: 'value',
          name: '请求数/用户数',
          position: 'left',
          axisLabel: {
            formatter: '{value}',
          },
        },
        {
          type: 'value',
          name: 'Token数',
          position: 'right',
          axisLabel: {
            formatter: '{value}',
          },
        },
      ],
      series: [
        {
          name: '请求数',
          type: 'line',
          yAxisIndex: 0,
          data: data.map(item => [item.bucket, item.reqs]),
          smooth: true,
          symbol: 'circle',
          symbolSize: 4,
          lineStyle: {
            width: 2,
          },
          areaStyle: {
            opacity: 0.1,
          },
        },
        {
          name: 'Token数',
          type: 'line',
          yAxisIndex: 1,
          data: data.map(item => [item.bucket, item.tokens]),
          smooth: true,
          symbol: 'circle',
          symbolSize: 4,
          lineStyle: {
            width: 2,
          },
        },
        {
          name: '用户数',
          type: 'line',
          yAxisIndex: 0,
          data: data.map(item => [item.bucket, item.users]),
          smooth: true,
          symbol: 'circle',
          symbolSize: 4,
          lineStyle: {
            width: 2,
          },
        },
      ],
    };
  }, [seriesData]);

  // 处理导出
  const handleExport = async () => {
    try {
      const blob = await exportCsv({
        query_type: 'series',
        start_ms: timeRange.start,
        end_ms: timeRange.end,
      });
      
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `dashboard_${dayjs(timeRange.start).format('YYYYMMDD')}_${dayjs(timeRange.end).format('YYYYMMDD')}.csv`;
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

      {/* KPI指标 */}
      <KPICard items={kpiItems} loading={isLoading} />

      {/* 趋势图表 */}
      <Card title="流量趋势" loading={isLoading}>
        <Chart
          option={chartOption}
          style={{ height: 400 }}
          loading={isLoading}
        />
      </Card>
    </Space>
  );
};

export default Dashboard;
