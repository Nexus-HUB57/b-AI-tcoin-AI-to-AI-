import { useEffect, useRef, useState, useCallback } from "react";
import { io, Socket } from "socket.io-client";

/**
 * WebSocket Event Types
 */
export enum WebSocketEventType {
  // Sincronização TSRA
  SYNC_STARTED = "sync:started",
  SYNC_COMPLETED = "sync:completed",
  SYNC_FAILED = "sync:failed",

  // Eventos
  EVENT_RECEIVED = "event:received",
  EVENT_PROCESSED = "event:processed",
  EVENT_QUEUE_UPDATED = "event:queue:updated",

  // Comandos
  COMMAND_GENERATED = "command:generated",
  COMMAND_EXECUTED = "command:executed",
  COMMAND_QUEUE_UPDATED = "command:queue:updated",

  // Fluxos
  FLOW_TRIGGERED = "flow:triggered",
  FLOW_COMPLETED = "flow:completed",
  FLOW_FAILED = "flow:failed",

  // Homeostase
  HOMEOSTASE_UPDATED = "homeostase:updated",
  HOMEOSTASE_ALERT = "homeostase:alert",

  // Genesis
  GENESIS_EVOLVED = "genesis:evolved",
  GENESIS_EXPERIENCE = "genesis:experience",

  // Status
  STATUS_UPDATED = "status:updated",
  NUCLEUS_STATUS_CHANGED = "nucleus:status:changed",

  // Controle
  TSRA_STARTED = "tsra:started",
  TSRA_STOPPED = "tsra:stopped",
}

/**
 * WebSocket Payload
 */
export interface WebSocketPayload {
  timestamp: number;
  data: any;
  metadata?: {
    sourceNucleus?: string;
    flowType?: string;
    severity?: "info" | "warning" | "critical";
  };
}

/**
 * WebSocket Connection State
 */
export interface WebSocketState {
  isConnected: boolean;
  isConnecting: boolean;
  error: Error | null;
  clientId: string | null;
  reconnectAttempts: number;
  lastEventTime: number | null;
}

/**
 * Hook para gerenciar conexão WebSocket e eventos
 */
export function useWebSocketEvents() {
  const socketRef = useRef<Socket | null>(null);
  const [state, setState] = useState<WebSocketState>({
    isConnected: false,
    isConnecting: false,
    error: null,
    clientId: null,
    reconnectAttempts: 0,
    lastEventTime: null,
  });

  const eventListenersRef = useRef<Map<string, Set<Function>>>(new Map());
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  /**
   * Conectar ao servidor WebSocket
   */
  const connect = useCallback((): void => {
    if (socketRef.current?.connected) {
      return;
    }

    setState((prev) => ({ ...prev, isConnecting: true }));

    try {
      const socket = io(window.location.origin, {
        transports: ["websocket", "polling"],
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        reconnectionAttempts: 5,
      });

      // Handler de conexão
      socket.on("connect", () => {
        console.log("✅ WebSocket conectado:", socket.id);
        setState((prev) => ({
          ...prev,
          isConnected: true,
          isConnecting: false,
          error: null,
          clientId: socket.id || null,
          reconnectAttempts: 0,
        }));
      });

      // Handler de desconexão
      socket.on("disconnect", (reason) => {
        console.log("🔌 WebSocket desconectado:", reason);
        setState((prev) => ({
          ...prev,
          isConnected: false,
          isConnecting: false,
        }));
      });

      // Handler de erro
      socket.on("error", (error: any) => {
        console.error("❌ Erro WebSocket:", error);
        setState((prev) => ({
          ...prev,
          error: new Error(error?.message || "Erro de conexão WebSocket"),
        }));
      });

      // Handler de reconexão
      socket.on("reconnect_attempt", () => {
        setState((prev) => ({
          ...prev,
          reconnectAttempts: prev.reconnectAttempts + 1,
          isConnecting: true,
        }));
      });

      // Handler de pong (keep-alive)
      socket.on("server:pong", (data: any) => {
        // Keep-alive recebido
      });

      // Registrar listeners de eventos
      Object.values(WebSocketEventType).forEach((eventType) => {
        socket.on(eventType, (payload: WebSocketPayload) => {
          setState((prev) => ({
            ...prev,
            lastEventTime: Date.now(),
          }));

          // Chamar callbacks registrados
          const listeners = eventListenersRef.current.get(eventType);
          if (listeners) {
            listeners.forEach((listener) => {
              try {
                listener(payload);
              } catch (error) {
                console.error(`Erro ao processar evento ${eventType}:`, error);
              }
            });
          }
        });
      });

      socketRef.current = socket;
    } catch (error) {
      console.error("Erro ao conectar WebSocket:", error);
      setState((prev) => ({
        ...prev,
        isConnecting: false,
        error: error instanceof Error ? error : new Error("Erro desconhecido"),
      }));
    }
  }, []);

  /**
   * Desconectar do servidor WebSocket
   */
  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
    }

    if (reconnectTimeoutRef.current !== null) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    setState({
      isConnected: false,
      isConnecting: false,
      error: null,
      clientId: null,
      reconnectAttempts: 0,
      lastEventTime: null,
    });
  }, []);

  /**
   * Registrar listener para um evento
   */
  const addEventListener = useCallback((eventType: string, listener: Function) => {
    if (!eventListenersRef.current.has(eventType)) {
      eventListenersRef.current.set(eventType, new Set());
    }

    eventListenersRef.current.get(eventType)?.add(listener);

    // Retornar função para remover listener
    return () => {
      eventListenersRef.current.get(eventType)?.delete(listener);
    };
  }, []);

  /**
   * Remover todos os listeners de um evento
   */
  const removeEventListeners = useCallback((eventType: string) => {
    eventListenersRef.current.delete(eventType);
  }, []);

  /**
   * Enviar ping para manter conexão viva
   */
  const sendPing = useCallback(() => {
    if (socketRef.current?.connected) {
      socketRef.current.emit("client:ping");
    }
  }, []);

  /**
   * Conectar ao montar e desconectar ao desmontar
   */
  useEffect(() => {
    connect();

    // Keep-alive ping a cada 30 segundos
    const pingInterval = setInterval(() => {
      sendPing();
    }, 30000);

    return () => {
      clearInterval(pingInterval);
      disconnect();
    };
  }, [connect, disconnect, sendPing]);

  return {
    state,
    connect,
    disconnect,
    addEventListener,
    removeEventListeners,
    sendPing,
    isConnected: state.isConnected,
    isConnecting: state.isConnecting,
    error: state.error,
  };
}

/**
 * Hook para escutar eventos específicos
 */
export function useWebSocketEvent(
  eventType: string,
  callback: (payload: WebSocketPayload) => void,
  enabled: boolean = true
) {
  const { addEventListener, removeEventListeners } = useWebSocketEvents();

  useEffect(() => {
    if (!enabled) return;

    const unsubscribe = addEventListener(eventType, callback);

    return () => {
      unsubscribe();
    };
  }, [eventType, callback, enabled, addEventListener]);
}

/**
 * Hook para coletar eventos em um array
 */
export function useWebSocketEventHistory(
  eventType: string,
  maxSize: number = 100,
  enabled: boolean = true
) {
  const [events, setEvents] = useState<WebSocketPayload[]>([]);
  const { addEventListener } = useWebSocketEvents();

  useEffect(() => {
    if (!enabled) return;

    const unsubscribe = addEventListener(eventType, (payload: WebSocketPayload) => {
      setEvents((prev) => {
        const updated = [payload, ...prev];
        return updated.slice(0, maxSize);
      });
    });

    return () => {
      unsubscribe();
    };
  }, [eventType, maxSize, enabled, addEventListener]);

  return events;
}

/**
 * Hook para agregar eventos por tipo
 */
export function useWebSocketEventAggregation(
  eventTypes: string[],
  aggregationFn: (events: WebSocketPayload[]) => any,
  enabled: boolean = true
) {
  const [aggregated, setAggregated] = useState<any>(null);
  const eventsRef = useRef<Map<string, WebSocketPayload[]>>(new Map());
  const { addEventListener } = useWebSocketEvents();

  useEffect(() => {
    if (!enabled) return;

    const unsubscribers = eventTypes.map((eventType) =>
      addEventListener(eventType, (payload: WebSocketPayload) => {
        if (!eventsRef.current.has(eventType)) {
          eventsRef.current.set(eventType, []);
        }

        const events = eventsRef.current.get(eventType)!;
        events.unshift(payload);
        events.splice(50); // Manter últimos 50

        // Recalcular agregação
        const allEvents = Array.from(eventsRef.current.values()).flat();
        setAggregated(aggregationFn(allEvents));
      })
    );

    return () => {
      unsubscribers.forEach((unsubscribe) => unsubscribe());
    };
  }, [eventTypes, aggregationFn, enabled, addEventListener]);

  return aggregated;
}
