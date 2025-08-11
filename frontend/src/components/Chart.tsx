/**
 * 通用ECharts图表组件
 */
import React, { useEffect, useRef, useImperativeHandle, forwardRef } from 'react';
import * as echarts from 'echarts';
import { Spin } from 'antd';

export interface ChartProps {
  option: echarts.EChartsOption;
  style?: React.CSSProperties;
  className?: string;
  loading?: boolean;
  theme?: string;
  onChartReady?: (chart: echarts.ECharts) => void;
  onEvents?: Record<string, (params: any) => void>;
}

export interface ChartRef {
  getChart: () => echarts.ECharts | null;
  resize: () => void;
}

const Chart = forwardRef<ChartRef, ChartProps>(({
  option,
  style,
  className,
  loading = false,
  theme,
  onChartReady,
  onEvents,
}, ref) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<echarts.ECharts | null>(null);

  // 暴露给父组件的方法
  useImperativeHandle(ref, () => ({
    getChart: () => chartInstanceRef.current,
    resize: () => {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.resize();
      }
    },
  }));

  // 初始化图表
  useEffect(() => {
    if (!chartRef.current) return;

    // 创建图表实例
    const chart = echarts.init(chartRef.current, theme);
    chartInstanceRef.current = chart;

    // 绑定事件
    if (onEvents) {
      Object.entries(onEvents).forEach(([eventName, handler]) => {
        chart.on(eventName, handler);
      });
    }

    // 通知父组件图表已准备好
    if (onChartReady) {
      onChartReady(chart);
    }

    // 窗口大小变化时重新调整图表大小
    const handleResize = () => {
      chart.resize();
    };

    window.addEventListener('resize', handleResize);

    // 清理函数
    return () => {
      window.removeEventListener('resize', handleResize);
      
      // 解绑事件
      if (onEvents) {
        Object.keys(onEvents).forEach(eventName => {
          chart.off(eventName);
        });
      }
      
      chart.dispose();
      chartInstanceRef.current = null;
    };
  }, [theme, onChartReady, onEvents]);

  // 更新图表配置
  useEffect(() => {
    if (chartInstanceRef.current && option) {
      chartInstanceRef.current.setOption(option, true);
    }
  }, [option]);

  // 处理加载状态
  useEffect(() => {
    if (chartInstanceRef.current) {
      if (loading) {
        chartInstanceRef.current.showLoading('default', {
          text: '加载中...',
          color: '#1890ff',
          textColor: '#000',
          maskColor: 'rgba(255, 255, 255, 0.8)',
          zlevel: 0,
        });
      } else {
        chartInstanceRef.current.hideLoading();
      }
    }
  }, [loading]);

  const defaultStyle: React.CSSProperties = {
    width: '100%',
    height: '400px',
    ...style,
  };

  return (
    <div className={className} style={{ position: 'relative' }}>
      <div
        ref={chartRef}
        style={defaultStyle}
      />
      {loading && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'rgba(255, 255, 255, 0.8)',
            zIndex: 1000,
          }}
        >
          <Spin size="large" />
        </div>
      )}
    </div>
  );
});

Chart.displayName = 'Chart';

export default Chart;
