import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ChevronDown, ChevronRight } from "lucide-react";
import { BasicConfig } from "@/components/BasicConfig";
import { FilteringSystem } from "@/components/FilteringSystem";
import { RankingSystem } from "@/components/RankingSystem";
import { StrategyTemplates } from "@/components/StrategyTemplates";
import { Button } from "./ui/button";
import { Play } from "lucide-react";
import { RefreshCcw } from "lucide-react";
import { ChevronLeft } from "lucide-react";
import { useEffect } from "react";

export function ConfigurationPanel({setBasicConfig, setRankingConfig, setFilters, setisExpanded, isRunning, handleRunBacktest, isExpanded, setSelectedStrategy, rankingConfig, selectedStrategy}) {
  const [openSections, setOpenSections] = useState({
    basic: true,
    filters: true,
    ranking: false,
    templates: false,
  });

  const toggleSection = (section) => {
    setisExpanded(false)
    setOpenSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  useEffect(()=>{
    if(openSections.basic || openSections.filters || openSections.ranking || openSections.templates) {
      setisExpanded(false);
    }
    else {
      setisExpanded(true);
    }
  },[openSections])

  const toggleSidebar = () => {
    setisExpanded(!isExpanded);
    if(openSections.basic || openSections.filters || openSections.ranking || openSections.templates) {
      setOpenSections({
        basic: false,
        filters: false,
        ranking: false,
        templates: false,
      });
    }
  }

  const handleFilters = () => {
    setOpenSections({
      basic: false,
      filters: false,
      ranking: false,
      templates: false,
    });
    handleRunBacktest()
  }

  const sections = [
    { key: "basic", title: "Basic Configuration", component: BasicConfig, propFunctions: setBasicConfig, propData: null },
    { key: "filters", title: "Filtering System", component: FilteringSystem, propFunctions: setFilters, propData: null },
    { key: "ranking", title: "Ranking System", component: RankingSystem, propFunctions: setRankingConfig, propData: rankingConfig?.ranking_metrics },
    { key: "templates", title: "Strategy Templates", component: StrategyTemplates, propFunctions: setSelectedStrategy, propData: selectedStrategy },
  ];

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center p-4 rounded-t-lg">
      <h2 className="text-lg font-semibold">Configuration</h2>
          {isExpanded ? <ChevronRight onClick={()=>toggleSidebar()} className="w-4 h-4 hidden lg:block" /> : <ChevronLeft onClick={()=>toggleSidebar()} className="w-4 h-4 hidden lg:block" />}
          </div>

      <Card>
        <CardContent>
          <Button 
          onClick={handleFilters} disabled={isRunning}
           size="lg" className="w-full">
            {isRunning ? <RefreshCcw className="w-4 h-4 mr-2 animate-spin" /> : <Play className="w-4 h-4 mr-2" />}
            <span className="lg:hidden">{isRunning ? "Running Backtest..." : "Run Backtest"}</span>
            <span className="hidden lg:inline">{isExpanded ? "" : (isRunning ? "Running Backtest..." : "Run Backtest")}</span>
          </Button>
        </CardContent>
      </Card>
      {sections.map(({ key, title, component: Component, propFunctions, propData }) => (
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
            <div className={`transition-all duration-200 ${openSections[key] ? 'block' : 'hidden'}`}>
              <CardContent className="m-2">
                <Component onConfigChange={propFunctions} propData={propData}/>
              </CardContent>
            </div>
          </Collapsible>
        </Card>
      ))}
    </div>
  );
}

export default ConfigurationPanel;
