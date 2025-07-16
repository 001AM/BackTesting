import React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

// Mock data
const topWinners = [
  { stock: "Reliance Industries", returns: "45.2%", weight: "8.5%" },
  { stock: "TCS", returns: "38.7%", weight: "7.2%" },
  { stock: "HDFC Bank", returns: "32.1%", weight: "6.8%" },
  { stock: "Infosys", returns: "28.9%", weight: "5.9%" },
  { stock: "ITC", returns: "25.4%", weight: "4.7%" },
]

const topLosers = [
  { stock: "Bajaj Finance", returns: "-12.3%", weight: "3.2%" },
  { stock: "Asian Paints", returns: "-8.7%", weight: "2.8%" },
  { stock: "Nestle India", returns: "-6.4%", weight: "2.1%" },
  { stock: "Titan Company", returns: "-4.2%", weight: "1.9%" },
  { stock: "UltraTech Cement", returns: "-3.1%", weight: "1.5%" },
]

const sectorAllocation = [
  { name: "IT", value: 25, color: "#0088FE" },
  { name: "Banking", value: 20, color: "#00C49F" },
  { name: "Energy", value: 15, color: "#FFBB28" },
  { name: "FMCG", value: 12, color: "#FF8042" },
  { name: "Pharma", value: 10, color: "#8884D8" },
  { name: "Auto", value: 8, color: "#82CA9D" },
  { name: "Others", value: 10, color: "#FFC658" },
]

const portfolioLog = [
  { date: "2023-10-01", action: "Rebalance", stocks: "20", totalValue: "₹27.5L" },
  { date: "2023-07-01", action: "Rebalance", stocks: "20", totalValue: "₹25.5L" },
  { date: "2023-04-01", action: "Rebalance", stocks: "20", totalValue: "₹24.0L" },
  { date: "2023-01-01", action: "Rebalance", stocks: "20", totalValue: "₹22.5L" },
  { date: "2022-10-01", action: "Rebalance", stocks: "20", totalValue: "₹21.0L" },
]

export default function PortfolioAnalytics() {
  return (
    <div className="space-y-6">
      <Tabs defaultValue="performance" className="space-y-4">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="allocation">Allocation</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
        </TabsList>

        {/* Performance Tab */}
        <TabsContent value="performance" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Top Winners */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Top 5 Winners</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Stock</TableHead>
                      <TableHead>Returns</TableHead>
                      <TableHead>Weight</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {topWinners.map((stock, index) => (
                      <TableRow key={index}>
                        <TableCell className="font-medium">{stock.stock}</TableCell>
                        <TableCell>
                          <Badge variant="secondary" className="text-green-600">
                            {stock.returns}
                          </Badge>
                        </TableCell>
                        <TableCell>{stock.weight}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            {/* Top Losers */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Top 5 Losers</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Stock</TableHead>
                      <TableHead>Returns</TableHead>
                      <TableHead>Weight</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {topLosers.map((stock, index) => (
                      <TableRow key={index}>
                        <TableCell className="font-medium">{stock.stock}</TableCell>
                        <TableCell>
                          <Badge variant="secondary" className="text-red-600">
                            {stock.returns}
                          </Badge>
                        </TableCell>
                        <TableCell>{stock.weight}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Allocation Tab */}
        <TabsContent value="allocation" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Sector Allocation</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={sectorAllocation}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {sectorAllocation.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>

                <div className="space-y-2">
                  {sectorAllocation.map((sector, index) => (
                    <div key={index} className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: sector.color }} />
                        <span className="text-sm">{sector.name}</span>
                      </div>
                      <span className="text-sm font-medium">{sector.value}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* History Tab */}
        <TabsContent value="history" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Portfolio History</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Action</TableHead>
                    <TableHead>Stocks</TableHead>
                    <TableHead>Total Value</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {portfolioLog.map((entry, index) => (
                    <TableRow key={index}>
                      <TableCell>{entry.date}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{entry.action}</Badge>
                      </TableCell>
                      <TableCell>{entry.stocks}</TableCell>
                      <TableCell className="font-medium">{entry.totalValue}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
