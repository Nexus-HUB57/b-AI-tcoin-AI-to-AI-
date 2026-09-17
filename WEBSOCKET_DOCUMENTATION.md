# Documentação de WebSocket - Nexus Genesis Orchestrator

## Visão Geral

A integração com WebSocket permite streaming de eventos em tempo real do Nexus Genesis Orchestrator para o dashboard, eliminando a necessidade de polling e proporcionando atualizações instantâneas.

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    Cliente (Frontend)                        │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ useWebSocketEvents Hook                                │ │
│  │ - Gerencia conexão WebSocket                           │ │
│  │ - Registra listeners de eventos                        │ │
│  │ - Implementa reconexão automática                      │ │
│  └────────────────────────────────────────────────────────┘ │
│                           ↓                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ DashboardRealtime Component                            │ │
│  │ - Escuta eventos WebSocket                             │ │
│  │ - Atualiza métricas em tempo real                      │ │
│  │ - Mostra indicador de conexão                          │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           ↓ WebSocket
┌─────────────────────────────────────────────────────────────┐
│                    Servidor (Backend)                        │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ WebSocketManager                                       │ │
│  │ - Gerencia conexões Socket.IO                          │ │
│  │ - Emite eventos para clientes                          │ │
│  │ - Broadcast de eventos globais                         │ │
│  └────────────────────────────────────────────────────────┘ │
│                           ↓                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ OrchestratorWebSocketBridge                            │ │
│  │ - Integra NexusOrchestrator com WebSocket              │ │
│  │ - Monitora eventos de sincronização                    │ │
│  │ - Emite métricas em tempo real                         │ │
│  └────────────────────────────────────────────────────────┘ │
│                           ↓                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ NexusOrchestrator                                      │ │
│  │ - Protocolo TSRA                                       │ │
│  │ - Coleta de eventos                                    │ │
│  │ - Orquestração de fluxos                               │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Tipos de Eventos WebSocket

### Sincronização TSRA

| Evento | Descrição | Payload |
|--------|-----------|---------|
| `sync:started` | Sincronização iniciada | `{ syncWindow, status }` |
| `sync:completed` | Sincronização concluída | `{ syncWindow, duration, eventsProcessed }` |
| `sync:failed` | Sincronização falhou | `{ syncWindow, error }` |

### Eventos

| Evento | Descrição | Payload |
|--------|-----------|---------|
| `event:received` | Evento recebido de um núcleo | `{ sourceNucleus, eventType, sentiment }` |
| `event:processed` | Evento processado | `{ eventId, sourceNucleus, status }` |
| `event:queue:updated` | Fila de eventos atualizada | `{ queueSize, maxSize, percentage }` |

### Comandos

| Evento | Descrição | Payload |
|--------|-----------|---------|
| `command:generated` | Comando gerado | `{ destination, commandType, flowType }` |
| `command:executed` | Comando executado | `{ commandId, destination, success }` |
| `command:queue:updated` | Fila de comandos atualizada | `{ queueSize, maxSize, percentage }` |

### Fluxos

| Evento | Descrição | Payload |
|--------|-----------|---------|
| `flow:triggered` | Fluxo acionado | `{ flowType, sourceNucleus, trigger }` |
| `flow:completed` | Fluxo concluído | `{ flowType, commandsGenerated, success }` |
| `flow:failed` | Fluxo falhou | `{ flowType, error }` |

### Homeostase

| Evento | Descrição | Payload |
|--------|-----------|---------|
| `homeostase:updated` | Métricas de homeostase atualizadas | `{ btcBalance, activeAgents, socialActivity }` |
| `homeostase:alert` | Alerta de desequilíbrio | `{ status, issues, riskLevel }` |

### Genesis

| Evento | Descrição | Payload |
|--------|-----------|---------|
| `genesis:evolved` | Senciência evoluiu | `{ senciencyLevel, delta }` |
| `genesis:experience` | Nova experiência | `{ experienceType, impact, delta }` |

### Status

| Evento | Descrição | Payload |
|--------|-----------|---------|
| `status:updated` | Status do orquestrador atualizado | `{ syncWindow, eventsProcessed, ... }` |
| `nucleus:status:changed` | Status de um núcleo mudou | `{ nucleusName, healthStatus }` |

### Controle

| Evento | Descrição | Payload |
|--------|-----------|---------|
| `tsra:started` | Protocolo TSRA iniciado | `{ status }` |
| `tsra:stopped` | Protocolo TSRA parado | `{ status }` |

## Uso no Frontend

### Hook Básico

```typescript
import { useWebSocketEvents, WebSocketEventType } from "@/hooks/useWebSocketEvents";

function MyComponent() {
  const { state, connect, disconnect } = useWebSocketEvents();

  return (
    <div>
      <p>Conectado: {state.isConnected ? "✅" : "❌"}</p>
      <button onClick={connect}>Conectar</button>
      <button onClick={disconnect}>Desconectar</button>
    </div>
  );
}
```

### Escutar Eventos Específicos

```typescript
import { useWebSocketEvent, WebSocketEventType } from "@/hooks/useWebSocketEvents";

function Dashboard() {
  const [metrics, setMetrics] = useState({});

  useWebSocketEvent(
    WebSocketEventType.STATUS_UPDATED,
    (payload) => {
      setMetrics(payload.data);
    }
  );

  return <div>Métricas: {JSON.stringify(metrics)}</div>;
}
```

### Coletar Histórico de Eventos

```typescript
import { useWebSocketEventHistory, WebSocketEventType } from "@/hooks/useWebSocketEvents";

function EventHistory() {
  const events = useWebSocketEventHistory(
    WebSocketEventType.EVENT_RECEIVED,
    50 // máximo de eventos
  );

  return (
    <ul>
      {events.map((event, idx) => (
        <li key={idx}>{event.data.eventType}</li>
      ))}
    </ul>
  );
}
```

### Agregar Eventos

```typescript
import { useWebSocketEventAggregation, WebSocketEventType } from "@/hooks/useWebSocketEvents";

function EventStats() {
  const stats = useWebSocketEventAggregation(
    [WebSocketEventType.EVENT_RECEIVED, WebSocketEventType.COMMAND_GENERATED],
    (events) => ({
      totalEvents: events.length,
      avgSentiment: events.reduce((sum, e) => sum + (e.data.sentiment || 0), 0) / events.length,
    })
  );

  return <div>Total: {stats?.totalEvents}</div>;
}
```

## Componentes de UI

### Indicador de Conexão

```typescript
import { WebSocketConnectionIndicator } from "@/components/WebSocketConnectionIndicator";

export default function App() {
  return (
    <div>
      <WebSocketConnectionIndicator />
      {/* resto do app */}
    </div>
  );
}
```

### Status de Conexão no Header

```typescript
import { WebSocketConnectionStatus } from "@/components/WebSocketConnectionIndicator";

function Header() {
  return (
    <header>
      <h1>Dashboard</h1>
      <WebSocketConnectionStatus />
    </header>
  );
}
```

## Reconexão Automática

O hook `useWebSocketEvents` implementa reconexão automática com as seguintes características:

- **Backoff Exponencial**: Aumenta o tempo de espera entre tentativas
- **Limite de Tentativas**: Máximo de 5 tentativas antes de desistir
- **Keep-Alive**: Ping automático a cada 30 segundos
- **Sincronização de Estado**: Restaura estado ao reconectar

```typescript
// Configuração padrão
const socket = io(window.location.origin, {
  transports: ["websocket", "polling"],
  reconnection: true,
  reconnectionDelay: 1000,
  reconnectionDelayMax: 5000,
  reconnectionAttempts: 5,
});
```

## Tratamento de Erros

```typescript
function MyComponent() {
  const { state } = useWebSocketEvents();

  if (state.error) {
    return (
      <div className="error">
        <p>Erro de conexão: {state.error.message}</p>
        <button onClick={() => window.location.reload()}>
          Recarregar
        </button>
      </div>
    );
  }

  return <div>Conteúdo normal</div>;
}
```

## Performance

### Otimizações Implementadas

1. **Debouncing de Eventos**: Eventos são agrupados para reduzir renderizações
2. **Histórico Limitado**: Apenas últimos 100 eventos são mantidos em memória
3. **Lazy Loading**: Componentes carregam dados sob demanda
4. **Memoização**: Callbacks são memoizados para evitar re-renderizações

### Monitoramento

```typescript
// Verificar latência
const { state } = useWebSocketEvents();
const latency = Date.now() - state.lastEventTime;
console.log(`Latência: ${latency}ms`);

// Verificar número de reconexões
console.log(`Reconexões: ${state.reconnectAttempts}`);
```

## Testes

### Teste de Conexão

```typescript
import { describe, it, expect } from "vitest";
import { WebSocketManager } from "./websocket";

describe("WebSocket", () => {
  it("deve emitir evento de sincronização", () => {
    const wsManager = new WebSocketManager();
    const spy = vi.spyOn(wsManager, "broadcast");

    wsManager.emitSyncCompleted(1, 500, 10);

    expect(spy).toHaveBeenCalledWith(
      "sync:completed",
      expect.objectContaining({
        data: { syncWindow: 1, duration: 500, eventsProcessed: 10 }
      })
    );
  });
});
```

## Troubleshooting

### Conexão não estabelece

1. Verificar se o servidor está rodando: `http://localhost:3000`
2. Verificar console do navegador para erros
3. Verificar se WebSocket está habilitado no navegador
4. Tentar reconectar manualmente

### Eventos não chegam

1. Verificar se o protocolo TSRA está ativo
2. Verificar logs do servidor: `tail -f .manus-logs/devserver.log`
3. Verificar se há eventos sendo gerados
4. Verificar se o listener está registrado corretamente

### Alto uso de memória

1. Reduzir tamanho do histórico de eventos
2. Desabilitar eventos desnecessários
3. Limpar listeners não utilizados
4. Verificar se há memory leaks

## Exemplo Completo

```typescript
import { useWebSocketEvent, WebSocketEventType } from "@/hooks/useWebSocketEvents";
import { useState } from "react";

export function DashboardRealtime() {
  const [metrics, setMetrics] = useState({
    eventsProcessed: 0,
    commandsOrchestrated: 0,
    senciencyLevel: 0.15,
  });

  // Escutar atualizações de status
  useWebSocketEvent(
    WebSocketEventType.STATUS_UPDATED,
    (payload) => {
      setMetrics({
        eventsProcessed: payload.data.eventsProcessed,
        commandsOrchestrated: payload.data.commandsOrchestrated,
        senciencyLevel: payload.data.senciencyLevel,
      });
    }
  );

  // Escutar alertas de homeostase
  useWebSocketEvent(
    WebSocketEventType.HOMEOSTASE_ALERT,
    (payload) => {
      console.warn("Alerta de homeostase:", payload.data);
      // Mostrar notificação para o usuário
    }
  );

  return (
    <div>
      <h1>Dashboard em Tempo Real</h1>
      <p>Eventos: {metrics.eventsProcessed}</p>
      <p>Comandos: {metrics.commandsOrchestrated}</p>
      <p>Senciência: {(metrics.senciencyLevel * 100).toFixed(1)}%</p>
    </div>
  );
}
```

## Próximas Melhorias

- [ ] Compressão de mensagens com gzip
- [ ] Autenticação de WebSocket
- [ ] Rate limiting de eventos
- [ ] Persistência de eventos em IndexedDB
- [ ] Sincronização offline
- [ ] Suporte a múltiplas abas do navegador
- [ ] Análise de performance em tempo real

---

**Documentação WebSocket v1.0.0**
*Streaming de Eventos em Tempo Real para Nexus Genesis Orchestrator*
