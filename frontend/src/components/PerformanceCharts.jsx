import React, { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from "recharts"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"

// Mock data for charts
const equityCurveData = [
  { date: "2020-01", portfolio: 1000000, nifty: 1000000 },
  { date: "2020-04", portfolio: 950000, nifty: 920000 },
  { date: "2020-07", portfolio: 1100000, nifty: 1050000 },
  { date: "2020-10", portfolio: 1250000, nifty: 1150000 },
  { date: "2021-01", portfolio: 1400000, nifty: 1280000 },
  { date: "2021-04", portfolio: 1350000, nifty: 1320000 },
  { date: "2021-07", portfolio: 1600000, nifty: 1450000 },
  { date: "2021-10", portfolio: 1750000, nifty: 1580000 },
  { date: "2022-01", portfolio: 1650000, nifty: 1520000 },
  { date: "2022-04", portfolio: 1800000, nifty: 1600000 },
  { date: "2022-07", portfolio: 1950000, nifty: 1720000 },
  { date: "2022-10", portfolio: 2100000, nifty: 1850000 },
  { date: "2023-01", portfolio: 2250000, nifty: 1980000 },
  { date: "2023-04", portfolio: 2400000, nifty: 2100000 },
  { date: "2023-07", portfolio: 2550000, nifty: 2220000 },
  { date: "2023-10", portfolio: 2700000, nifty: 2350000 },
]

const drawdownData = [
  { date: "2020-01", drawdown: 0 },
  { date: "2020-04", drawdown: -5 },
  { date: "2020-07", drawdown: 0 },
  { date: "2020-10", drawdown: 0 },
  { date: "2021-01", drawdown: 0 },
  { date: "2021-04", drawdown: -3.6 },
  { date: "2021-07", drawdown: 0 },
  { date: "2021-10", drawdown: 0 },
  { date: "2022-01", drawdown: -5.7 },
  { date: "2022-04", drawdown: 0 },
  { date: "2022-07", drawdown: 0 },
  { date: "2022-10", drawdown: 0 },
  { date: "2023-01", drawdown: 0 },
  { date: "2023-04", drawdown: 0 },
  { date: "2023-07", drawdown: 0 },
  { date: "2023-10", drawdown: 0 },
]

export default function PerformanceCharts() {
  const [showBenchmark, setShowBenchmark] = useState(true)

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Equity Curve */}
      <Card className="lg:col-span-2">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Equity Curve</CardTitle>
            <div className="flex items-center space-x-2">
              <Switch id="benchmark" checked={showBenchmark} onCheckedChange={setShowBenchmark} />
              <Label htmlFor="benchmark" className="text-sm">
                Show Nifty 50
              </Label>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={equityCurveData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis tickFormatter={(value) => `₹${(value / 100000).toFixed(0)}L`} />
              <Tooltip
                formatter={(value) => [`₹${(value / 100000).toFixed(1)}L`, ""]}
                labelFormatter={(label) => `Date: ${label}`}
              />
              <Line type="monotone" dataKey="portfolio" stroke="#2563eb" strokeWidth={2} name="Portfolio" />
              {showBenchmark && (
                <Line
                  type="monotone"
                  dataKey="nifty"
                  stroke="#dc2626"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  name="Nifty 50"
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Drawdown Chart */}
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle>Drawdown Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={drawdownData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis tickFormatter={(value) => `${value}%`} />
              <Tooltip
                formatter={(value) => [`${value}%`, "Drawdown"]}
                labelFormatter={(label) => `Date: ${label}`}
              />
              <Area type="monotone" dataKey="drawdown" stroke="#dc2626" fill="#dc2626" fillOpacity={0.3} />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  )
}
