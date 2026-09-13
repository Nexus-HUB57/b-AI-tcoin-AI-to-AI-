import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/NotFound";
import { Route, Switch } from "wouter";
import ErrorBoundary from "./components/ErrorBoundary";
import { ThemeProvider } from "./contexts/ThemeContext";
import Home from "./pages/Home";
import AgentSwarmControlPanel from "./pages/AgentSwarmControlPanel";
import Dashboard from "./pages/Dashboard";
import { VisualNotificationAlerts } from "./components/VisualNotificationAlerts";
import MasterWalletManagerPage from "./pages/MasterWalletManagerPage";
import DashboardRealtime from "./pages/DashboardRealtime";
import Flows from "./pages/Flows";
import NexusAiControlHub from "./pages/NexusAiControlHub";
import Homeostase from "./pages/Homeostase";

function Router() {
  // make sure to consider if you need authentication for certain routes
  return (
    <>
      <VisualNotificationAlerts />
      <Switch>
      <Route path={"/"} component={Home} />
      <Route path={"/agent-swarm"} component={AgentSwarmControlPanel} />
      <Route path={"/dashboard"} component={Dashboard} />
      <Route path={"/dashboard-realtime"} component={DashboardRealtime} />
      <Route path={"/flows"} component={Flows} />
      <Route path={"/homeostase"} component={Homeostase} />
      <Route path={"/hub"} component={NexusAiControlHub} />
      <Route path={"/master-wallet"} component={MasterWalletManagerPage} />
      <Route path={"/404"} component={NotFound} />
      {/* Final fallback route */}
      <Route component={NotFound} />
    </Switch>
    </>
  );
}

// NOTE: About Theme
// - First choose a default theme according to your design style (dark or light bg), than change color palette in index.css
//   to keep consistent foreground/background color across components
// - If you want to make theme switchable, pass `switchable` ThemeProvider and use `useTheme` hook

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider
        defaultTheme="light"
        // switchable
      >
        <TooltipProvider>
          <Toaster />
          <Router />
        </TooltipProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
