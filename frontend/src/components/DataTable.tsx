/**
 * 通用数据表格组件
 */
import React from 'react';
import { Table, Card, Empty, Typography } from 'antd';
import type { ColumnsType, TableProps } from 'antd/es/table';

const { Title } = Typography;

export interface DataTableProps<T = any> {
  title?: string;
  columns: ColumnsType<T>;
  data?: T[];
  loading?: boolean;
  showCard?: boolean;
  emptyText?: string;
  extra?: React.ReactNode;
  pagination?: TableProps<T>['pagination'];
  scroll?: TableProps<T>['scroll'];
  size?: TableProps<T>['size'];
  bordered?: boolean;
  rowKey?: TableProps<T>['rowKey'];
}

function DataTable<T extends Record<string, any>>({
  title,
  columns,
  data = [],
  loading = false,
  showCard = true,
  emptyText = '暂无数据',
  extra,
  pagination,
  scroll,
  size,
  bordered,
  rowKey,
}: DataTableProps<T>) {
  const tableElement = (
    <Table
      columns={columns}
      dataSource={data}
      loading={loading}
      pagination={pagination !== false ? {
        showSizeChanger: true,
        showQuickJumper: true,
        showTotal: (total, range) =>
          `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
        ...pagination,
      } : false}
      locale={{
        emptyText: <Empty description={emptyText} />,
      }}
      scroll={scroll || { x: 'max-content' }}
      size={size}
      bordered={bordered}
      rowKey={rowKey}
    />
  );

  if (showCard) {
    return (
      <Card
        title={title && <Title level={4} style={{ margin: 0 }}>{title}</Title>}
        extra={extra}
        className="data-table"
      >
        {tableElement}
      </Card>
    );
  }

  return tableElement;
}

export default DataTable;
