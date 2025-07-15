import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { TrendingUp, Database, BarChart3, Settings, Download, GitBranch } from "lucide-react"
import { Link } from "react-router-dom";

function Footer() {
  return (
    <footer className="bg-gray-900 text-white py-12">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center space-x-2 mb-4">
                <TrendingUp className="h-6 w-6" />
                <span className="text-lg font-bold">QuantBacktest</span>
              </div>
              <p className="text-gray-400">Professional backtesting platform for equity-based investment strategies.</p>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Platform</h4>
              <ul className="space-y-2 text-gray-400">
                <li>
                  <Link href="/backtest">Backtest Engine</Link>
                </li>
                <li>
                  <Link href="/data">Data Management</Link>
                </li>
                <li>
                  <Link href="/results">Results Analysis</Link>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Features</h4>
              <ul className="space-y-2 text-gray-400">
                <li>Strategy Configuration</li>
                <li>Performance Analytics</li>
                <li>Risk Management</li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Resources</h4>
              <ul className="space-y-2 text-gray-400">
                <li>Documentation</li>
                <li>API Reference</li>
                <li>Support</li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 mt-8 pt-8 text-center text-gray-400">
            <p>&copy; 2024 QuantBacktest. Built for Qode Assignment.</p>
          </div>
        </div>
    </footer>
  )
}

export default Footer
