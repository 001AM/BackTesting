import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  LineChart,
  Line,
} from "recharts";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Percent,
  ArrowUpDown,
  Eye,
  ChevronDown,
  ChevronUp,
  Calendar,
  Clock,
} from "lucide-react";
import { useState } from "react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";

export default function PortfolioAnalytics({ portfolioData }) {
  const [expandedRebalance, setExpandedRebalance] = useState(null);
  // Add these state declarations at the top of your component
  const [searchQuery, setSearchQuery] = useState("");
  const [actionFilter, setActionFilter] = useState("all");
  const [dateFilter, setDateFilter] = useState("all");

  // Add this filtered transactions calculation

  const toggleRebalance = (date) => {
    setExpandedRebalance(expandedRebalance === date ? null : date);
  };

  if (!portfolioData) {
    return <div>Loading portfolio data...</div>;
  }

  // Extract data from portfolioData
  const {
    initial_capital,
    final_value,
    total_return_percentage,
    annualized_return,
    total_profit_loss,
    total_transactions,
    buy_transactions,
    sell_transactions,
    start_date,
    end_date,
    rebalance_dates,
    transaction_history,
    portfolio_history,
    top_winners,
    top_losers,
    compound_annual_growth_rate,
    volatility,
    max_drawdown,
    win_rate,
    equity_curve,
    returns_series,
    drawdown_series,
  } = portfolioData;

  // Format dates
  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  // Prepare data for charts
  const portfolioEvolution = equity_curve.map((item) => ({
    date: new Date(item.date).toLocaleDateString("en-US", {
      month: "short",
      year: "2-digit",
    }),
    value: item.total_value,
  }));

  const monthlyReturns = Object.entries(returns_series).map(
    ([date, returnValue]) => ({
      month: new Date(date).toLocaleDateString("en-US", {
        month: "short",
        year: "2-digit",
      }),
      return: (returnValue * 100).toFixed(1),
    })
  );

  // Group transactions by rebalance date
  const rebalancingHistory = [
    // Add initial portfolio setup as first "rebalance"
    {
      date: start_date,
      type: "Initial Setup",
      portfolioValue: initial_capital,
      cashBalance: initial_capital,
      totalTransactions: transaction_history.filter(
        (tx) => tx.date === start_date
      ).length,
      buyTransactions: transaction_history.filter(
        (tx) => tx.date === start_date && tx.action === "BUY"
      ).length,
      sellTransactions: transaction_history.filter(
        (tx) => tx.date === start_date && tx.action === "SELL"
      ).length,
      holdings: portfolio_history.find((ph) => ph.date === start_date)?.holdings
        ? Object.values(
            portfolio_history.find((ph) => ph.date === start_date).holdings
          ).map((h) => ({
            symbol: h.symbol,
            name: h.company_name,
            quantity: h.quantity,
            avgPrice: h.avg_price,
            value: h.value,
            weight: `${(
              (h.value /
                (h.value +
                  (portfolio_history.find((ph) => ph.date === start_date)
                    ?.cash_balance || 0))) *
              100
            ).toFixed(1)}%`,
          }))
        : [],
      transactions: transaction_history
        .filter((tx) => tx.date === start_date)
        .map((tx) => ({
          symbol: tx.symbol,
          action: tx.action,
          quantity: tx.quantity,
          price: tx.price,
          value: tx.total_value,
          reason: "Initial purchase",
        })),
    },
    // Add all rebalance dates
    ...rebalance_dates.map((date) => {
      const transactions = transaction_history.filter((tx) => tx.date === date);
      const holdings =
        portfolio_history.find((ph) => ph.date === date)?.holdings || {};

      return {
        date,
        type: "Rebalance",
        portfolioValue:
          portfolio_history.find((ph) => ph.date === date)?.total_value || 0,
        cashBalance:
          portfolio_history.find((ph) => ph.date === date)?.cash_balance || 0,
        totalTransactions: transactions.length,
        buyTransactions: transactions.filter((tx) => tx.action === "BUY")
          .length,
        sellTransactions: transactions.filter((tx) => tx.action === "SELL")
          .length,
        holdings: Object.values(holdings).map((h) => ({
          symbol: h.symbol,
          name: h.company_name,
          quantity: h.quantity,
          avgPrice: h.avg_price,
          value: h.value,
          weight: `${(
            (h.value /
              (h.value +
                (portfolio_history.find((ph) => ph.date === date)
                  ?.cash_balance || 0))) *
            100
          ).toFixed(1)}%`,
        })),
        transactions: transactions.map((tx) => ({
          symbol: tx.symbol,
          action: tx.action,
          quantity: tx.quantity,
          price: tx.price,
          value: tx.total_value,
          reason: tx.reason || "Rebalance",
        })),
      };
    }),
    // Add final portfolio state
    {
      date: end_date,
      type: "Final State",
      portfolioValue: final_value,
      cashBalance: final_value, // Assuming fully liquidated
      totalTransactions: transaction_history.filter(
        (tx) => tx.date === end_date
      ).length,
      buyTransactions: 0,
      sellTransactions: transaction_history.filter((tx) => tx.date === end_date)
        .length,
      holdings: [],
      transactions: transaction_history
        .filter((tx) => tx.date === end_date)
        .map((tx) => ({
          symbol: tx.symbol,
          action: tx.action,
          quantity: tx.quantity,
          price: tx.price,
          value: tx.total_value,
          reason: "Final liquidation",
        })),
    },
  ];

  const filteredTransactions = transaction_history.filter((tx) => {
    // Search filter
    const matchesSearch =
      tx.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tx.company_name.toLowerCase().includes(searchQuery.toLowerCase());

    // Action filter
    const matchesAction = actionFilter === "all" || tx.action === actionFilter;

    // Date filter
    const matchesDate = dateFilter === "all" || tx.date === dateFilter;

    return matchesSearch && matchesAction && matchesDate;
  });

  return (
    <div className="space-y-6">
      {/* Portfolio Period Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Calendar className="h-5 w-5" />
              <span>Portfolio Period</span>
            </div>
            <Badge variant="outline" className="text-sm">
              {new Date(start_date).toLocaleDateString("en-US", {
                year: "numeric",
                month: "long",
                day: "numeric",
              })}
              {" → "}
              {new Date(end_date).toLocaleDateString("en-US", {
                year: "numeric",
                month: "long",
                day: "numeric",
              })}
            </Badge>
          </CardTitle>
        </CardHeader>
      </Card>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          {/* <TabsTrigger value="allocation">Allocation</TabsTrigger> */}
          <TabsTrigger value="rebalancing">Rebalancing</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          {/* Key Metrics Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Total Value
                </CardTitle>
                <DollarSign className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  ₹{final_value.toLocaleString()}
                </div>
                <p className="text-xs text-muted-foreground">
                  {total_return_percentage >= 0 ? "+" : ""}
                  {total_return_percentage.toFixed(2)}% total return
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">CAGR</CardTitle>
                <Percent className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {annualized_return.toFixed(2)}%
                </div>
                <p className="text-xs text-muted-foreground">
                  Annualized return
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Max Drawdown
                </CardTitle>
                <TrendingDown className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {max_drawdown.toFixed(2)}%
                </div>
                <p className="text-xs text-muted-foreground">Peak to trough</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {(win_rate * 100).toFixed(2)}%
                </div>
                <p className="text-xs text-muted-foreground">
                  Profitable periods
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Portfolio Evolution Chart */}
          <Card>
            <CardHeader>
              <CardTitle>Portfolio Evolution</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={portfolioEvolution}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis
                    tickFormatter={(value) => `₹${(value / 1000).toFixed(0)}K`}
                  />
                  <Tooltip
                    formatter={(value) => [
                      `₹${value.toLocaleString()}`,
                      "Portfolio Value",
                    ]}
                    labelFormatter={(label) => `Date: ${label}`}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#2563eb"
                    strokeWidth={3}
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Monthly Returns */}
          <Card>
            <CardHeader>
              <CardTitle>Monthly Returns Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={monthlyReturns}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip formatter={(value) => [`${value}%`, "Return"]} />
                  <Bar dataKey="return" fill="#2563eb" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="performance" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Top Winners */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center">
                  <TrendingUp className="w-5 h-5 mr-2 text-green-600" />
                  Top Winners
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {top_winners.slice(0, 5).map((stock, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-3 bg-green-50 rounded-lg border"
                    >
                      <div className="flex-1">
                        <div className="font-medium text-sm">
                          {stock.symbol}
                        </div>
                        <div className="text-xs text-muted-foreground truncate">
                          {stock.company_name}
                        </div>
                      </div>
                      <div className="text-right">
                        <Badge
                          variant="secondary"
                          className="text-green-600 mb-1"
                        >
                          {stock.total_return >= 0 ? "+" : ""}
                          {stock.total_return.toFixed(2)}%
                        </Badge>
                        <div className="text-xs text-muted-foreground">
                          {stock.total_pnl >= 0 ? "+" : ""}₹
                          {stock.total_pnl.toLocaleString()}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Top Losers */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center">
                  <TrendingDown className="w-5 h-5 mr-2 text-red-600" />
                  Top Losers
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {top_losers.slice(0, 5).map((stock, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-3 bg-red-50 rounded-lg border"
                    >
                      <div className="flex-1">
                        <div className="font-medium text-sm">
                          {stock.symbol}
                        </div>
                        <div className="text-xs text-muted-foreground truncate">
                          {stock.company_name}
                        </div>
                      </div>
                      <div className="text-right">
                        <Badge
                          variant="secondary"
                          className="text-red-600 mb-1"
                        >
                          {stock.total_return.toFixed(2)}%
                        </Badge>
                        <div className="text-xs text-muted-foreground">
                          {stock.total_pnl.toLocaleString()}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="rebalancing" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center">
                  <ArrowUpDown className="w-5 h-5 mr-2" />
                  Portfolio Timeline
                </div>
                <div className="flex items-center space-x-2">
                  <Badge variant="secondary" className="text-xs">
                    <Clock className="w-3 h-3 mr-1" />
                    {formatDate(start_date)} → {formatDate(end_date)}
                  </Badge>
                  <Badge variant="secondary">
                    {rebalancingHistory.length} Events
                  </Badge>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {rebalancingHistory.map((rebalance, index) => (
                  <Card
                    key={index}
                    className={`border-l-4 ${
                      rebalance.type === "Initial Setup"
                        ? "border-l-blue-500"
                        : rebalance.type === "Final State"
                        ? "border-l-purple-500"
                        : "border-l-primary"
                    }`}
                  >
                    <Collapsible
                      open={expandedRebalance === rebalance.date}
                      onOpenChange={() => toggleRebalance(rebalance.date)}
                    >
                      <CollapsibleTrigger asChild>
                        <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-4">
                              <div>
                                <CardTitle className="text-lg flex items-center">
                                  {rebalance.type === "Initial Setup" ? (
                                    <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded mr-2">
                                      Initial
                                    </span>
                                  ) : rebalance.type === "Final State" ? (
                                    <span className="bg-purple-100 text-purple-800 text-xs px-2 py-1 rounded mr-2">
                                      Final
                                    </span>
                                  ) : (
                                    <span className="bg-primary/10 text-primary text-xs px-2 py-1 rounded mr-2">
                                      Rebalance
                                    </span>
                                  )}
                                  {formatDate(rebalance.date)}
                                </CardTitle>
                                <div className="text-sm text-muted-foreground">
                                  {rebalance.holdings.length} holdings •{" "}
                                  {rebalance.totalTransactions} transactions
                                </div>
                              </div>
                            </div>
                            <div className="flex items-center space-x-4">
                              <div className="text-right">
                                <div className="font-semibold">
                                  ₹{rebalance.portfolioValue.toLocaleString()}
                                </div>
                                <div className="text-sm text-muted-foreground">
                                  Cash: ₹
                                  {rebalance.cashBalance.toLocaleString()}
                                </div>
                              </div>
                              {expandedRebalance === rebalance.date ? (
                                <ChevronUp className="w-5 h-5" />
                              ) : (
                                <ChevronDown className="w-5 h-5" />
                              )}
                            </div>
                          </div>
                        </CardHeader>
                      </CollapsibleTrigger>
                      <CollapsibleContent>
                        <CardContent className="pt-0">
                          {/* Holdings and transactions sections */}
                          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            {/* Holdings section */}
                            <div className="space-y-4">
                              <h4 className="font-semibold flex items-center">
                                <Eye className="w-4 h-4 mr-2" />
                                Holdings ({rebalance.holdings.length})
                              </h4>
                              {rebalance.holdings.length > 0 ? (
                                <div className="space-y-3">
                                  {rebalance.holdings.map(
                                    (holding, holdingIndex) => (
                                      <div
                                        key={holdingIndex}
                                        className="flex items-center justify-between p-3 bg-muted/30 rounded-lg"
                                      >
                                        <div className="flex-1">
                                          <div className="font-medium text-sm">
                                            {holding.symbol}
                                          </div>
                                          <div className="text-xs text-muted-foreground">
                                            {holding.name}
                                          </div>
                                          <div className="text-xs text-muted-foreground mt-1">
                                            {holding.quantity} × ₹
                                            {holding.avgPrice.toFixed(2)}
                                          </div>
                                        </div>
                                        <div className="text-right">
                                          <div className="font-medium">
                                            ₹{holding.value.toLocaleString()}
                                          </div>
                                          <Badge
                                            variant="outline"
                                            className="text-xs"
                                          >
                                            {holding.weight}
                                          </Badge>
                                        </div>
                                      </div>
                                    )
                                  )}
                                </div>
                              ) : (
                                <div className="text-sm text-muted-foreground italic">
                                  No holdings at this stage
                                </div>
                              )}
                            </div>

                            {/* Transactions section */}
                            <div className="space-y-4">
                              <h4 className="font-semibold flex items-center">
                                <ArrowUpDown className="w-4 h-4 mr-2" />
                                Transactions ({rebalance.totalTransactions})
                              </h4>
                              {rebalance.transactions.length > 0 ? (
                                <div className="space-y-2 max-h-96 overflow-y-auto">
                                  {rebalance.transactions.map(
                                    (transaction, transactionIndex) => (
                                      <div
                                        key={transactionIndex}
                                        className={`flex items-center justify-between p-3 rounded-lg border ${
                                          transaction.action === "BUY"
                                            ? "bg-green-50 border-green-200"
                                            : "bg-red-50 border-red-200"
                                        }`}
                                      >
                                        <div className="flex-1">
                                          <div className="flex items-center space-x-2">
                                            <Badge
                                              variant={
                                                transaction.action === "BUY"
                                                  ? "secondary"
                                                  : "destructive"
                                              }
                                              className="text-xs"
                                            >
                                              {transaction.action}
                                            </Badge>
                                            <span className="font-medium text-sm">
                                              {transaction.symbol}
                                            </span>
                                          </div>
                                          <div className="text-xs text-muted-foreground mt-1">
                                            {transaction.reason}
                                          </div>
                                        </div>
                                        <div className="text-right">
                                          <div className="font-medium text-sm">
                                            ₹
                                            {transaction.value.toLocaleString()}
                                          </div>
                                          <div className="text-xs text-muted-foreground">
                                            {transaction.quantity} × ₹
                                            {transaction.price.toFixed(2)}
                                          </div>
                                        </div>
                                      </div>
                                    )
                                  )}
                                </div>
                              ) : (
                                <div className="text-sm text-muted-foreground italic">
                                  No transactions at this stage
                                </div>
                              )}
                            </div>
                          </div>

                          {/* Summary Stats */}
                          <div className="mt-6 grid grid-cols-3 gap-4 p-4 bg-muted/20 rounded-lg">
                            <div className="text-center">
                              <div className="text-sm text-muted-foreground">
                                Buy Transactions
                              </div>
                              <div className="font-semibold text-green-600">
                                {rebalance.buyTransactions}
                              </div>
                            </div>
                            <div className="text-center">
                              <div className="text-sm text-muted-foreground">
                                Sell Transactions
                              </div>
                              <div className="font-semibold text-red-600">
                                {rebalance.sellTransactions}
                              </div>
                            </div>
                            <div className="text-center">
                              <div className="text-sm text-muted-foreground">
                                Cash Position
                              </div>
                              <div className="font-semibold">
                                {(
                                  (rebalance.cashBalance /
                                    rebalance.portfolioValue) *
                                  100
                                ).toFixed(1)}
                                %
                              </div>
                            </div>
                          </div>
                        </CardContent>
                      </CollapsibleContent>
                    </Collapsible>
                  </Card>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center">
                  <Clock className="w-5 h-5 mr-2" />
                  Transaction History
                </div>
                <Badge variant="secondary">
                  {formatDate(start_date)} → {formatDate(end_date)}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {/* Search and Filter Controls */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div className="md:col-span-2">
                  <Input
                    placeholder="Search by symbol or company..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
                <Select value={actionFilter} onValueChange={setActionFilter}>
                  <SelectTrigger>
                    <SelectValue placeholder="All actions" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All actions</SelectItem>
                    <SelectItem value="BUY">Buy only</SelectItem>
                    <SelectItem value="SELL">Sell only</SelectItem>
                  </SelectContent>
                </Select>
                <Select value={dateFilter} onValueChange={setDateFilter}>
                  <SelectTrigger>
                    <SelectValue placeholder="All dates" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All dates</SelectItem>
                    {Array.from(
                      new Set(transaction_history.map((tx) => tx.date))
                    ).map((date) => (
                      <SelectItem key={date} value={date}>
                        {formatDate(date)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Clear Filters Button */}
              {(searchQuery ||
                actionFilter !== "all" ||
                dateFilter !== "all") && (
                <div className="flex justify-end mb-4">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setSearchQuery("");
                      setActionFilter("all");
                      setDateFilter("all");
                    }}
                  >
                    Clear filters
                  </Button>
                </div>
              )}

              {/* Filtered Transaction Count */}
              <div className="text-sm text-muted-foreground mb-4">
                Showing {filteredTransactions.length} of{" "}
                {transaction_history.length} transactions
              </div>

              {/* Transaction Timeline */}
              <div className="space-y-6">
                <div className="relative">
                  <div className="absolute left-5 top-0 bottom-0 w-0.5 bg-gray-200"></div>
                  <div className="space-y-8 pl-8">
                    {filteredTransactions.length > 0 ? (
                      filteredTransactions.map((tx, index) => (
                        <div key={index} className="relative">
                          <div className="absolute -left-8 top-4 w-4 h-4 rounded-full bg-primary border-4 border-white"></div>
                          <div
                            className={`p-4 rounded-lg border ${
                              tx.action === "BUY"
                                ? "bg-green-50 border-green-200"
                                : "bg-red-50 border-red-200"
                            }`}
                          >
                            <div className="flex justify-between items-start">
                              <div>
                                <div className="font-medium flex items-center">
                                  <span
                                    className={`inline-block w-2 h-2 rounded-full mr-2 ${
                                      tx.action === "BUY"
                                        ? "bg-green-500"
                                        : "bg-red-500"
                                    }`}
                                  ></span>
                                  {tx.symbol} - {tx.action}
                                </div>
                                <div className="text-sm text-muted-foreground mt-1">
                                  {formatDate(tx.date)}
                                </div>
                                <div className="text-sm text-muted-foreground mt-1">
                                  {tx.quantity} shares @ ₹{tx.price.toFixed(2)}
                                </div>
                              </div>
                              <div className="text-right">
                                <div className="font-medium">
                                  ₹{tx.total_value.toLocaleString()}
                                </div>
                                <div className="text-xs text-muted-foreground">
                                  Portfolio: ₹
                                  {tx.portfolio_value.toLocaleString()}
                                </div>
                                <div className="text-xs text-muted-foreground">
                                  Cash: ₹{tx.cash_balance.toLocaleString()}
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-center py-8 text-muted-foreground">
                        No transactions match your filters
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
