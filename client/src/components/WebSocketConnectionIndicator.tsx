import { useEffect, useState } from "react";
import { useWebSocketEvents } from "@/hooks/useWebSocketEvents";
import { AlertCircle, Wifi, WifiOff, Loader2 } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

/**
 * Componente de indicador de conexão WebSocket
 * Mostra status de conexão e oferece reconexão manual
 */
export function WebSocketConnectionIndicator() {
  const { state, connect, disconnect } = useWebSocketEvents();
  const [showAlert, setShowAlert] = useState(false);

  // Mostrar alerta quando houver erro
  useEffect(() => {
    if (state.error) {
      setShowAlert(true);
      const timeout = setTimeout(() => setShowAlert(false), 5000);
      return () => clearTimeout(timeout);
    }
  }, [state.error]);

  const getStatusIcon = () => {
    if (state.isConnecting) {
      return <Loader2 className="h-4 w-4 animate-spin text-yellow-600" />;
    }
    if (state.isConnected) {
      return <Wifi className="h-4 w-4 text-green-600" />;
    }
    return <WifiOff className="h-4 w-4 text-red-600" />;
  };

  const getStatusText = () => {
    if (state.isConnecting) {
      return `Conectando... (tentativa ${state.reconnectAttempts})`;
    }
    if (state.isConnected) {
      return `Conectado (${state.clientId?.slice(0, 8)}...)`;
    }
    return "Desconectado";
  };

  const getStatusColor = () => {
    if (state.isConnecting) return "bg-yellow-50 border-yellow-200";
    if (state.isConnected) return "bg-green-50 border-green-200";
    return "bg-red-50 border-red-200";
  };

  return (
    <>
      {/* Indicador Compacto */}
      <div className={`fixed bottom-4 right-4 p-3 rounded-lg border ${getStatusColor()} flex items-center gap-2 shadow-lg`}>
        {getStatusIcon()}
        <span className="text-sm font-medium">{getStatusText()}</span>
        {!state.isConnected && !state.isConnecting && (
          <Button
            size="sm"
            variant="ghost"
            onClick={connect}
            className="ml-2 h-6 px-2 text-xs"
          >
            Reconectar
          </Button>
        )}
      </div>

      {/* Alerta de Erro */}
      {showAlert && state.error && (
        <Alert variant="destructive" className="fixed bottom-20 right-4 w-80 shadow-lg">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            <p className="font-semibold">Erro de Conexão WebSocket</p>
            <p className="text-sm mt-1">{state.error.message}</p>
            <Button
              size="sm"
              variant="outline"
              onClick={connect}
              className="mt-2 w-full"
            >
              Tentar Reconectar
            </Button>
          </AlertDescription>
        </Alert>
      )}
    </>
  );
}

/**
 * Componente de status de conexão para headers
 */
export function WebSocketConnectionStatus() {
  const { state } = useWebSocketEvents();

  const getStatusColor = () => {
    if (state.isConnecting) return "text-yellow-600";
    if (state.isConnected) return "text-green-600";
    return "text-red-600";
  };

  const getStatusDot = () => {
    if (state.isConnecting) return "bg-yellow-600 animate-pulse";
    if (state.isConnected) return "bg-green-600 animate-pulse";
    return "bg-red-600";
  };

  return (
    <div className="flex items-center gap-2">
      <div className={`w-2 h-2 rounded-full ${getStatusDot()}`} />
      <span className={`text-xs font-medium ${getStatusColor()}`}>
        {state.isConnecting
          ? "Conectando..."
          : state.isConnected
            ? "Ao vivo"
            : "Offline"}
      </span>
    </div>
  );
}

/**
 * Componente de histórico de reconexões
 */
export function WebSocketReconnectionHistory() {
  const { state } = useWebSocketEvents();
  const [history, setHistory] = useState<Array<{ timestamp: number; status: string }>>([]);

  useEffect(() => {
    if (state.reconnectAttempts > 0) {
      setHistory((prev) => [
        ...prev,
        {
          timestamp: Date.now(),
          status: state.isConnected ? "conectado" : "tentando",
        },
      ]);
    }
  }, [state.reconnectAttempts, state.isConnected]);

  if (history.length === 0) return null;

  return (
    <div className="text-xs text-muted-foreground space-y-1">
      <p className="font-semibold">Histórico de Reconexão:</p>
      {history.slice(-5).map((item, idx) => (
        <p key={idx}>
          {new Date(item.timestamp).toLocaleTimeString()} - {item.status}
        </p>
      ))}
    </div>
  );
}
