import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import { Search, TrendingUp, Building } from "lucide-react"
import axiosInstance from "@/lib/axios"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogTitle, DialogTrigger, DialogHeader } from "@/components/ui/dialog"

export default function DataPage() {
  const [stocks, setStocks] = useState([])
  const [filteredStocks, setFilteredStocks] = useState([])
  const [searchTerm, setSearchTerm] = useState("")
  const [dialogOpen, setDialogOpen] = useState(false)
  const [stats, setStats] = useState({
    totalStocks: 0,
    lastUpdate: "",
    dataCompleteness: 0,
    sectors: 0,
  })
  const [loading, setLoading] = useState(true)
  const [symbolToAdd, setSymbolToAdd] = useState("")

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [stockRes, statsRes] = await Promise.all([
          axiosInstance.get("/stocks/universe"),
          axiosInstance.get("/stocks/universe/statistics")
        ])

        setStocks(stockRes.data.data)
        setFilteredStocks(stockRes.data.data)
        setStats({
          totalStocks: statsRes.data.data.total_stocks,
          lastUpdate: statsRes.data.data.last_updated,
          dataCompleteness: statsRes.data.data.data_completeness,
          sectors: statsRes.data.data.total_sectors,
        })
        
        setLoading(false)
      } catch (error) {
        console.error("Failed to fetch stock data", error)
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  const handleStockInput = (e) => {
    setSymbolToAdd(e.target.value)
  }

  useEffect(() => {
    const filtered = stocks.filter((stock) =>
      (stock.symbol?.toLowerCase() ?? "").includes(searchTerm.toLowerCase()) ||
      (stock.name?.toLowerCase() ?? "").includes(searchTerm.toLowerCase()) ||
      (stock.sector?.toLowerCase() ?? "").includes(searchTerm.toLowerCase())
    )
    setFilteredStocks(filtered)
  }, [searchTerm, stocks])

  const handleAddStock = async () => {
    try {
      await axiosInstance.post("populate/populate/add_company/", { symbol_list: [symbolToAdd] } )
      setDialogOpen(false)
    } catch (error) {
      console.error("Failed to add stock", error)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading market data...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-11/12 bg-slate-50">
      <div className="container mx-auto px-4 py-8">
        {/* ───────────────── Stats Cards ───────────────── */}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
          <Card><CardContent className="p-4 flex justify-between items-center">
            <div><p className="text-sm text-gray-600">Total Stocks</p><p className="text-2xl font-bold">{stats.totalStocks}</p></div>
            <Building className="h-8 w-8 text-blue-600" />
          </CardContent></Card>

          <Card><CardContent className="p-4 flex justify-between items-center">
            <div><p className="text-sm text-gray-600">Sectors</p><p className="text-2xl font-bold">{stats.sectors}</p></div>
            <TrendingUp className="h-8 w-8 text-green-600" />
          </CardContent></Card>

          <Card><CardContent className="p-4">
            <p className="text-sm text-gray-600 mb-2">Data Completeness</p>
            <div className="flex items-center space-x-2">
              <Progress value={stats.dataCompleteness} className="flex-1" />
              <span className="text-sm font-medium">{stats.dataCompleteness.toFixed(1)}%</span>
            </div>
          </CardContent></Card>

          {/* <Card><CardContent className="p-4">
            <p className="text-sm text-gray-600">Last Updated</p>
            <p className="text-sm font-medium">{stats.lastUpdate}</p>
          </CardContent></Card> */}
        </div>

        {/* ───────────────── Tabs and Stock Table ───────────────── */}
        <Tabs defaultValue="stocks" className="space-y-6">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="stocks">Stock Data</TabsTrigger>
            <TabsTrigger value="prices">Price History</TabsTrigger>
            <TabsTrigger value="fundamentals">Fundamentals</TabsTrigger>
          </TabsList>

          <TabsContent value="stocks">
            <Card className="gap-6">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Stock Universe</CardTitle>
                    <CardDescription>Complete list of stocks with fundamental data</CardDescription>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                      <DialogTrigger asChild>
                        <Button variant="outline">Add Stock</Button>
                      </DialogTrigger>
                      <DialogContent>
                        <DialogHeader>
                          <DialogTitle>Add New Stock</DialogTitle>
                          <DialogDescription>
                            Add a new stock to the universe for backtesting analysis.
                          </DialogDescription>
                        </DialogHeader>
                        <div className="grid gap-4 py-4">
                          <div className="flex items-center gap-4">
                            <label htmlFor="symbol" className="text-right">
                              Symbol
                            </label>
                            <Input id="symbol" onChange={()=>handleStockInput(e)} placeholder="e.g., RELIANCE" />
                          </div>
                        </div>
                        <div className="flex justify-end gap-2">
                          <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
                          <Button onClick={()=>handleAddStock()}>Add Stock</Button>
                        </div>
                      </DialogContent>
                    </Dialog>
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                      <Input
                        placeholder="Search stocks..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="pl-10 w-64"
                      />
                    </div>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Symbol</TableHead>
                      <TableHead>Company Name</TableHead>
                      <TableHead>Sector</TableHead>
                      <TableHead className="text-right">Market Cap</TableHead>
                      <TableHead className="text-right">P/E</TableHead>
                      <TableHead className="text-right">ROE (%)</TableHead>
                      <TableHead className="text-right">ROCE (%)</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredStocks.map((stock) => (
                      <TableRow key={stock.symbol}>
                        <TableCell className="font-medium">{stock.symbol}</TableCell>
                        <TableCell>{stock.company_name}</TableCell>
                        <TableCell><Badge variant="outline">{stock.sector}</Badge></TableCell>
                        <TableCell className="text-right">{stock.market_cap?.toLocaleString() ?? "-"}</TableCell>
                        <TableCell className="text-right">{stock.pe_ratio ?? "-"}</TableCell>
                        <TableCell className="text-right">{stock.roe ?? "-"}</TableCell>
                        <TableCell className="text-right">{stock.roce ?? "-"}</TableCell>
                        <TableCell><Badge variant="secondary">{"Updated"}</Badge></TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="prices">
            <Card>
              <CardHeader>
                <CardTitle className="mb-1">Price Data Coverage</CardTitle>
                <CardDescription className="mb-0.5">Historical OHLCV data availability across stocks</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-4">
                    <div className="text-center p-4 bg-green-50 rounded-lg">
                      <p className="text-2xl font-bold text-green-600">98.5%</p>
                      <p className="text-sm text-gray-600">Daily Data Coverage</p>
                    </div>
                    <div className="text-center p-4 bg-blue-50 rounded-lg">
                      <p className="text-2xl font-bold text-blue-600">10 Years</p>
                      <p className="text-sm text-gray-600">Historical Depth</p>
                    </div>
                    <div className="text-center p-4 bg-purple-50 rounded-lg">
                      <p className="text-2xl font-bold text-purple-600">Real-time</p>
                      <p className="text-sm text-gray-600">Data Updates</p>
                    </div>
                  </div>

                  <div className="mt-6">
                    <h4 className="font-medium mb-3">Data Sources</h4>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="flex items-center space-x-3 p-3 border rounded-lg">
                        <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                        <div>
                          <p className="font-medium">Yahoo Finance API</p>
                          <p className="text-sm text-gray-600">Primary price data source</p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-3 p-3 border rounded-lg">
                        <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                        <div>
                          <p className="font-medium">NSE Official Data</p>
                          <p className="text-sm text-gray-600">Corporate actions & adjustments</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="fundamentals">
            <Card>
              <CardHeader>
                <CardTitle className="mb-1.5">Fundamental Data Metrics</CardTitle>
                <CardDescription className="mb-0.5">Available financial metrics and ratios for analysis</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-3 gap-6">
                  <div>
                    <h4 className="font-medium mb-3">Profitability Ratios</h4>
                    <ul className="space-y-2 text-sm">
                      <li className="flex items-center space-x-2">
                        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                        <span>Return on Equity (ROE)</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                        <span>Return on Capital Employed (ROCE)</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                        <span>Net Profit Margin</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                        <span>Operating Margin</span>
                      </li>
                    </ul>
                  </div>

                  <div>
                    <h4 className="font-medium mb-3">Valuation Ratios</h4>
                    <ul className="space-y-2 text-sm">
                      <li className="flex items-center space-x-2">
                        <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                        <span>Price to Earnings (P/E)</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                        <span>Price to Book (P/B)</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                        <span>EV/EBITDA</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                        <span>Price to Sales (P/S)</span>
                      </li>
                    </ul>
                  </div>

                  <div>
                    <h4 className="font-medium mb-3">Financial Health</h4>
                    <ul className="space-y-2 text-sm">
                      <li className="flex items-center space-x-2">
                        <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                        <span>Debt to Equity</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                        <span>Current Ratio</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                        <span>Interest Coverage</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                        <span>Cash Flow Ratios</span>
                      </li>
                    </ul>
                  </div>
                </div>

                {/* <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <h4 className="font-medium text-yellow-800 mb-2">Data Collection Status</h4>
                  <p className="text-sm text-yellow-700">
                    Fundamental data is updated quarterly after earnings announcements. Next scheduled update: March 31,
                    2024
                  </p>
                </div> */}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

