import { Navigate } from "react-router-dom";
import Layout from "@/layout/Layout";
import NotFound from "@/pages/notfound/NotFound";
import Home from "@/pages/home/Home";
import Data from "@/pages/data/Data"
import BackTesting from "@/pages/backtesting/BackTesting";

const routesConfig = [
  {
    path: "/",
    element: <Layout />,
    children: [
      {
        index: true, // Optional: redirect to /home
        element: <Navigate to="home" replace />
      },
      {
        path: "home",
        element: <Home />
      },
      {
        path: "data",
        element: <Data/>
      },
      {
        path: "backtest",
        element: <BackTesting/>
      }
    ]
  },
  {
    path: "*", // Catch all unmatched top-level routes
    element: <NotFound />
  }
];

export default routesConfig;

