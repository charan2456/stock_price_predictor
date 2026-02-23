import { createBrowserRouter } from "react-router";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { Predictions } from "./pages/Predictions";
import { SentimentFeed } from "./pages/SentimentFeed";
import { Portfolio } from "./pages/Portfolio";
import { Watchlist } from "./pages/Watchlist";
import { Comparison } from "./pages/Comparison";
import { BacktestResults } from "./pages/BacktestResults";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Layout,
    children: [
      { index: true, Component: Dashboard },
      { path: "predictions", Component: Predictions },
      { path: "sentiment", Component: SentimentFeed },
      { path: "portfolio", Component: Portfolio },
      { path: "watchlist", Component: Watchlist },
      { path: "compare", Component: Comparison },
      { path: "backtest", Component: BacktestResults },
    ],
  },
]);
