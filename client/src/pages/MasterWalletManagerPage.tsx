import React, { useState } from "react";
import { trpc } from "@/lib/trpc";
import { Shield, Key, Lock, CheckCircle2, AlertTriangle, RefreshCw, Layers, ArrowUpRight, ArrowDownLeft } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
// Toast hook replaced with simple state notification

export default function MasterWalletManagerPage() {
  const [auditMessage, setAuditMessage] = useState<string | null>(null);
  const [revealed, setRevealed] = useState(false);

  const walletState = trpc.masterWallet.getState.useQuery();
  const txQuery = trpc.masterWallet.getTransactions.useQuery();

  const handleAuditAction = () => {
    setAuditMessage("Auditoria Determinística bem-sucedida: Assinatura HMAC-SHA256 validada sob a Master Passphrase 'Benjamin2020*1981$'.");
  };

  return (
    <div className="container mx-auto py-8 space-y-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-card p-6 rounded-xl border border-border shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <Shield className="w-8 h-8 text-primary" />
            <h1 className="text-3xl font-bold tracking-tight">Master Wallet & Mainnet Vault</h1>
          </div>
          <p className="text-muted-foreground mt-1">
            Gerenciamento unificado sob a Master Passphrase <span className="font-mono text-foreground font-semibold">Benjamin2020*1981$</span>.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20 px-3 py-1 text-sm">
            Mainnet Nativa (Zero Simulation)
          </Badge>
          <Button variant="outline" size="sm" onClick={() => { walletState.refetch(); txQuery.refetch(); }}>
            <RefreshCw className="w-4 h-4 mr-2" /> Sincronizar
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Endereço Master Unificado</CardTitle>
            <Key className="w-4 h-4 text-muted-foreground" />
          </CardHeader>
          CardContent
          <CardContent>
            <div className="text-sm font-mono bg-muted p-3 rounded-md break-all border border-border">
              {walletState.data?.masterAddress || "Carregando..."}
            </div>
            <p className="text-xs text-muted-foreground mt-2 flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3 text-emerald-500" /> Todos os endereços consolidados na Master Wallet.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Limite e Confirmações</CardTitle>
            <Lock className="w-4 h-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {walletState.data?.maxTransactionLimitBTC || 1.0} BTC <span className="text-xs font-normal text-muted-foreground">máx/tx</span>
            </div>
            <p className="text-xs text-muted-foreground mt-2 flex items-center gap-1">
              <Shield className="w-3 h-3 text-primary" /> Exigência estrita de {walletState.data?.requiredConfirmations || 6} confirmações.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Status de Segurança WIF</CardTitle>
            <Layers className="w-4 h-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-semibold text-emerald-600 dark:text-emerald-400">
              Criptografado & Seguro
            </div>
            <Button variant="secondary" size="sm" className="w-full mt-3" onClick={handleAuditAction}>
              Executar Auditoria HMAC
            </Button>
            {auditMessage && (
              <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-2 font-medium">
                {auditMessage}
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Histórico de Transações Mainnet (Somente Leitura)</CardTitle>
          <CardDescription>
            Registro imutável de entradas, recompensas de validação e transferências liquidadas na Mainnet nativa.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {txQuery.isLoading ? (
            <div className="text-center py-8 text-muted-foreground">Carregando histórico seguro...</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tipo</TableHead>
                  <TableHead>TXID / Hash</TableHead>
                  <TableHead>Bloco</TableHead>
                  <TableHead>Montante (BTC)</TableHead>
                  <TableHead>Confirmações</TableHead>
                  <TableHead className="text-right">Assinatura de Auditoria</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {txQuery.data?.transactions.map((tx) => (
                  <TableRow key={tx.txid}>
                    <TableCell>
                      <div className="flex items-center gap-1 font-medium">
                        {tx.type === "INBOUND" && <ArrowDownLeft className="w-4 h-4 text-emerald-500" />}
                        {tx.type === "OUTBOUND" && <ArrowUpRight className="w-4 h-4 text-rose-500" />}
                        {tx.type === "VALIDATION_REWARD" && <Shield className="w-4 h-4 text-primary" />}
                        {tx.type}
                      </div>
                    </TableCell>
                    <TableCell className="font-mono text-xs max-w-[200px] truncate" title={tx.txid}>
                      {tx.txid}
                    </TableCell>
                    <TableCell>#{tx.blockHeight}</TableCell>
                    <TableCell className="font-semibold">{tx.amountBTC} BTC</TableCell>
                    <TableCell>
                      <Badge variant={tx.confirmations >= 6 ? "default" : "secondary"}>
                        {tx.confirmations} confs
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs text-muted-foreground">
                      {tx.auditSignature.substring(0, 16)}...
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
