import React from 'react'
import { Table, Tag } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { Trade } from '../../types/backtest'
import { detectPriceDecimals } from '../../utils/priceFormat'

interface Props { trades: Trade[] }

const fmtCny = (n: number) => `¥${n.toFixed(2)}`

const TradeTable: React.FC<Props> = ({ trades }) => {
  const priceDecimals = detectPriceDecimals(trades.map(t => t.price))
  const fmtPrice = (n: number) => `¥${n.toFixed(priceDecimals)}`

  const columns: ColumnsType<Trade & { key: number }> = [
    { title: '日期', dataIndex: 'date', key: 'date', width: 110, fixed: 'left' as const },
    {
      title: '方向', dataIndex: 'direction', key: 'direction', width: 70,
      render: (v: string) => <Tag color={v === '买入' ? 'red' : 'cyan'}>{v}</Tag>,
    },
    { title: '原因', dataIndex: 'reason', key: 'reason', width: 150 },
    { title: '价格', dataIndex: 'price', key: 'price', width: 90, render: fmtPrice },
    { title: '数量 (股)', dataIndex: 'shares', key: 'shares', width: 90, align: 'right' as const },
    { title: '成交金额', dataIndex: 'amount', key: 'amount', width: 110, render: fmtCny, align: 'right' as const },
    { title: '过户费', dataIndex: 'transfer_fee', key: 'transfer_fee', width: 90, render: fmtCny, align: 'right' as const },
    {
      title: '印花税', dataIndex: 'stamp_tax', key: 'stamp_tax', width: 90, align: 'right' as const,
      render: (v: number | null) => v == null ? <span style={{ color: '#555' }}>—</span> : fmtCny(v),
    },
    { title: '佣金', dataIndex: 'commission', key: 'commission', width: 90, render: fmtCny, align: 'right' as const },
    { title: '总手续费', dataIndex: 'total_fee', key: 'total_fee', width: 90, render: fmtCny, align: 'right' as const },
    {
      title: '盈亏', dataIndex: 'pnl', key: 'pnl', width: 100, align: 'right' as const,
      render: (v: number | null) => {
        if (v == null) return <span style={{ color: '#555' }}>—</span>
        return <span style={{ color: v >= 0 ? '#ef5350' : '#26a69a' }}>{fmtCny(v)}</span>
      },
    },
    { title: '剩余现金', dataIndex: 'remaining_cash', key: 'remaining_cash', width: 120, render: fmtCny, align: 'right' as const },
  ]

  const totalFees = trades.reduce((s, t) => s + t.total_fee, 0)
  const totalPnl = trades.filter(t => t.pnl != null).reduce((s, t) => s + (t.pnl ?? 0), 0)

  return (
    <Table
      columns={columns}
      dataSource={trades.map((t, i) => ({ ...t, key: i }))}
      size="small"
      scroll={{ x: 1200 }}
      pagination={false}
      style={{ background: '#161b22' }}
      summary={() => (
        <Table.Summary.Row>
          <Table.Summary.Cell index={0} colSpan={9} align="right">
            <b style={{ color: '#8b949e' }}>合计手续费</b>
          </Table.Summary.Cell>
          <Table.Summary.Cell index={1} align="right">
            <b style={{ color: '#fa8c16' }}>¥{totalFees.toFixed(2)}</b>
          </Table.Summary.Cell>
          <Table.Summary.Cell index={2} align="right">
            <b style={{ color: totalPnl >= 0 ? '#ef5350' : '#26a69a' }}>¥{totalPnl.toFixed(2)}</b>
          </Table.Summary.Cell>
          <Table.Summary.Cell index={3} />
        </Table.Summary.Row>
      )}
    />
  )
}

export default TradeTable
