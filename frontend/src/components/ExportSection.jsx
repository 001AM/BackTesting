import React from "react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from "@/components/ui/dropdown-menu";
import { Download, FileText, FileSpreadsheet } from "lucide-react";
import * as XLSX from 'xlsx';

export default function ExportSection({ data }) {
  const formatNumber = (num) => {
    if (typeof num !== 'number') return num;
    return parseFloat(num.toFixed(4));
  };

  const exportToCSV = () => {
    if (!data) return;

    // Prepare transaction history CSV
    const transactionHeaders = [
      "Date", "Symbol", "Company Name", "Action", 
      "Quantity", "Price", "Total Value", 
      "Portfolio Value", "Cash Balance"
    ];
    
    const transactionRows = data.transaction_history.map(tx => [
      tx.date,
      tx.symbol,
      tx.company_name,
      tx.action,
      tx.quantity,
      formatNumber(tx.price),
      formatNumber(tx.total_value),
      formatNumber(tx.portfolio_value),
      formatNumber(tx.cash_balance)
    ]);

    // Prepare portfolio history CSV
    const portfolioHeaders = [
      "Date", "Symbol", "Company Name", 
      "Quantity", "Avg Price", "Current Price", 
      "Value", "Cash Balance", "Total Value"
    ];
    
    const portfolioRows = data.portfolio_history.flatMap(entry => {
      const holdings = Object.values(entry.holdings);
      return holdings.map(holding => [
        entry.date,
        holding.symbol,
        holding.company_name,
        holding.quantity,
        formatNumber(holding.avg_price),
        formatNumber(holding.current_price),
        formatNumber(holding.value),
        formatNumber(entry.cash_balance),
        formatNumber(entry.total_value)
      ]);
    });

    // Prepare performance metrics CSV
    const performanceHeaders = ["Metric", "Value"];
    const performanceRows = [
      ["Initial Capital", formatNumber(data.initial_capital)],
      ["Final Value", formatNumber(data.final_value)],
      ["Total Return (%)", formatNumber(data.total_return_percentage)],
      ["Annualized Return (%)", formatNumber(data.annualized_return)],
      ["Total Profit/Loss", formatNumber(data.total_profit_loss)],
      ["Total Transactions", data.total_transactions],
      ["Buy Transactions", data.buy_transactions],
      ["Sell Transactions", data.sell_transactions],
      ["Start Date", data.start_date],
      ["End Date", data.end_date],
      ["Volatility", formatNumber(data.volatility)],
      ["Max Drawdown (%)", formatNumber(data.max_drawdown)],
      ["Sharpe Ratio", formatNumber(data.sharpe_ratio)]
    ];

    // Combine all CSV data
    const csvContent = [
      "Transaction History",
      transactionHeaders.join(","),
      ...transactionRows.map(row => row.join(",")),
      "\nPortfolio History",
      portfolioHeaders.join(","),
      ...portfolioRows.map(row => row.join(",")),
      "\nPerformance Metrics",
      performanceHeaders.join(","),
      ...performanceRows.map(row => row.join(","))
    ].join("\n");

    // Create download link
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `portfolio-report-${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const exportToExcel = () => {
    if (!data) return;

    try {
      const wb = XLSX.utils.book_new();
      
      // Add transaction history sheet
      const transactionData = data.transaction_history.map(tx => ({
        Date: tx.date,
        Symbol: tx.symbol,
        "Company Name": tx.company_name,
        Action: tx.action,
        Quantity: tx.quantity,
        Price: formatNumber(tx.price),
        "Total Value": formatNumber(tx.total_value),
        "Portfolio Value": formatNumber(tx.portfolio_value),
        "Cash Balance": formatNumber(tx.cash_balance)
      }));
      
      const transactionWS = XLSX.utils.json_to_sheet(transactionData);
      
      // Set column widths for transaction sheet
      transactionWS['!cols'] = [
        { width: 12 }, // Date
        { width: 10 }, // Symbol
        { width: 25 }, // Company Name
        { width: 8 },  // Action
        { width: 10 }, // Quantity
        { width: 12 }, // Price
        { width: 12 }, // Total Value
        { width: 15 }, // Portfolio Value
        { width: 12 }  // Cash Balance
      ];
      
      XLSX.utils.book_append_sheet(wb, transactionWS, "Transactions");
      
      // Add portfolio history sheet
      const portfolioData = data.portfolio_history.flatMap(entry => {
        const holdings = Object.values(entry.holdings);
        return holdings.map(holding => ({
          Date: entry.date,
          Symbol: holding.symbol,
          "Company Name": holding.company_name,
          Quantity: holding.quantity,
          "Avg Price": formatNumber(holding.avg_price),
          "Current Price": formatNumber(holding.current_price),
          Value: formatNumber(holding.value),
          "Cash Balance": formatNumber(entry.cash_balance),
          "Total Value": formatNumber(entry.total_value)
        }));
      });
      
      const portfolioWS = XLSX.utils.json_to_sheet(portfolioData);
      
      // Set column widths for portfolio sheet
      portfolioWS['!cols'] = [
        { width: 12 }, // Date
        { width: 10 }, // Symbol
        { width: 25 }, // Company Name
        { width: 10 }, // Quantity
        { width: 12 }, // Avg Price
        { width: 12 }, // Current Price
        { width: 12 }, // Value
        { width: 12 }, // Cash Balance
        { width: 12 }  // Total Value
      ];
      
      XLSX.utils.book_append_sheet(wb, portfolioWS, "Portfolio");
      
      // Add performance sheet
      const performanceData = [
        { Metric: "Initial Capital", Value: formatNumber(data.initial_capital) },
        { Metric: "Final Value", Value: formatNumber(data.final_value) },
        { Metric: "Total Return (%)", Value: formatNumber(data.total_return_percentage) },
        { Metric: "Annualized Return (%)", Value: formatNumber(data.annualized_return) },
        { Metric: "Total Profit/Loss", Value: formatNumber(data.total_profit_loss) },
        { Metric: "Total Transactions", Value: data.total_transactions },
        { Metric: "Buy Transactions", Value: data.buy_transactions },
        { Metric: "Sell Transactions", Value: data.sell_transactions },
        { Metric: "Start Date", Value: data.start_date },
        { Metric: "End Date", Value: data.end_date },
        { Metric: "Volatility", Value: formatNumber(data.volatility) },
        { Metric: "Max Drawdown (%)", Value: formatNumber(data.max_drawdown) },
        { Metric: "Sharpe Ratio", Value: formatNumber(data.sharpe_ratio) }
      ];
      
      const performanceWS = XLSX.utils.json_to_sheet(performanceData);
      
      // Set column widths for performance sheet
      performanceWS['!cols'] = [
        { width: 20 }, // Metric
        { width: 15 }  // Value
      ];
      
      XLSX.utils.book_append_sheet(wb, performanceWS, "Performance");
      
      // Generate and download the Excel file
      XLSX.writeFile(wb, `portfolio-report-${new Date().toISOString().split('T')[0]}.xlsx`);
    } catch (error) {
      console.error("Error exporting to Excel:", error);
      // Fallback to CSV if Excel export fails
      exportToCSV();
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" className="h-8 gap-1">
          <Download className="h-3.5 w-3.5" />
          <span className="sr-only sm:not-sr-only sm:whitespace-nowrap">
            Export Data
          </span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => exportToCSV()}>
          <FileText className="mr-2 h-3.5 w-3.5" />
          Export as CSV
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => exportToExcel()}>
          <FileSpreadsheet className="mr-2 h-3.5 w-3.5" />
          Export as Excel
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}