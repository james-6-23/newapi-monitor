/**
 * KPI指标卡片组件
 */
import React from 'react';
import { Card, Statistic, Row, Col, Tooltip } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { formatNumber } from '@/api/stats';

export interface KPIItem {
  title: string;
  value: number;
  suffix?: string;
  prefix?: string;
  precision?: number;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  description?: string;
  color?: string;
}

interface KPICardProps {
  title?: string;
  items: KPIItem[];
  loading?: boolean;
  span?: number;
}

const KPICard: React.FC<KPICardProps> = ({
  title,
  items,
  loading = false,
  span = 6,
}) => {
  const renderKPIItem = (item: KPIItem, index: number) => {
    const {
      title: itemTitle,
      value,
      suffix,
      prefix,
      precision = 0,
      trend,
      description,
      color = '#1890ff',
    } = item;

    const formattedValue = typeof value === 'number' ? formatNumber(value) : value;

    const statisticElement = (
      <Statistic
        title={itemTitle}
        value={formattedValue}
        suffix={suffix}
        prefix={prefix}
        precision={precision}
        valueStyle={{ color }}
        loading={loading}
      />
    );

    return (
      <Col span={span} key={index}>
        <Card
          className="kpi-card"
          style={{
            textAlign: 'center',
            height: '100%',
          }}
          bodyStyle={{ padding: '20px 16px' }}
        >
          {description ? (
            <Tooltip title={description}>
              <div style={{ position: 'relative' }}>
                {statisticElement}
                <InfoCircleOutlined
                  style={{
                    position: 'absolute',
                    top: 0,
                    right: 0,
                    color: '#999',
                    fontSize: 12,
                  }}
                />
              </div>
            </Tooltip>
          ) : (
            statisticElement
          )}

          {/* 趋势指示器 */}
          {trend && (
            <div style={{ marginTop: 8 }}>
              <span
                style={{
                  color: trend.isPositive ? '#52c41a' : '#ff4d4f',
                  fontSize: 12,
                }}
              >
                {trend.isPositive ? (
                  <ArrowUpOutlined />
                ) : (
                  <ArrowDownOutlined />
                )}
                {' '}
                {Math.abs(trend.value).toFixed(1)}%
              </span>
              <span style={{ color: '#999', fontSize: 12, marginLeft: 4 }}>
                vs 上期
              </span>
            </div>
          )}
        </Card>
      </Col>
    );
  };

  if (title) {
    return (
      <Card title={title} loading={loading}>
        <Row gutter={[16, 16]}>
          {items.map(renderKPIItem)}
        </Row>
      </Card>
    );
  }

  return (
    <Row gutter={[16, 16]}>
      {items.map(renderKPIItem)}
    </Row>
  );
};

export default KPICard;
