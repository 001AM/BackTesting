import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, Shield, Zap, Target } from "lucide-react";

const templates = [
  {
    id: "value",
    name: "Value Strategy",
    description: "Focus on undervalued stocks with strong fundamentals",
    icon: Shield,
    metrics: ["pe_ratio", "pb_ratio", "debt_equity_ratio"], // Use metric IDs that match availableMetrics
    color: "bg-blue-500",
  },
  // {
  //   id: "growth",
  //   name: "Growth Strategy",
  //   description: "Target companies with high growth potential",
  //   icon: TrendingUp,
  //   metrics: ["Revenue Growth", "Profit Growth", "ROE"],
  //   color: "bg-green-500",
  // },
  {
    id: "quality",
    name: "Quality Strategy",
    description: "Select high-quality companies with consistent performance",
    icon: Target,
    metrics: ["roce", "roe", "current_ratio"], // Use metric IDs that match availableMetrics
    color: "bg-purple-500",
  },
  // {
  //   id: "momentum",
  //   name: "Momentum Strategy",
  //   description: "Capitalize on price and earnings momentum",
  //   icon: Zap,
  //   metrics: ["Price Momentum", "Earnings Revision", "Revenue Growth"],
  //   color: "bg-orange-500",
  // },
];

export function StrategyTemplates({ onConfigChange }) {
  const applyTemplate = (templateId) => {
    console.log(`Applying template: ${templateId}`);
    let selectedTemplate = templates.find((template) => template.id === templateId);

    if (onConfigChange && selectedTemplate) {
      const rankingMetrics = selectedTemplate.metrics.map((metric) => ({
        [metric]: true,
      }));

      const templateConfig = {
        ranking_metrics: rankingMetrics,
      };

      onConfigChange(templateConfig);
    }
  };
  const getMetricDisplayName = (metricId) => {
    const metricMap = {
      roe: "ROE",
      pe_ratio: "P/E",
      roce: "ROCE",
      debt_equity_ratio: "Debt/Equity",
      current_ratio: "Current Ratio",
      pb_ratio: "P/BV",
    };
    return metricMap[metricId] || metricId;
  };

  return (
    <div className="space-y-4">
      <div className="text-sm text-muted-foreground">
        Quick-start with pre-configured strategies
      </div>

      <div className="grid grid-cols-1 gap-3">
        {templates.map((template) => {
          const Icon = template.icon;
          return (
            <Card
              key={template.id}
              className="cursor-pointer hover:shadow-md transition-shadow"
            >
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div
                      className={`w-8 h-8 ${template.color} rounded-lg flex items-center justify-center`}
                    >
                      <Icon className="w-4 h-4 text-white" />
                    </div>
                    <div>
                      <CardTitle className="text-sm">{template.name}</CardTitle>
                      <CardDescription className="text-xs">
                        {template.description}
                      </CardDescription>
                    </div>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="flex flex-wrap gap-1 mb-3">
                  {template.metrics.map((metric) => (
                    <Badge key={metric} variant="outline" className="text-xs">
                      {getMetricDisplayName(metric)}
                    </Badge>
                  ))}
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full bg-transparent"
                  onClick={() => applyTemplate(template.id)}
                >
                  Apply Template
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
