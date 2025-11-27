import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { Settings, Mic, Sparkles } from "lucide-react";

interface SettingsViewProps {
  micSensitivity: number;
  setMicSensitivity: (value: number) => void;
  proactivityLevel: number;
  setProactivityLevel: (value: number) => void;
}

export function SettingsView({ micSensitivity, setMicSensitivity, proactivityLevel, setProactivityLevel }: SettingsViewProps) {
  return (
    <div className="space-y-6">
      <Card className="bg-gradient-to-br from-gray-50/50 to-gray-100/50 dark:from-gray-900/50 dark:to-gray-800/50 border-primary/10">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Configuration
          </CardTitle>
          <CardDescription>
            Manage your agent's behavior and setups
          </CardDescription>
        </CardHeader>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-blue-500/10 text-blue-500">
                  <Mic className="h-4 w-4" />
                </div>
                <CardTitle className="text-base">Audio Setup</CardTitle>
              </div>
              <span className="text-xs font-mono bg-muted px-2 py-1 rounded">Default</span>
            </div>
            <CardDescription className="text-xs mt-1">
              Microphone sensitivity and detection
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">Silence Threshold</label>
                  <span className="text-xs text-muted-foreground font-mono">
                    {micSensitivity.toFixed(1)}s
                  </span>
                </div>
                <Slider
                  value={[micSensitivity]}
                  onValueChange={(values) => setMicSensitivity(values[0])}
                  min={0.5}
                  max={3.0}
                  step={0.1}
                  className="w-full"
                />
                <div className="flex justify-between text-[10px] text-muted-foreground uppercase tracking-wider font-medium">
                  <span>Fast</span>
                  <span>Patient</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-purple-500/10 text-purple-500">
                  <Sparkles className="h-4 w-4" />
                </div>
                <CardTitle className="text-base">Agent Behavior</CardTitle>
              </div>
              <span className="text-xs font-mono bg-muted px-2 py-1 rounded">Experimental</span>
            </div>
            <CardDescription className="text-xs mt-1">
              How proactive the agent should be
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">Proactivity Level</label>
                  <span className="text-xs text-muted-foreground font-mono">
                    {(proactivityLevel * 100).toFixed(0)}%
                  </span>
                </div>
                <Slider
                  value={[proactivityLevel]}
                  onValueChange={(values) => setProactivityLevel(values[0])}
                  min={0}
                  max={1.0}
                  step={0.1}
                  className="w-full"
                />
                <div className="flex justify-between text-[10px] text-muted-foreground uppercase tracking-wider font-medium">
                  <span>Reactive</span>
                  <span>Proactive</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
        
        {/* Placeholder for future setups */}
        <Card className="border-dashed opacity-50">
          <CardContent className="flex flex-col items-center justify-center h-full min-h-[140px] gap-2">
            <div className="p-3 rounded-full bg-muted">
              <Settings className="h-4 w-4 text-muted-foreground" />
            </div>
            <p className="text-sm text-muted-foreground">Add New Setup</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
