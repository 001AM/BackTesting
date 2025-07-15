import React from "react";
import { TrendingUp } from "lucide-react";
import { Link } from "react-router-dom";

const Navbar = () => {
  return (
    <div className="flex items-center justify-between min-h-18 w-full border-b border-gray-200 pl-10 pr-10 bg-white shadow-sm">
      {/* Logo Section */}
      <div className="flex items-center space-x-2">
        <TrendingUp color="#026af2" className="h-8 w-8" />
        <span className="text-2xl font-[800] text-gray-900 ">QuantAnalysis</span>
      </div>

      {/* Menu Items */}
      <div className="flex space-x-6 text-base font-[600] text-gray-700">
        <Link to="/backtest" className="hover:text-blue-600 transition-colors">Backtest</Link>
        <Link to="/data" className="hover:text-blue-600 transition-colors">Data</Link>
        <Link to="/results" className="hover:text-blue-600 transition-colors">Results</Link>
      </div>
    </div>
  );
};

export default Navbar;

