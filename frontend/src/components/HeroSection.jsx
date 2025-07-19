import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  TrendingUp,
  Database,
} from "lucide-react";
import { Link } from "react-router-dom";

function HeroSection() {
  return (
    <section className="py-20">
      <div className="container mx-auto px-4 text-center">
        <Badge variant="bg-secondary" className="mb-4">
          Full-Stack Backtesting Platform
        </Badge>
        <h2 className="text-5xl font-bold text-gray-900 mb-6">
          Backtest Your Equity Strategies
          <span className="text-blue-600"> with Precision</span>
        </h2>
        <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
          A comprehensive platform for testing fundamental analysis strategies
          on Indian equities. Configure custom filters, ranking systems, and
          position sizing methods to validate your investment approach.
        </p>
        <div className="flex justify-center space-x-4">
          <Link to="/backtest">
            <Button size="lg" className="bg-blue-600 hover:bg-blue-700">
              Start Backtesting
              <TrendingUp className="ml-2 h-5 w-5" />
            </Button>
          </Link>
          <Link to="/data">
            <Button size="lg" variant="outline">
              View Data
              <Database className="ml-2 h-5 w-5" />
            </Button>
          </Link>
        </div>
      </div>
    </section>
  );
}

export default HeroSection;
