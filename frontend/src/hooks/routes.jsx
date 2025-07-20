import { Navigate } from "react-router-dom";
import Layout from "@/layout/Layout";
import NotFound from "@/pages/notfound/NotFound";
import Home from "@/pages/home/Home";
import Data from "@/pages/data/Data";
import BackTesting from "@/pages/backtesting/BackTesting";

const routesConfig = [
  {
    path: "/",
    element: <Layout />,
    children: [
      {
        path: "",
        element: <Home /> // ✅ Show Home at /
      },
      {
        path: "data",
        element: <Data />
      },
      {
        path: "backtest",
        element: <BackTesting />
      }
    ]
  },
  {
    path: "*",
    element: <NotFound />
  }
];

export default routesConfig;
