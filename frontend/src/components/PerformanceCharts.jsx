import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from "recharts";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

export default function PerformanceCharts({ equitydata, drawdown }) {
  const [showBenchmark, setShowBenchmark] = useState(true);

  // Format equity data for chart - keeping same structure as before
  const formatEquityData = () => {
    return equitydata.map((item) => ({
      date: new Date(item.date).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
      }),
      portfolio: item.total_value,
      nifty: item.nifty_investment_value, // Will be populated when we have Nifty data
    }));
  };

  // Format drawdown data for chart
  const formatDrawdownData = () => {
    return drawdown.map((item) => ({
      date: new Date(item.date).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
      }),
      drawdown: item.drawdown,
    }));
  };

  const equityChartData = formatEquityData();
  const drawdownChartData = formatDrawdownData();

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Equity Curve */}
      <Card className="lg:col-span-2">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Equity Curve</CardTitle>
            <div className="flex items-center space-x-2">
              <Switch 
                id="benchmark" 
                checked={showBenchmark} 
                onCheckedChange={setShowBenchmark}
                className="data-[state=checked]:bg-blue-600 data-[state=unchecked]:border border-gray-300"
              />
              <Label htmlFor="benchmark" className="text-sm">
                Show Nifty 50
              </Label>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={showBenchmark ?  300 : 250}>
            <LineChart data={equityChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis
                tickFormatter={(value) => `₹${(value / 1000).toFixed(0)}K`}
              />
              <Tooltip
                formatter={(value) => [`₹${value.toLocaleString("en-IN")}`, ""]}
                labelFormatter={(label) => `Date: ${label}`}
              />
              <Line
                type="monotone"
                dataKey="portfolio"
                stroke="#2563eb"
                strokeWidth={2}
                name="Portfolio"
                dot={false}
              />
              {showBenchmark && (
                <Line
                  type="monotone"
                  dataKey="nifty"
                  stroke="#dc2626"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  name="Nifty 50"
                  dot={false}
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
            <AreaChart data={drawdownChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis tickFormatter={(value) => `${value}%`} />
              <Tooltip
                formatter={(value) => [`${value}%`, "Drawdown"]}
                labelFormatter={(label) => `Date: ${label}`}
              />
              <Area
                type="monotone"
                dataKey="drawdown"
                stroke="#dc2626"
                fill="#dc2626"
                fillOpacity={0.3}
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}
