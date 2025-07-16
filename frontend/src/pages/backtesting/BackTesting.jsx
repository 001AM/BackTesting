"use client"

import { useState } from "react"
import { ConfigurationPanel } from "@/components/ConfigurationPanel"
import ResultsDashboard  from "@/components/ResultsDashboard"
import { Button } from "@/components/ui/button"
import { Play, Download } from "lucide-react"
import { Card } from "@/components/ui/card"

export default function BacktestingPlatform() {
  const [isRunning, setIsRunning] = useState(false)
  const [hasResults, setHasResults] = useState(false)

  const handleRunBacktest = async () => {
    setIsRunning(true)
    // Simulate backtest execution
    await new Promise((resolve) => setTimeout(resolve, 2000))
    setIsRunning(false)
    setHasResults(true)
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-6">
        {/* Top Controls */}
        <div className="flex justify-end mb-6 space-x-2">
          <Button variant="outline" size="sm">
            <Download className="w-4 h-4 mr-2" />
            Export
          </Button>
          <Button onClick={handleRunBacktest} disabled={isRunning} size="lg">
            <Play className="w-4 h-4 mr-2" />
            {isRunning ? "Running..." : "Run Backtest"}
          </Button>
        </div>

        <div className="px-3 grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Configuration Panel */}
          <div className="lg:col-span-1">
            <ConfigurationPanel />
          </div>

          {/* Results Dashboard */}
          <div className="lg:col-span-2">
            {hasResults ? (
              <ResultsDashboard />
            ) : (
              <Card className="p-8 text-center">
                <div className="space-y-4">
                  <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto">
                    <Play className="w-8 h-8 text-muted-foreground" />
                  </div>
                  <h3 className="text-lg font-semibold">Ready to Backtest</h3>
                  <p className="text-muted-foreground">
                    Configure your strategy parameters and click "Run Backtest" to see results
                  </p>
                </div>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
