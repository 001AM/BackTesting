import React from "react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from "@/components/ui/dropdown-menu"
import { Download, FileText, FileSpreadsheet } from "lucide-react"

export default function ExportSection() {
  const handleExport = (format) => {
    console.log(`Exporting in ${format} format`)
    // Actual export logic should go here
  }

  return (
    <div className="flex items-center space-x-2">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm">
            <Download className="w-4 h-4 mr-2" />
            Export Data
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuItem onClick={() => handleExport("csv")}>
            <FileText className="w-4 h-4 mr-2" />
            Export as CSV
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => handleExport("excel")}>
            <FileSpreadsheet className="w-4 h-4 mr-2" />
            Export as Excel
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <Button variant="outline" size="sm" onClick={() => handleExport("portfolio-log")} className="hidden">
        <Download className="w-4 h-4 mr-2" />
        Portfolio Log
      </Button>

      <Button variant="outline" size="sm" onClick={() => handleExport("performance-report")} className="hidden">
        <FileText className="w-4 h-4 mr-2" />
        Performance Report
      </Button>
    </div>
  )
}
