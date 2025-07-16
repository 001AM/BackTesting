import React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { TrendingUp, TrendingDown, Activity, Target, Shield, Zap } from "lucide-react"

const metrics = [
  {
    title: "CAGR",
    value: "18.2%",
    change: "+2.1%",
    trend: "up",
    icon: TrendingUp,
    description: "Compound Annual Growth Rate",
  },
  {
    title: "Total Returns",
    value: "170.0%",
    change: "+15.2%",
    trend: "up",
    icon: Target,
    description: "Total portfolio returns",
  },
  {
    title: "Sharpe Ratio",
    value: "1.34",
    change: "+0.12",
    trend: "up",
    icon: Activity,
    description: "Risk-adjusted returns",
  },
  {
    title: "Max Drawdown",
    value: "-8.5%",
    change: "-1.2%",
    trend: "down",
    icon: TrendingDown,
    description: "Maximum peak-to-trough decline",
  },
  {
    title: "Volatility",
    value: "16.8%",
    change: "-0.8%",
    trend: "down",
    icon: Zap,
    description: "Standard deviation of returns",
  },
  {
    title: "Win Rate",
    value: "68.4%",
    change: "+3.2%",
    trend: "up",
    icon: Shield,
    description: "Percentage of profitable trades",
  },
]

export default function MetricsGrid() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {metrics.map((metric) => {
        const Icon = metric.icon
        return (
          <Card key={metric.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{metric.title}</CardTitle>
              <Icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metric.value}</div>
              <div className="flex items-center space-x-2 text-xs text-muted-foreground">
                <span className={`flex items-center ${metric.trend === "up" ? "text-green-600" : "text-red-600"}`}>
                  {metric.trend === "up" ? (
                    <TrendingUp className="w-3 h-3 mr-1" />
                  ) : (
                    <TrendingDown className="w-3 h-3 mr-1" />
                  )}
                  {metric.change}
                </span>
                <span>vs benchmark</span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">{metric.description}</p>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
