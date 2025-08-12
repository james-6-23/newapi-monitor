/**
 * 时间范围筛选组件
 */
import React from 'react';
import { Card, DatePicker, Select, Space, Button, Tooltip } from 'antd';
import { ReloadOutlined, DownloadOutlined } from '@ant-design/icons';
import dayjs, { Dayjs } from 'dayjs';

const { RangePicker } = DatePicker;
const { Option } = Select;

export interface TimeRange {
  start: number;
  end: number;
}

export interface RangeFilterProps {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
  onRefresh?: () => void;
  onExport?: () => void;
  loading?: boolean;
  showExport?: boolean;
  showRefresh?: boolean;
  extraFilters?: React.ReactNode;
}

// 预设时间范围
const PRESET_RANGES = [
  {
    label: '最近1小时',
    value: 'last_1h',
    getRange: () => ({
      start: dayjs().subtract(1, 'hour').valueOf(),
      end: dayjs().valueOf(),
    }),
  },
  {
    label: '最近6小时',
    value: 'last_6h',
    getRange: () => ({
      start: dayjs().subtract(6, 'hour').valueOf(),
      end: dayjs().valueOf(),
    }),
  },
  {
    label: '最近24小时',
    value: 'last_24h',
    getRange: () => ({
      start: dayjs().subtract(24, 'hour').valueOf(),
      end: dayjs().valueOf(),
    }),
  },
  {
    label: '最近7天',
    value: 'last_7d',
    getRange: () => ({
      start: dayjs().subtract(7, 'day').valueOf(),
      end: dayjs().valueOf(),
    }),
  },
  {
    label: '最近30天',
    value: 'last_30d',
    getRange: () => ({
      start: dayjs().subtract(30, 'day').valueOf(),
      end: dayjs().valueOf(),
    }),
  },
];

const RangeFilter: React.FC<RangeFilterProps> = ({
  value,
  onChange,
  onRefresh,
  onExport,
  loading = false,
  showExport = true,
  showRefresh = true,
  extraFilters,
}) => {
  const handlePresetChange = (presetValue: string) => {
    const preset = PRESET_RANGES.find(p => p.value === presetValue);
    if (preset) {
      onChange(preset.getRange());
    }
  };

  const handleDateRangeChange = (dates: [Dayjs | null, Dayjs | null] | null) => {
    if (dates && dates[0] && dates[1]) {
      onChange({
        start: dates[0].valueOf(),
        end: dates[1].valueOf(),
      });
    }
  };

  const getCurrentPreset = () => {
    const current = PRESET_RANGES.find(preset => {
      const range = preset.getRange();
      const timeDiff = Math.abs(range.start - value.start) + Math.abs(range.end - value.end);
      return timeDiff < 60000; // 允许1分钟的误差
    });
    return current?.value;
  };

  return (
    <Card className="filter-container" bodyStyle={{ padding: '16px' }}>
      <Space wrap size="middle">
        {/* 预设时间范围 */}
        <Space>
          <span>时间范围:</span>
          <Select
            style={{ width: 120 }}
            placeholder="选择范围"
            value={getCurrentPreset()}
            onChange={handlePresetChange}
            allowClear
          >
            {PRESET_RANGES.map(preset => (
              <Option key={preset.value} value={preset.value}>
                {preset.label}
              </Option>
            ))}
          </Select>
        </Space>

        {/* 自定义时间范围 */}
        <Space>
          <span>自定义:</span>
          <RangePicker
            showTime
            value={[dayjs(value.start), dayjs(value.end)]}
            onChange={handleDateRangeChange}
            format="YYYY-MM-DD HH:mm"
            placeholder={['开始时间', '结束时间']}
          />
        </Space>

        {/* 额外的筛选器 */}
        {extraFilters}

        {/* 操作按钮 */}
        <Space>
          {showRefresh && (
            <Tooltip title="刷新数据">
              <Button
                icon={<ReloadOutlined />}
                onClick={onRefresh}
                loading={loading}
              >
                刷新
              </Button>
            </Tooltip>
          )}

          {showExport && (
            <Tooltip title="导出数据">
              <Button
                icon={<DownloadOutlined />}
                onClick={onExport}
                disabled={loading}
              >
                导出
              </Button>
            </Tooltip>
          )}
        </Space>
      </Space>
    </Card>
  );
};

export default RangeFilter;
