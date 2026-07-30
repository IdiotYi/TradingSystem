import React from 'react'
import { Table, Tag } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { FundEvent } from '../../types/fund'

interface Props {
  events: FundEvent[]
}

type FundEventRow = FundEvent & { key: string }

const EMPTY_VALUE = <span style={{ color: '#555' }}>—</span>

const formatCny = (value: number) =>
  `¥${value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
const formatNav = (value: number) => `¥${value.toFixed(4)}`
const formatShares = (value: number) =>
  value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
const formatSignedShares = (value: number) => `${value >= 0 ? '+' : ''}${formatShares(value)}`

function getEventTypeTag(event: FundEvent) {
  switch (event.event_type) {
    case 'investment':
      return <Tag color="red">定投</Tag>
    case 'dividend':
      return <Tag color="blue">分红再投</Tag>
    case 'split':
      return <Tag color="purple">份额折算</Tag>
    default: {
      const exhaustive: never = event
      return exhaustive
    }
  }
}

function getScheduledDate(event: FundEvent) {
  switch (event.event_type) {
    case 'investment':
      return event.scheduled_date
    case 'dividend':
    case 'split':
      return EMPTY_VALUE
    default: {
      const exhaustive: never = event
      return exhaustive
    }
  }
}

function getNav(event: FundEvent) {
  switch (event.event_type) {
    case 'investment':
      return formatNav(event.nav)
    case 'dividend':
    case 'split':
      return EMPTY_VALUE
    default: {
      const exhaustive: never = event
      return exhaustive
    }
  }
}

function getCashAmount(event: FundEvent) {
  switch (event.event_type) {
    case 'investment':
      return formatCny(event.amount)
    case 'dividend':
      return formatCny(event.dividend_cash)
    case 'split':
      return EMPTY_VALUE
    default: {
      const exhaustive: never = event
      return exhaustive
    }
  }
}

function getAdjustedShares(event: FundEvent) {
  switch (event.event_type) {
    case 'investment':
    case 'dividend':
      return formatShares(event.acquired_shares)
    case 'split':
      return formatSignedShares(event.shares_after - event.shares_before)
    default: {
      const exhaustive: never = event
      return exhaustive
    }
  }
}

function getNote(event: FundEvent) {
  switch (event.event_type) {
    case 'investment':
      return event.advanced ? '因缺少目标交易日净值，提前至最近交易日执行' : '按计划定投'
    case 'dividend':
      return `每份分红 ${formatNav(event.dividend_per_share)}，红利再投`
    case 'split':
      return `${event.split_type || '份额折算'} ×${event.split_ratio.toFixed(4)}`
    default: {
      const exhaustive: never = event
      return exhaustive
    }
  }
}

const FundEventTable: React.FC<Props> = ({ events }) => {
  const columns: ColumnsType<FundEventRow> = [
    { title: '日期', dataIndex: 'date', key: 'date', width: 110, fixed: 'left' as const },
    {
      title: '事件类型',
      dataIndex: 'event_type',
      key: 'event_type',
      width: 110,
      render: (_, record) => getEventTypeTag(record),
    },
    {
      title: '计划日期',
      dataIndex: 'scheduled_date',
      key: 'scheduled_date',
      width: 120,
      render: (_, record) => getScheduledDate(record),
    },
    {
      title: '净值',
      dataIndex: 'nav',
      key: 'nav',
      width: 100,
      align: 'right' as const,
      render: (_, record) => getNav(record),
    },
    {
      title: '金额/分红现金',
      dataIndex: 'amount',
      key: 'amount',
      width: 130,
      align: 'right' as const,
      render: (_, record) => getCashAmount(record),
    },
    {
      title: '获得/调整份额',
      dataIndex: 'acquired_shares',
      key: 'acquired_shares',
      width: 130,
      align: 'right' as const,
      render: (_, record) => getAdjustedShares(record),
    },
    {
      title: '份额结余',
      dataIndex: 'shares_after',
      key: 'shares_after',
      width: 130,
      align: 'right' as const,
      render: (value: number) => formatShares(value),
    },
    {
      title: '说明',
      dataIndex: 'note',
      key: 'note',
      width: 280,
      render: (_, record) => <span className="fund-event-note">{getNote(record)}</span>,
    },
  ]

  return (
    <Table
      columns={columns}
      dataSource={events.map((event, index) => ({ ...event, key: `${event.event_type}-${event.date}-${index}` }))}
      size="small"
      scroll={{ x: 1180 }}
      pagination={false}
      style={{ background: '#161b22' }}
    />
  )
}

export default FundEventTable
