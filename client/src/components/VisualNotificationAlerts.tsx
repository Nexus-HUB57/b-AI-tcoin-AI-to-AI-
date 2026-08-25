import React, { useState, useEffect } from "react";
import { AlertCircle, CheckCircle2, Bell, X, ShieldAlert, Cpu } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export interface SystemNotification {
  id: string;
  title: string;
  message: string;
  type: "SUCCESS" | "WARNING" | "ERROR" | "INFO";
  timestamp: number;
}

export function VisualNotificationAlerts() {
  const [notifications, setNotifications] = useState<SystemNotification[]>([
    {
      id: "notif-init",
      title: "Cluster de 20 Workers Ativo",
      message: "Absorção de núcleos nativos Zettascale operando sob Master Passphrase.",
      type: "SUCCESS",
      timestamp: Date.now() - 10000
    }
  ]);

  // Simular evento de teste ou alerta de falha de worker após alguns segundos
  useEffect(() => {
    const timer = setTimeout(() => {
      setNotifications((prev) => [
        {
          id: `notif-${Date.now()}`,
          title: "Tarefa Pesada Concluída",
          message: "Worker #14 finalizou sintese neural-symbolic com sucesso (Confirmações: 6+).",
          type: "SUCCESS",
          timestamp: Date.now()
        },
        ...prev.slice(0, 4)
      ]);
    }, 5000);
    return () => clearTimeout(timer);
  }, []);

  const dismissNotification = (id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  if (notifications.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-3 max-w-sm w-full px-4">
      {notifications.map((n) => (
        <div
          key={n.id}
          className={`p-4 rounded-xl shadow-lg border backdrop-blur-md flex items-start justify-between gap-3 transition-all animate-in fade-in slide-in-from-bottom-3 ${
            n.type === "SUCCESS"
              ? "bg-emerald-950/80 border-emerald-500/30 text-emerald-100"
              : n.type === "ERROR"
              ? "bg-rose-950/80 border-rose-500/30 text-rose-100"
              : "bg-card/90 border-border text-foreground"
          }`}
        >
          <div className="flex items-start gap-3">
            {n.type === "SUCCESS" && <CheckCircle2 className="w-5 h-5 text-emerald-400 mt-0.5 shrink-0" />}
            {n.type === "ERROR" && <ShieldAlert className="w-5 h-5 text-rose-400 mt-0.5 shrink-0" />}
            {n.type === "INFO" && <Bell className="w-5 h-5 text-primary mt-0.5 shrink-0" />}
            {n.type === "WARNING" && <AlertCircle className="w-5 h-5 text-amber-400 mt-0.5 shrink-0" />}
            <div>
              <h4 className="font-semibold text-sm">{n.title}</h4>
              <p className="text-xs opacity-90 mt-1">{n.message}</p>
              <span className="text-[10px] opacity-70 mt-2 block">
                {new Date(n.timestamp).toLocaleTimeString()}
              </span>
            </div>
          </div>
          <button
            onClick={() => dismissNotification(n.id)}
            className="text-muted-foreground hover:text-foreground transition-colors p-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      ))}
    </div>
  );
}
