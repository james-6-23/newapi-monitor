/**
 * 通用数据表格组件
 */
import React from 'react';
import { Table, Card, Empty, Typography } from 'antd';
import type { ColumnsType, TableProps } from 'antd/es/table';

const { Title } = Typography;

export interface DataTableProps<T = any> extends Omit<TableProps<T>, 'columns'> {
  title?: string;
  columns: ColumnsType<T>;
  data?: T[];
  loading?: boolean;
  showCard?: boolean;
  emptyText?: string;
  extra?: React.ReactNode;
}

function DataTable<T extends Record<string, any>>({
  title,
  columns,
  data = [],
  loading = false,
  showCard = true,
  emptyText = '暂无数据',
  extra,
  ...tableProps
}: DataTableProps<T>) {
  const tableElement = (
    <Table
      columns={columns}
      dataSource={data}
      loading={loading}
      pagination={{
        showSizeChanger: true,
        showQuickJumper: true,
        showTotal: (total, range) =>
          `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
        ...tableProps.pagination,
      }}
      locale={{
        emptyText: <Empty description={emptyText} />,
      }}
      scroll={{ x: 'max-content' }}
      {...tableProps}
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
