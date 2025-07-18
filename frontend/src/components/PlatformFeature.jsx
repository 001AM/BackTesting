import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { TrendingUp, Database, BarChart3, Settings, Download, GitBranch } from "lucide-react"
import { Link } from "react-router-dom";

function PlatformFeature() {
  return (
    <section className="py-16 bg-white">
        <div className="container mx-auto px-4">
          <h3 className="text-3xl font-bold text-center mb-12">Platform Features</h3>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            <Card>
              <CardHeader>
                <Settings className="h-10 w-10 text-blue-600 mb-2" />
                <CardTitle>Flexible Configuration</CardTitle>
                <CardDescription>
                  Configure rebalancing frequency, portfolio size, and position sizing methods
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li>• Quarterly, Yearly rebalancing</li>
                  <li>• Equal, Market-cap, Metric-weighted sizing</li>
                  <li>• Custom portfolio sizes</li>
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <Database className="h-10 w-10 text-green-600 mb-2" />
                <CardTitle>Comprehensive Data</CardTitle>
                <CardDescription>
                  100+ Indian listed companies with historical price and fundamental data
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li>• OHLCV price data</li>
                  <li>• P&L, Balance Sheet, Cash Flow</li>
                  <li>• Performance & valuation ratios</li>
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <BarChart3 className="h-10 w-10 text-purple-600 mb-2" />
                <CardTitle>Advanced Analytics</CardTitle>
                <CardDescription>Detailed performance metrics and visualization tools</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li>• Equity curves & drawdown charts</li>
                  <li>• CAGR, Sharpe ratio, Max drawdown</li>
                  <li>• Portfolio logs & attribution</li>
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <GitBranch className="h-10 w-10 text-orange-600 mb-2" />
                <CardTitle>Smart Filtering</CardTitle>
                <CardDescription>Apply market cap, profitability, and custom metric filters</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li>• Market cap range filtering</li>
                  <li>• ROCE, ROE, PAT thresholds</li>
                  <li>• Custom metric combinations</li>
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <TrendingUp className="h-10 w-10 text-red-600 mb-2" />
                <CardTitle>Ranking System</CardTitle>
                <CardDescription>Sort and rank stocks based on single or multiple metrics</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li>• Single metric ranking</li>
                  <li>• Composite ranking system</li>
                  <li>• Ascending/descending sorts</li>
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <Download className="h-10 w-10 text-indigo-600 mb-2" />
                <CardTitle>Export & Share</CardTitle>
                <CardDescription>Export results and share strategies with your team</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li>• CSV & Excel export</li>
                  <li>• Strategy comparison</li>
                  <li>• Benchmark analysis</li>
                </ul>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>
  )
}

export default PlatformFeature
