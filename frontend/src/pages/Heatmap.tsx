/**
 * 热力图页面
 */
import React, { useState, useMemo } from 'react';
import { Card, Space, message, Segmented } from 'antd';
import { useQuery } from '@tanstack/react-query';
import dayjs from 'dayjs';
import * as echarts from 'echarts';

import Chart from '@/components/Chart';
import RangeFilter, { TimeRange } from '@/components/RangeFilter';
import { getSeries, Metric } from '@/api/stats';

const Heatmap: React.FC = () => {
  // 状态管理
  const [timeRange, setTimeRange] = useState<TimeRange>({
    start: dayjs().subtract(7, 'day').valueOf(),
    end: dayjs().valueOf(),
  });
  const [metric, setMetric] = useState<Metric>('reqs');

  // 获取时序数据（1小时粒度）
  const {
    data: seriesData,
    isLoading,
    refetch,
    error,
  } = useQuery({
    queryKey: ['heatmap', timeRange.start, timeRange.end],
    queryFn: () => getSeries({
      start_ms: timeRange.start,
      end_ms: timeRange.end,
      slot_sec: 3600, // 1小时粒度
    }),
  });

  // 生成热力图数据
  const heatmapData = useMemo(() => {
    if (!seriesData?.data) {
      return {
        data: [] as [number, number, number][],
        hours: ['00', '01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11',
                '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23'],
        days: ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
      };
    }

    const data: [number, number, number][] = [];
    const hours = ['00', '01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11',
                   '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23'];
    const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];

    seriesData.data.forEach((item: any) => {
      const date = dayjs(item.bucket);
      const hour = date.hour();
      const day = date.day();
      const value = item[metric as keyof typeof item] as number;

      data.push([hour, day, value]);
    });

    return { data, hours, days };
  }, [seriesData, metric]);

  // 热力图配置
  const chartOption: echarts.EChartsOption = useMemo(() => {
    if (!heatmapData.data.length) return {};

    const maxValue = Math.max(...heatmapData.data.map(item => item[2]));

    return {
      title: {
        text: `${metric === 'reqs' ? '请求数' : metric === 'tokens' ? 'Token数' : '用户数'}热力图`,
        left: 'center',
      },
      tooltip: {
        position: 'top',
        formatter: (params: any) => {
          const hour = heatmapData.hours[params.data[0]];
          const day = heatmapData.days[params.data[1]];
          const value = params.data[2];
          return `${day} ${hour}:00<br/>${metric === 'reqs' ? '请求数' : metric === 'tokens' ? 'Token数' : '用户数'}: ${value.toLocaleString()}`;
        },
      },
      grid: {
        height: '50%',
        top: '10%',
      },
      xAxis: {
        type: 'category',
        data: heatmapData.hours,
        splitArea: {
          show: true,
        },
        axisLabel: {
          formatter: (value: string) => `${value}:00`,
        },
      },
      yAxis: {
        type: 'category',
        data: heatmapData.days,
        splitArea: {
          show: true,
        },
      },
      visualMap: {
        min: 0,
        max: maxValue,
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: '15%',
        inRange: {
          color: ['#313695', '#4575b4', '#74add1', '#abd9e9', '#e0f3f8', '#ffffcc', '#fee090', '#fdae61', '#f46d43', '#d73027', '#a50026'],
        },
      },
      series: [
        {
          name: metric === 'reqs' ? '请求数' : metric === 'tokens' ? 'Token数' : '用户数',
          type: 'heatmap',
          data: heatmapData.data,
          label: {
            show: false,
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowColor: 'rgba(0, 0, 0, 0.5)',
            },
          },
        },
      ],
    };
  }, [heatmapData, metric]);

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
        loading={isLoading}
        showExport={false}
        extraFilters={
          <Space>
            <span>指标:</span>
            <Segmented
              options={[
                { label: '请求数', value: 'reqs' },
                { label: 'Token数', value: 'tokens' },
                { label: '用户数', value: 'users' },
              ]}
              value={metric}
              onChange={(value) => setMetric(value as Metric)}
            />
          </Space>
        }
      />

      {/* 热力图 */}
      <Card title="时间热力图" loading={isLoading}>
        <div style={{ textAlign: 'center', marginBottom: 16, color: '#666' }}>
          横轴为小时，纵轴为星期，颜色深浅表示数值大小
        </div>
        <Chart
          option={chartOption}
          style={{ height: 500 }}
          loading={isLoading}
        />
      </Card>
    </Space>
  );
};

export default Heatmap;
