import React from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import PerformanceCharts from "@/components/PerformanceCharts"
import MetricsGrid from "@/components/MetricsGrid"
import PortfolioAnalytics from "@/components/PortfolioAnalytics"
import ExportSection from "@/components/ExportSection"
// import { AdvancedAnalytics } from "@/components/advanced-analytics"

export default function ResultsDashboard({data}) {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Backtest Results</h2>
        <ExportSection />
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="charts">Charts</TabsTrigger>
          <TabsTrigger value="portfolio">Portfolio</TabsTrigger>
          {/* <TabsTrigger value="analytics">Analytics</TabsTrigger> */}
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <MetricsGrid data={data}/>
          <PerformanceCharts equitydata={data.equity_curve} drawdown={data.drawdown_series}/>
        </TabsContent>

        <TabsContent value="charts" className="space-y-4">
          <PerformanceCharts equitydata={data.equity_curve} drawdown={data.drawdown_series}/>
        </TabsContent>

        <TabsContent value="portfolio" className="space-y-4">
          <PortfolioAnalytics portfolioData={data}/>
        </TabsContent>

        {/* <TabsContent value="analytics" className="space-y-4">
          <AdvancedAnalytics />
        </TabsContent> */}
      </Tabs>
    </div>
  )
}
