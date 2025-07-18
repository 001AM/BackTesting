import React from "react";
import Navbar from "@/components/Navbar";
import { Outlet } from "react-router-dom";

const Layout = () => {
  return (
    <div className="flex flex-col h-screen bg-background">
      <Navbar />
      <Outlet />
    </div>
  );
};

export default Layout;

