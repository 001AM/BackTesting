import { useState, useEffect } from "react";
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

export function FilteringSystem({onConfigChange}) {
  const [marketCapRange, setMarketCapRange] = useState([1000, 100000]);
  const [roceThreshold, setRoceThreshold] = useState("15");
  const [patThreshold, setPatThreshold] = useState("0");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [peRatio, setPeRatio] = useState("");
  const [debtEquity, setDebtEquity] = useState("");
  
  const parseRange = (rangeString) => {
    if (!rangeString) return { min: null, max: null };
    
    if (rangeString.includes('+')) {
      const min = parseFloat(rangeString.replace('+', ''));
      return { min, max: null };
    }
    
    const [min, max] = rangeString.split('-').map(val => parseFloat(val));
    return { min: min || null, max: max || null };
  };

  useEffect(() => {
    if (onConfigChange) {
      const peRange = parseRange(peRatio);
      const debtRange = parseRange(debtEquity);
      
      onConfigChange({
        min_market_cap: marketCapRange[0],
        max_market_cap: marketCapRange[1],
        min_roce: parseFloat(roceThreshold) || 0,
        pat_positive: parseFloat(patThreshold) || 0,
        min_pe_ratio: peRange.min,
        max_pe_ratio: peRange.max,
        min_debt_equity: debtRange.min,
        max_debt_equity: debtRange.max,
      });
    }
  }, [marketCapRange, roceThreshold, patThreshold, peRatio, debtEquity, onConfigChange]);

  return (
    <div className="space-y-6">
      {/* Market Cap Filter */}
      <div className="space-y-4">
        <Label className="text-sm font-medium">Market Cap Range</Label>
        <div className="px-2">
          <Slider
            value={marketCapRange}
            onValueChange={setMarketCapRange}
            max={1000000}
            min={1000}
            step={1000}
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
      <div className="space-y-2">
        <Label className="text-sm font-medium">PAT Threshold</Label>
        <div className="relative">
          <Input
            type="number"
            value={patThreshold}
            onChange={(e) => setPatThreshold(e.target.value)}
            className="pr-8"
            placeholder="0"
          />
          <span className="absolute right-3 top-1/2 transform -translate-y-1/2 text-muted-foreground">
            Cr
          </span>
        </div>
      </div>
    </div>
  );
}
