import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { TrendingUp, TrendingDown, Activity, Target, Shield, Zap } from "lucide-react"

export default function MetricsGrid({ data }) {
  console.log(data,"==================1")
  console.log(data.compound_annual_growth_rate,"===============================")

  const metrics = [
    {
      title: "CAGR",
      value: `${data.compound_annual_growth_rate.toFixed(2)}%`,
      trend: "up",
      icon: TrendingUp,
      description: "Compound Annual Growth Rate",
    },
    {
      title: "Total Returns",
      value: `${data.total_return_percentage.toFixed(2)}%`,
      trend: "up",
      icon: Target,
      description: "Total portfolio returns",
    },
    {
      title: "Sharpe Ratio",
      value: data.sharpe_ratio.toFixed(2),
      trend: "up",
      icon: Activity,
      description: "Risk-adjusted returns",
    },
    {
      title: "Max Drawdown",
      value: `${data.max_drawdown.toFixed(2)}%`,
      trend: data.max_drawdown > -8.5 ? "up" : "down",
      icon: TrendingDown,
      description: "Maximum peak-to-trough decline",
    },
    {
      title: "Volatility",
      value: `${data.volatility.toFixed(2)}%`,
      trend: data.volatility < 16.8 ? "up" : "down",
      icon: Zap,
      description: "Standard deviation of returns",
    },
    {
      title: "Win Rate",
      value: `${(data.win_rate * 100).toFixed(2)}%`,
      trend: "up",
      icon: Shield,
      description: "Percentage of profitable periods",
    },
  ]
  console.log(metrics)

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
              <p className="text-xs text-muted-foreground mt-1">{metric.description}</p>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}