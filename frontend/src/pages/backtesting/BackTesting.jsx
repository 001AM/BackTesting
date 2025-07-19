import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ConfigurationPanel } from "@/components/ConfigurationPanel";
import ResultsDashboard from "@/components/ResultsDashboard";
import { Play } from "lucide-react";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/axios";

export default function BacktestingPlatform() {
  const [Data, Setdata] = useState()

  const [isRunning, setIsRunning] = useState(false);
  const [hasResults, setHasResults] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);

  const [basicConfig, setBasicConfig] = useState({
    start_date: null,
    end_date: null,
    rebalancing_frequency: "quarterly",
    portfolio_size: 20,
    initial_capital: 1000000,
    weighting_method: "equal",
  });

  const [filters, setFilters] = useState({
    min_market_cap: 1000,
    max_market_cap: 10000,
    min_roce: 15,
    pat_positive: true,
    min_pe_ratio: null,
    max_pe_ratio: null,
    min_debt_equity: null,
    max_debt_equity: null,
  });

  const [rankingConfig, setRankingConfig] = useState({
    ranking_metrics: [{ roe: true }, { roce: true }],
  });

  const handleRunBacktest = async () => {
    setIsRunning(true);
    const finalConfig = {
      ...basicConfig,
      ...filters,
      ...rankingConfig,
    };

    console.log("Final config:", finalConfig);
    const res = await api.post("/backtest/backtest", finalConfig)
    console.log("Backtest response:", res.data)
    Setdata(res.data.data)
    setIsRunning(false);
    setIsExpanded(true);
    setHasResults(true);
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto px-4 py-6">
        <div className="px-3">
          <div className="flex flex-col lg:flex-row gap-6 h-full">
            {/* Configuration Panel */}
            <motion.div
              className="w-full lg:flex-shrink-0"
              initial={false}
              animate={{
                width:
                  typeof window !== "undefined" && window.innerWidth >= 1024
                    ? isExpanded
                      ? "200px"
                      : "400px"
                    : "100%",
              }}
              transition={{
                duration: 0.5,
                ease: [0.25, 0.1, 0.25, 1.0],
              }}
            >
              <ConfigurationPanel
                setisExpanded={setIsExpanded}
                setBasicConfig={setBasicConfig}
                setRankingConfig={setRankingConfig}
                setFilters={setFilters}
                isRunning={isRunning}
                handleRunBacktest={handleRunBacktest}
                isExpanded={isExpanded}
              />
            </motion.div>

            {/* Results Dashboard */}
            <motion.div
              className="w-full lg:flex-1 lg:min-w-0"
              initial={false}
              animate={{
                opacity: hasResults ? 1 : 1,
              }}
              transition={{
                duration: 0.3,
                delay: hasResults ? 0.2 : 0,
              }}
            >
              <AnimatePresence mode="wait">
                {hasResults ? (
                  <motion.div
                    key="results"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    transition={{
                      duration: 0.4,
                      ease: [0.25, 0.1, 0.25, 1.0],
                    }}
                  >
                    <ResultsDashboard data={Data} />
                  </motion.div>
                ) : (
                  <motion.div
                    key="placeholder"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.3 }}
                  >
                    <Card className="p-8 text-center h-full flex items-center justify-center min-h-[400px] lg:min-h-0">
                      <div className="space-y-4">
                        <motion.div
                          className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto cursor-pointer"
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                          onClick={handleRunBacktest}
                        >
                          <Play className="w-8 h-8 text-muted-foreground" />
                        </motion.div>
                        <h3 className="text-lg font-semibold">
                          Ready to Backtest
                        </h3>
                        <p className="text-muted-foreground max-w-md">
                          Configure your strategy parameters and click "Run
                          Backtest" to see results
                        </p>
                      </div>
                    </Card>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  );
}
