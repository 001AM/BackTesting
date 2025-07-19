import { useState, useEffect } from "react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Calendar } from "@/components/ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { CalendarIcon } from "lucide-react";
import { format } from "date-fns";

export function BasicConfig({ onConfigChange }) {
  const [startDate, setStartDate] = useState(new Date("2023-07-18"));
  const [endDate, setEndDate] = useState(() => {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    return yesterday;
  });
  const [rebalanceFreq, setRebalanceFreq] = useState("quarterly");
  const [portfolioSize, setPortfolioSize] = useState("5");
  const [initialCapital, setInitialCapital] = useState("10000");
  const [weightingMethod, setWeightingMethod] = useState("equal");

  useEffect(() => {
    if (onConfigChange) {
      onConfigChange({
        start_date: startDate ? startDate.toISOString().split("T")[0] : null,
        end_date: endDate ? endDate.toISOString().split("T")[0] : null,
        rebalancing_frequency: rebalanceFreq,
        portfolio_size: parseInt(portfolioSize) || 0,
        initial_capital: parseInt(initialCapital) || 0,
        weighting_method: weightingMethod,
      });
    }
  }, [
    startDate,
    endDate,
    rebalanceFreq,
    portfolioSize,
    initialCapital,
    weightingMethod,
    onConfigChange,
  ]);

  return (
    <div className="space-y-6">
      {/* Date Range */}
      <div className="space-y-4">
        <Label className="text-sm font-medium">Backtest Period</Label>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label className="text-xs text-muted-foreground">Start Date</Label>
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="outline" className="w-full justify-start text-left font-normal bg-transparent">
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {startDate ? format(startDate, "PPP") : "Pick a date"}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0">
                <Calendar
                  mode="single"
                  selected={startDate}
                  onSelect={setStartDate}
                  initialFocus
                />
              </PopoverContent>
            </Popover>
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">End Date</Label>
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="outline" className="w-full justify-start text-left font-normal bg-transparent">
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {endDate ? format(endDate, "PPP") : "Pick a date"}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0">
                <Calendar
                  mode="single"
                  selected={endDate}
                  onSelect={setEndDate}
                  initialFocus
                />
              </PopoverContent>
            </Popover>
          </div>
        </div>
      </div>

      {/* Rebalancing Frequency */}
      <div className="space-y-2">
        <Label className="text-sm font-medium">Rebalancing Frequency</Label>
        <Select value={rebalanceFreq} onValueChange={setRebalanceFreq}>
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="quarterly">Quarterly</SelectItem>
            <SelectItem value="yearly">Yearly</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Portfolio Size */}
      <div className="space-y-2">
        <Label className="text-sm font-medium">Portfolio Size</Label>
        <div className="flex items-center space-x-2">
          <span className="text-sm text-muted-foreground">Top</span>
          <Input
            type="number"
            value={portfolioSize}
            onChange={(e) => setPortfolioSize(e.target.value)}
            className="w-20"
          />
          <span className="text-sm text-muted-foreground">stocks</span>
        </div>
      </div>

      {/* Initial Capital */}
      <div className="space-y-2">
        <Label className="text-sm font-medium">Initial Capital</Label>
        <div className="relative">
          <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground">₹</span>
          <Input
            type="number"
            value={initialCapital}
            onChange={(e) => setInitialCapital(e.target.value)}
            className="pl-8"
            placeholder="1000000"
          />
        </div>
      </div>

      {/* Weighting Method */}
      <div className="space-y-3">
        <Label className="text-sm font-medium">Weighting Method</Label>
        <RadioGroup value={weightingMethod} onValueChange={setWeightingMethod}>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="equal" id="equal" />
            <Label htmlFor="equal" className="text-sm">
              Equal-weighted
            </Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="market-cap" id="market-cap" />
            <Label htmlFor="market-cap" className="text-sm">
              Market cap-weighted
            </Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="roce" id="roce" />
            <Label htmlFor="roce" className="text-sm">
              Metric-weighted (ROCE)
            </Label>
          </div>
        </RadioGroup>
      </div>
    </div>
  );
}
