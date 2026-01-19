import { useEffect, useMemo, useRef, useState } from "react";
import { useLocale } from "../../hooks/useLocale";
import { useStudioInit } from "../../hooks/useStudioRealtime";
import { AudioEngine } from "../../lib/AudioEngine";
import {
  selectActiveGeneration,
  selectActiveModel,
  useStudioStore,
} from "../../stores/studioStore";
import { CommandDeck } from "./CommandDeck";
import { HistorySidebar } from "./HistorySidebar";
import { TopHUD } from "./TopHUD";
import {
  type DomainType,
  GENERATION_LOGS,
  type GenerationTask,
  MODELS,
  type StudioProps,
  type VeoAspect,
  type VeoDuration,
  type VeoInputMode,
  type VeoResolution,
} from "./types";
import { Viewport } from "./Viewport";
import { DataStream, HexGrid, Scanline } from "./VisualComponents";

const StudioContainer: React.FC<StudioProps> = ({ userBalance, onNavigateHome, onTopUp }) => {
  const { t } = useLocale();

  // Initialize Studio store and realtime
  useStudioInit();

  // Store state
  const {
    generations,
    models,
    activeModelId: storeActiveModelId,
    prompt: storePrompt,
    generationStatus,
    startGeneration,
    setPrompt: setStorePrompt,
    setActiveModel: setStoreActiveModel,
    setConfig,
  } = useStudioStore();

  const storeActiveGeneration = useStudioStore(selectActiveGeneration);
  const storeActiveModel = useStudioStore(selectActiveModel);

  // Local UI State
  const [activeDomain, setActiveDomain] = useState<DomainType>("video");
  const [activeModelId, setActiveModelId] = useState<string>("veo-3.1");
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationLogs, setGenerationLogs] = useState<string[]>([]);

  // Veo Settings
  const [veoMode, setVeoMode] = useState<VeoInputMode>("text");
  const [veoResolution, setVeoResolution] = useState<VeoResolution>("720p");
  const [veoDuration, setVeoDuration] = useState<VeoDuration>("6s");
  const [aspectRatio, setAspectRatio] = useState<VeoAspect>("16:9");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showModelSelector, setShowModelSelector] = useState(false);

  // Uploads
  const [startFrame, setStartFrame] = useState<string | null>(null);
  const [endFrame, setEndFrame] = useState<string | null>(null);
  const [videoInput, setVideoInput] = useState<string | null>(null);
  const [refImages, setRefImages] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadTarget, setUploadTarget] = useState<"start" | "end" | "ref" | "video" | null>(null);

  // History
  const [history, setHistory] = useState<GenerationTask[]>([]);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);

  // Refs for cleanup timers
  const activeTimersRef = useRef<{ interval?: NodeJS.Timeout; timeout?: NodeJS.Timeout }>({});

  const activeModel = MODELS.find((m) => m.id === activeModelId) || MODELS[0];
  const activeTask = history.find((t) => t.id === activeTaskId) || null;

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      if (activeTimersRef.current.interval) {
        clearInterval(activeTimersRef.current.interval);
      }
      if (activeTimersRef.current.timeout) {
        clearTimeout(activeTimersRef.current.timeout);
      }
    };
  }, []);

  // -- VEO 3.1 LOGIC ENFORCER --
  useEffect(() => {
    if (!activeModel.isVeo) return;

    if (veoMode === "reference" && aspectRatio !== "16:9") setAspectRatio("16:9");
    if (
      (veoResolution === "1080p" || veoResolution === "4k" || veoMode === "reference") &&
      veoDuration !== "8s"
    )
      setVeoDuration("8s");
    if (veoMode === "extend" && veoResolution !== "720p") setVeoResolution("720p");
  }, [veoMode, veoResolution, aspectRatio, activeModel, veoDuration]);

  const handleDomainSwitch = (domain: DomainType) => {
    if (domain === activeDomain) return;
    AudioEngine.click();
    setActiveDomain(domain);
    const defaultModel = MODELS.find((m) => m.domain === domain);
    if (defaultModel) setActiveModelId(defaultModel.id);

    setStartFrame(null);
    setEndFrame(null);
    setRefImages([]);
    setVideoInput(null);
    setVeoMode("text");
  };

  const estimatedCost = useMemo(() => {
    let cost = activeModel.costMultiplier * 10;
    if (activeModel.isVeo) {
      if (veoResolution === "4k") cost *= 2.5;
      if (veoResolution === "1080p") cost *= 1.5;
      if (veoDuration === "8s") cost *= 1.2;
      if (veoMode !== "text") cost *= 1.2;
    }
    return Math.round(cost);
  }, [activeModel, veoResolution, veoDuration, veoMode]);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && uploadTarget) {
      if (uploadTarget === "video") {
        if (file.size > 50 * 1024 * 1024) {
          alert("Video too large. Max 50MB for preview.");
          return;
        }
      }

      const reader = new FileReader();
      reader.onload = (e) => {
        const res = e.target?.result as string;
        if (uploadTarget === "start") setStartFrame(res);
        if (uploadTarget === "end") setEndFrame(res);
        if (uploadTarget === "video") setVideoInput(res);
        if (uploadTarget === "ref") {
          if (refImages.length < 3) setRefImages((prev) => [...prev, res]);
          else alert("Maximum 3 reference images allowed");
        }
        AudioEngine.success();
      };
      reader.readAsDataURL(file);
    }
    setUploadTarget(null);
  };

  const triggerUpload = (target: "start" | "end" | "ref" | "video") => {
    setUploadTarget(target);
    if (fileInputRef.current) {
      fileInputRef.current.accept = target === "video" ? "video/*" : "image/*";
      setTimeout(() => fileInputRef.current?.click(), 100);
    }
  };

  const handleGenerate = async () => {
    if (userBalance < estimatedCost) return alert(t("modal.errors.insufficientFunds"));

    if (veoMode === "text" && !prompt.trim()) return alert("Enter a prompt");
    if (veoMode === "image" && !startFrame) return alert("Upload start frame");
    if (veoMode === "cinematic" && (!startFrame || !endFrame))
      return alert("Upload start and end frames");
    if (veoMode === "extend" && !videoInput) return alert("Upload video to extend");

    AudioEngine.boot();
    setIsGenerating(true);
    setGenerationLogs([]);

    // Start log simulation for visual feedback
    let logIndex = 0;
    const logInterval = setInterval(() => {
      if (logIndex < GENERATION_LOGS.length) {
        setGenerationLogs((prev) => [...prev, GENERATION_LOGS[logIndex]]);
        logIndex++;
      } else {
        clearInterval(logInterval);
        activeTimersRef.current.interval = undefined;
      }
    }, 500);
    activeTimersRef.current.interval = logInterval;

    try {
      // Call real API
      const generationId = await startGeneration({
        model_id: activeModelId,
        prompt: prompt,
        config: {
          resolution: veoResolution,
          aspect_ratio: aspectRatio,
          duration_seconds: parseInt(veoDuration.replace("s", ""), 10),
          custom_params: {
            mode: veoMode,
          },
        },
      });

      if (generationId) {
        // Also update local history for immediate UI feedback
        const newTask: GenerationTask = {
          id: generationId,
          domain: activeDomain,
          modelId: activeModelId,
          prompt: prompt,
          status: "processing",
          timestamp: Date.now(),
          cost: estimatedCost,
          outputs: [],
          veoConfig: activeModel.isVeo
            ? { mode: veoMode, resolution: veoResolution, duration: veoDuration, aspect: aspectRatio }
            : undefined,
        };
        setHistory((prev) => [newTask, ...prev]);
        setActiveTaskId(generationId);
        setPrompt(""); // Clear prompt after success
        AudioEngine.success();
      } else {
        AudioEngine.error();
        alert("Ошибка генерации. Попробуйте позже.");
      }
    } catch (error) {
      console.error("Generation error:", error);
      AudioEngine.error();
      alert(error instanceof Error ? error.message : "Неизвестная ошибка");
    } finally {
      // Stop log simulation
      if (activeTimersRef.current.interval) {
        clearInterval(activeTimersRef.current.interval);
        activeTimersRef.current.interval = undefined;
      }
      setIsGenerating(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-[#020202] text-white overflow-hidden font-mono selection:bg-pandora-cyan selection:text-black z-50 flex">
      <input type="file" ref={fileInputRef} className="hidden" onChange={handleFileUpload} />

      {/* --- BACKGROUND LAYERS --- */}
      <Scanline />
      <HexGrid />
      {/* Ambient glow from center */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_50%_40%,_rgba(0,255,255,0.08)_0%,_rgba(0,0,0,0)_50%)] pointer-events-none" />
      {/* Vignette effect */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,_transparent_30%,_rgba(0,0,0,0.9)_100%)] pointer-events-none" />
      {/* Corner data streams */}
      <DataStream position="left" />
      <DataStream position="right" />
      {/* Edge glow lines */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-pandora-cyan/30 to-transparent" />
      <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-pandora-cyan/20 to-transparent" />

      {/* --- HISTORY SIDEBAR --- */}
      <HistorySidebar
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        history={history}
        activeTaskId={activeTaskId}
        onTaskSelect={setActiveTaskId}
      />

      {/* --- MAIN AREA --- */}
      <div className="flex-1 flex flex-col relative h-full">
        {/* TOP HUD */}
        <TopHUD
          activeDomain={activeDomain}
          userBalance={userBalance}
          onNavigateHome={onNavigateHome}
          onTopUp={onTopUp}
          onDomainSwitch={handleDomainSwitch}
          onSidebarToggle={() => setIsHistoryOpen(!isHistoryOpen)}
          isSidebarOpen={isHistoryOpen}
        />

        {/* VIEWPORT */}
        <Viewport
          activeTask={activeTask}
          activeModel={activeModel}
          generationLogs={generationLogs}
          activeDomain={activeDomain}
        />

        {/* --- COMMAND DECK (FOOTER) --- */}
        <CommandDeck
          userBalance={userBalance}
          onTopUp={onTopUp}
          estimatedCost={estimatedCost}
          isGenerating={isGenerating}
          prompt={prompt}
          onPromptChange={setPrompt}
          onGenerate={handleGenerate}
          activeModel={activeModel}
          veoMode={veoMode}
          setVeoMode={setVeoMode}
          showAdvanced={showAdvanced}
          setShowAdvanced={setShowAdvanced}
          veoResolution={veoResolution}
          setVeoResolution={setVeoResolution}
          aspectRatio={aspectRatio}
          setAspectRatio={setAspectRatio}
          veoDuration={veoDuration}
          setVeoDuration={setVeoDuration}
          showModelSelector={showModelSelector}
          setShowModelSelector={setShowModelSelector}
          activeModelId={activeModelId}
          setActiveModelId={setActiveModelId}
          activeDomain={activeDomain}
          startFrame={startFrame}
          endFrame={endFrame}
          videoInput={videoInput}
          refImages={refImages}
          triggerUpload={triggerUpload}
        />
      </div>
    </div>
  );
};

export default StudioContainer;
