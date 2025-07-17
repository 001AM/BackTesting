import { useState } from "react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { ChevronDown } from "lucide-react";

export function FilteringSystem() {
  const [marketCapRange, setMarketCapRange] = useState([1000, 10000]);
  const [roceThreshold, setRoceThreshold] = useState("15");
  const [patPositive, setPatPositive] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [peRatio, setPeRatio] = useState("");
  const [debtEquity, setDebtEquity] = useState("");

  return (
    <div className="space-y-6">
      {/* Market Cap Filter */}
      <div className="space-y-4">
        <Label className="text-sm font-medium">Market Cap Range</Label>
        <div className="px-2">
          <Slider
            value={marketCapRange}
            onValueChange={setMarketCapRange}
            max={50000}
            min={100}
            step={100}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-muted-foreground mt-2">
            <span>₹{marketCapRange[0]} Cr</span>
            <span>₹{marketCapRange[1]} Cr</span>
          </div>
        </div>
      </div>

      {/* ROCE Threshold */}
      <div className="space-y-2">
        <Label className="text-sm font-medium">ROCE Threshold</Label>
        <div className="relative">
          <Input
            type="number"
            value={roceThreshold}
            onChange={(e) => setRoceThreshold(e.target.value)}
            className="pr-8"
            placeholder="15"
          />
          <span className="absolute right-3 top-1/2 transform -translate-y-1/2 text-muted-foreground">
            %
          </span>
        </div>
      </div>

      {/* PAT Filter */}
      <div className="flex items-center justify-between">
        <Label className="text-sm font-medium">PAT {">"} 0 Filter</Label>
        <Switch checked={patPositive} onCheckedChange={setPatPositive} />
      </div>

      {/* Advanced Filters */}
      <Card>
        <Collapsible open={showAdvanced} onOpenChange={setShowAdvanced}>
          <CollapsibleTrigger asChild>
            <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors">
              <CardTitle className="flex items-center justify-between text-sm">
                Additional Filters
                <ChevronDown
                  className={`w-4 h-4 transition-transform ${
                    showAdvanced ? "rotate-180" : ""
                  }`}
                />
              </CardTitle>
            </CardHeader>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                {/* P/E Ratio */}
                <div className="space-y-2">
                  <Label className="text-xs font-medium">P/E Ratio</Label>
                  <Select value={peRatio} onValueChange={setPeRatio}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select range" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="0-15">0 - 15</SelectItem>
                      <SelectItem value="15-25">15 - 25</SelectItem>
                      <SelectItem value="25-50">25 - 50</SelectItem>
                      <SelectItem value="50+">50+</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Debt-to-Equity */}
                <div className="space-y-2">
                  <Label className="text-xs font-medium">Debt-to-Equity</Label>
                  <Select value={debtEquity} onValueChange={setDebtEquity}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select range" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="0-0.5">0 - 0.5</SelectItem>
                      <SelectItem value="0.5-1">0.5 - 1.0</SelectItem>
                      <SelectItem value="1-2">1.0 - 2.0</SelectItem>
                      <SelectItem value="2+">2.0+</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </CollapsibleContent>
        </Collapsible>
      </Card>
    </div>
  );
}
