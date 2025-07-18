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
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
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

export function RankingSystem({onConfigChange}) {
  const [selectedMetrics, setSelectedMetrics] = useState(["roe", "roce"]);
  const [metricDirections, setMetricDirections] = useState({
    roe: "desc",
    roce: "desc",
  });
  const [compositeRanking, setCompositeRanking] = useState(false);
  const [metricWeights, setMetricWeights] = useState({
    roe: 50,
    roce: 50,
  });

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

      if (compositeRanking) {
        const newWeight = 100 / updatedMetrics.length;
        const updatedWeights = {};
        updatedMetrics.forEach((id) => {
          updatedWeights[id] = newWeight;
        });
        setMetricWeights(updatedWeights);
      }
    }
  };

  const removeMetric = (metricId) => {
    const updatedMetrics = selectedMetrics.filter((id) => id !== metricId);
    setSelectedMetrics(updatedMetrics);

    const updatedDirections = { ...metricDirections };
    delete updatedDirections[metricId];
    setMetricDirections(updatedDirections);

    const updatedWeights = { ...metricWeights };
    delete updatedWeights[metricId];
    setMetricWeights(updatedWeights);
  };

  const toggleDirection = (metricId) => {
    setMetricDirections({
      ...metricDirections,
      [metricId]: metricDirections[metricId] === "asc" ? "desc" : "asc",
    });
  };

  const updateWeight = (metricId, weight) => {
    setMetricWeights({ ...metricWeights, [metricId]: weight });
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

        {/* Composite Ranking */}
        <div className="space-y-4">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="composite"
              checked={compositeRanking}
              onCheckedChange={setCompositeRanking}
            />
            <Label htmlFor="composite" className="text-sm font-medium">
              Enable Composite Ranking
            </Label>
            <Tooltip>
              <TooltipTrigger>
                <Info className="w-4 h-4 text-muted-foreground" />
              </TooltipTrigger>
              <TooltipContent>
                <p className="max-w-xs">
                  Combine multiple metrics with custom weights to create a single composite score
                </p>
              </TooltipContent>
            </Tooltip>
          </div>

          {compositeRanking && selectedMetrics.length > 0 && (
            <div className="space-y-3 p-4 bg-muted/50 rounded-lg">
              <Label className="text-sm font-medium">Metric Weights</Label>
              {selectedMetrics.map((metricId) => {
                const metric = availableMetrics.find((m) => m.id === metricId);
                return (
                  <div key={metricId} className="flex items-center justify-between">
                    <span className="text-sm">{metric?.name}</span>
                    <div className="flex items-center space-x-2">
                      <Input
                        type="number"
                        value={metricWeights[metricId] || 0}
                        onChange={(e) => updateWeight(metricId, Number(e.target.value))}
                        className="w-16 h-8"
                        min="0"
                        max="100"
                      />
                      <span className="text-sm text-muted-foreground">%</span>
                    </div>
                  </div>
                );
              })}
              <div className="text-xs text-muted-foreground">
                Total: {Object.values(metricWeights).reduce((sum, weight) => sum + weight, 0)}%
              </div>
            </div>
          )}
        </div>
      </div>
    </TooltipProvider>
  );
}
