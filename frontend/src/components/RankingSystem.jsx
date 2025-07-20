import { useState, useEffect } from "react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  TooltipProvider,
} from "@/components/ui/tooltip";
import { Info, X, TrendingUp, TrendingDown } from "lucide-react";

const availableMetrics = [
  { id: "roe", name: "ROE", description: "Return on Equity" },
  { id: "pe_ratio", name: "P/E", description: "Price to Earnings Ratio" },
  { id: "roce", name: "ROCE", description: "Return on Capital Employed" },
  { id: "debt_equity_ratio", name: "Debt/Equity", description: "Debt to Equity Ratio" },
  { id: "current_ratio", name: "Current Ratio", description: "Current Assets / Current Liabilities" },
  { id: "pb_ratio", name: "P/BV", description: "Price to Book Value" },
];

export function RankingSystem({onConfigChange, propData}) {
  const [selectedMetrics, setSelectedMetrics] = useState([])
  const [metricDirections, setMetricDirections] = useState({})

  useEffect(() => {
    if (!propData || propData.length === 0) return;
    
    const metricNames = propData.map(metric => Object.keys(metric)[0]);
    const newSelected = availableMetrics.map(metric => metric.id).filter(id => metricNames.includes(id)); 
    const selectionChanged = JSON.stringify(newSelected.sort()) !== JSON.stringify(selectedMetrics.sort());
    
    if (selectionChanged) {
      setSelectedMetrics(newSelected);
      const newDirections = { ...metricDirections };
      newSelected.forEach(metric => {
        if (!(metric in newDirections)) {
          newDirections[metric] = "desc";
        }
      });
      Object.keys(newDirections).forEach(metric => {
        if (!newSelected.includes(metric)) {
          delete newDirections[metric];
        }
      });
      setMetricDirections(newDirections);
    }
  }, [propData]);

  useEffect(() => {
    if (onConfigChange) {
      const rankingMetrics = selectedMetrics.map(metric => ({
        [metric]: metricDirections[metric] === "desc"
      }));
      
      onConfigChange({
        ranking_metrics: rankingMetrics
      });
    }
  }, [selectedMetrics, metricDirections, onConfigChange]);

  const addMetric = (metricId) => {
    if (!selectedMetrics.includes(metricId)) {
      const updatedMetrics = [...selectedMetrics, metricId];
      setSelectedMetrics(updatedMetrics);
      setMetricDirections({ ...metricDirections, [metricId]: "desc" });
    }
  };

  const removeMetric = (metricId) => {
    const updatedMetrics = selectedMetrics.filter((id) => id !== metricId);
    setSelectedMetrics(updatedMetrics);

    const updatedDirections = { ...metricDirections };
    delete updatedDirections[metricId];
    setMetricDirections(updatedDirections);
  };

  const toggleDirection = (metricId) => {
    setMetricDirections({
      ...metricDirections,
      [metricId]: metricDirections[metricId] === "asc" ? "desc" : "asc",
    });
  };

  return (
    <TooltipProvider>
      <div className="space-y-6">
        {/* Metric Selection */}
        <div className="space-y-3">
          <Label className="text-sm font-medium">Ranking Metrics</Label>
          <Select onValueChange={addMetric}>
            <SelectTrigger>
              <SelectValue placeholder="Add ranking metric" />
            </SelectTrigger>
            <SelectContent>
              {availableMetrics
                .filter((metric) => !selectedMetrics.includes(metric.id))
                .map((metric) => (
                  <SelectItem key={metric.id} value={metric.id}>
                    <div className="flex flex-col">
                      <span>{metric.name}</span>
                      <span className="text-xs text-muted-foreground">{metric.description}</span>
                    </div>
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
        </div>
        {/* Selected Metrics */}
        <div className="space-y-3">
          {selectedMetrics.map((metricId) => {
            const metric = availableMetrics.find((m) => m.id === metricId);
            return (
              <div key={metricId} className="flex items-center justify-between p-3 border rounded-lg">
                <div className="flex items-center space-x-3">
                  <Badge variant="secondary">{metric?.name}</Badge>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => toggleDirection(metricId)}
                    className="h-6 px-2"
                  >
                    {metricDirections[metricId] === "desc" ? (
                      <TrendingDown className="w-3 h-3" />
                    ) : (
                      <TrendingUp className="w-3 h-3" />
                    )}
                    <span className="ml-1 text-xs">
                      {metricDirections[metricId] === "desc" ? "High to Low" : "Low to High"}
                    </span>
                  </Button>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removeMetric(metricId)}
                  className="h-6 w-6 p-0"
                >
                  <X className="w-3 h-3" />
                </Button>
              </div>
            );
          })}
        </div>
      </div>
    </TooltipProvider>
  );
}