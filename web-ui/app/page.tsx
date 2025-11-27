"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Mic, Database, Brain, Wifi, WifiOff, HelpCircle, Settings, Power } from "lucide-react";
import { WaveAnimation } from "@/components/wave-animation";
import { MCPManager } from "@/components/mcp-manager";
import { KnowledgeGraph } from "@/components/knowledge-graph";
import { SettingsView } from "@/components/settings-view";
import { useVoiceAgent } from "@/hooks/use-voice-agent";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";

export default function Home() {
  const { status, transcript, lastResponse, isConnected, agentRunning, userProfile, updateKnowledge, audioLevel, micSensitivity, setMicSensitivity, proactivityLevel, setProactivityLevel, triggerAgent, startAgent, stopAgent } = useVoiceAgent();

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4 sm:p-8">
      <div className="w-full max-w-4xl space-y-8">
        <div className="text-center space-y-2 relative">
          <div className="absolute right-0 top-0 flex items-center gap-2">
            {isConnected && agentRunning && (
              <Button 
                variant="ghost" 
                size="sm"
                onClick={stopAgent}
                className="text-red-500 hover:text-red-600 hover:bg-red-500/10 h-7 px-2 text-xs"
              >
                <Power className="h-3 w-3 mr-1" />
                Shutdown
              </Button>
            )}
            {isConnected ? (
              <div className="flex items-center gap-1 text-green-500 text-xs font-medium bg-green-500/10 px-2 py-1 rounded-full">
                <Wifi className="h-3 w-3" />
                <span>Connected</span>
              </div>
            ) : (
              <div className="flex items-center gap-1 text-red-500 text-xs font-medium bg-red-500/10 px-2 py-1 rounded-full">
                <WifiOff className="h-3 w-3" />
                <span>Disconnected</span>
              </div>
            )}
          </div>
          <div className="absolute left-0 top-0">
            <Dialog>
              <DialogTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <HelpCircle className="h-4 w-4" />
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-md">
                <DialogHeader>
                  <DialogTitle>Voice Commands</DialogTitle>
                  <DialogDescription>
                    Control Levial using these voice commands
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <div className="flex items-start gap-3 p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
                      <Mic className="h-5 w-5 text-blue-500 mt-0.5" />
                      <div>
                        <p className="font-semibold text-sm">"Hey Jarvis"</p>
                        <p className="text-xs text-muted-foreground">Wake the agent to start listening</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3 p-3 rounded-lg bg-purple-500/10 border border-purple-500/20">
                      <Mic className="h-5 w-5 text-purple-500 mt-0.5" />
                      <div>
                        <p className="font-semibold text-sm">"Thank you"</p>
                        <p className="text-xs text-muted-foreground">Stop the agent from speaking</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3 p-3 rounded-lg bg-pink-500/10 border border-pink-500/20">
                      <Mic className="h-5 w-5 text-pink-500 mt-0.5" />
                      <div>
                        <p className="font-semibold text-sm">"Alexa"</p>
                        <p className="text-xs text-muted-foreground">Pause listening (say "Hey Jarvis" to resume)</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                      <Mic className="h-5 w-5 text-red-500 mt-0.5" />
                      <div>
                        <p className="font-semibold text-sm">"Goodbye"</p>
                        <p className="text-xs text-muted-foreground">End the conversation session</p>
                      </div>
                    </div>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
          </div>
          <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-6xl bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
            Levial
          </h1>
          <p className="text-lg text-muted-foreground">
            Always-on voice assistant • Say "Hey Jarvis" to wake me
          </p>
        </div>

        <Tabs defaultValue="talk" className="w-full">
          <div className="flex justify-center mb-8">
            <TabsList className="grid w-full max-w-md grid-cols-4 h-12">
              <TabsTrigger value="talk" className="text-base">
                <Mic className="mr-2 h-4 w-4" />
                Talk
              </TabsTrigger>
              <TabsTrigger value="mcp" className="text-base">
                <Database className="mr-2 h-4 w-4" />
                MCP
              </TabsTrigger>
              <TabsTrigger value="knowledge" className="text-base">
                <Brain className="mr-2 h-4 w-4" />
                Know
              </TabsTrigger>
              <TabsTrigger value="settings" className="text-base">
                <Settings className="mr-2 h-4 w-4" />
                Set
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="talk" className="space-y-4">
            <div className="flex flex-col items-center justify-center py-8 gap-8">
              <WaveAnimation 
                status={status} 
                audioLevel={audioLevel} 
                agentRunning={agentRunning}
                onTrigger={triggerAgent}
                onStartAgent={startAgent}
              />
              
              {(transcript || lastResponse) && (
                <div className="w-full max-w-2xl space-y-4">
                  {transcript && (
                    <Card className="bg-muted/50 border-none">
                      <CardContent className="p-4">
                        <p className="text-sm font-medium text-muted-foreground mb-1">You said:</p>
                        <p className="text-lg">{transcript}</p>
                      </CardContent>
                    </Card>
                  )}
                  {lastResponse && (
                    <Card className="bg-primary/5 border-primary/20">
                      <CardContent className="p-4">
                        <p className="text-sm font-medium text-primary mb-1">Levial said:</p>
                        <p className="text-lg">{lastResponse}</p>
                      </CardContent>
                    </Card>
                  )}
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="mcp" className="space-y-4">
            <MCPManager />
          </TabsContent>

          <TabsContent value="knowledge" className="space-y-4">
            <KnowledgeGraph userProfile={userProfile} onUpdate={updateKnowledge} />
          </TabsContent>

          <TabsContent value="settings" className="space-y-4">
            <SettingsView 
              micSensitivity={micSensitivity} 
              setMicSensitivity={setMicSensitivity}
              proactivityLevel={proactivityLevel}
              setProactivityLevel={setProactivityLevel}
            />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
