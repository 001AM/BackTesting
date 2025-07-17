import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ChevronDown, ChevronRight } from "lucide-react";
import { BasicConfig } from "@/components/BasicConfig";
import { FilteringSystem } from "@/components/FilteringSystem";
import { RankingSystem } from "@/components/RankingSystem";
import { StrategyTemplates } from "@/components/StrategyTemplates";

export function ConfigurationPanel() {
  const [openSections, setOpenSections] = useState({
    basic: true,
    filters: true,
    ranking: false,
    templates: false,
  });

  const toggleSection = (section) => {
    setOpenSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const sections = [
    { key: "basic", title: "Basic Configuration", component: BasicConfig },
    { key: "filters", title: "Filtering System", component: FilteringSystem },
    { key: "ranking", title: "Ranking System", component: RankingSystem },
    { key: "templates", title: "Strategy Templates", component: StrategyTemplates },
  ];

  return (
    <div className="space-y-4">
      {sections.map(({ key, title, component: Component }) => (
        <Card key={key}>
          <Collapsible
            open={openSections[key]}
            onOpenChange={() => toggleSection(key)}
            
          >
            <CollapsibleTrigger asChild>
              <CardHeader className="cursor-pointer hover:bg-muted transition-colors">
                <CardTitle className="flex items-center justify-between text-sm">
                  {title}
                  {openSections[key] ? (
                    <ChevronDown className="w-4 h-4" />
                  ) : (
                    <ChevronRight className="w-4 h-4" />
                  )}
                </CardTitle>
              </CardHeader>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <CardContent className="m-2">
                <Component />
              </CardContent>
            </CollapsibleContent>
          </Collapsible>
        </Card>
      ))}
    </div>
  );
}

export default ConfigurationPanel;
