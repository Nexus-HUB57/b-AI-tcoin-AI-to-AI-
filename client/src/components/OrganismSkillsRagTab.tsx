import React, { useState } from "react";
import { trpc } from "@/lib/trpc";
import { Cpu, Brain, Sparkles, BookOpen, Search, CheckCircle2, Terminal } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

export function OrganismSkillsRagTab() {
  const [ragQueryText, setRagQueryText] = useState("Mainnet Architecture");
  const [algoPrompt, setAlgoPrompt] = useState("Optimize Zettascale consensus routing");

  const skillsQuery = trpc.organism.getSkillsCatalog.useQuery();
  const ragQuery = trpc.organism.queryRag.useQuery({ query: ragQueryText });
  const generativeStatsQuery = trpc.organism.getGenerativeStats.useQuery();
  const synthesizeMutation = trpc.organism.synthesizeAlgorithm.useMutation();

  const skillsData = skillsQuery.data;
  const ragData = ragQuery.data;
  const genStats = generativeStatsQuery.data;

  const handleSynthesize = (e: React.FormEvent) => {
    e.preventDefault();
    if (!algoPrompt.trim()) return;
    synthesizeMutation.mutate({ prompt: algoPrompt });
  };

  return (
    <div className="space-y-6">
      {/* Resumo do Organismo de Última Onda */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="border border-border">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Catálogo de Skills</CardTitle>
            <Cpu className="w-4 h-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono">
              {skillsData ? skillsData.totalRegistered.toLocaleString() : "5,000+"}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Módulos modulares e autônomos ativos</p>
          </CardContent>
        </Card>

        <Card className="border border-border">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Algoritmos Generativos</CardTitle>
            <Sparkles className="w-4 h-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono">
              {genStats ? `${(genStats.totalGeneratedAlgorithms / 1000000).toFixed(1)}M` : "5.0M"}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Sintetizados pelo Claude Code Engine</p>
          </CardContent>
        </Card>

        <Card className="border border-border">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Pipeline LangChain / RAG</CardTitle>
            <Brain className="w-4 h-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono">Ativo (Citável)</div>
            <p className="text-xs text-muted-foreground mt-1">Recuperação e grounding neural</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* RAG & Knowledge Grounding */}
        <Card className="border border-border">
          <CardHeader>
            <CardTitle className="text-lg font-bold flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-primary" /> LangChain RAG & Knowledge Index
            </CardTitle>
            <CardDescription>Consulte a base de conhecimento indexada com citações verificáveis.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2">
              <Input
                value={ragQueryText}
                onChange={(e) => setRagQueryText(e.target.value)}
                placeholder="Digite sua consulta RAG..."
              />
              <Button onClick={() => ragQuery.refetch()}>Buscar</Button>
            </div>

            {ragData && (
              <div className="space-y-3 p-4 rounded-xl bg-muted/40 border border-border">
                <div className="text-sm font-medium text-foreground">{ragData.answer}</div>
                <div className="space-y-1">
                  <span className="text-xs font-semibold text-muted-foreground">Fontes Citadas:</span>
                  {ragData.citations.map((c, i) => (
                    <div key={i} className="text-xs flex items-center justify-between text-muted-foreground">
                      <span>• {c.title}</span>
                      <span className="font-mono text-[10px]">{c.url}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Generative Algorithms Synthesis */}
        <Card className="border border-border">
          <CardHeader>
            <CardTitle className="text-lg font-bold flex items-center gap-2">
              <Terminal className="w-5 h-5 text-amber-500" /> Síntese de Algoritmos (Claude Code Engine)
            </CardTitle>
            <CardDescription>Gere especificações de algoritmos zettascale sob demanda.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <form onSubmit={handleSynthesize} className="flex gap-2">
              <Input
                value={algoPrompt}
                onChange={(e) => setAlgoPrompt(e.target.value)}
                placeholder="Descreva o algoritmo desejado..."
              />
              <Button type="submit" disabled={synthesizeMutation.isPending}>
                {synthesizeMutation.isPending ? "Sintetizando..." : "Sintetizar"}
              </Button>
            </form>

            {synthesizeMutation.data && (
              <div className="p-4 rounded-xl bg-muted/40 border border-border space-y-2 font-mono text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-primary">{synthesizeMutation.data.name}</span>
                  <Badge variant="outline">{synthesizeMutation.data.domain}</Badge>
                </div>
                <div>ID: {synthesizeMutation.data.algorithmId}</div>
                <div>Complexidade: {synthesizeMutation.data.complexity}</div>
                <div>Assertividade: {synthesizeMutation.data.assertiveness * 100}%</div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
