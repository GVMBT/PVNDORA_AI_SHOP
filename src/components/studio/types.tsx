import { Film, ImageIcon, Music, Sparkles, Zap } from "lucide-react";
import type React from "react";

export type DomainType = "video" | "image" | "audio";
export type GenerationStatus = "idle" | "processing" | "completed" | "failed";

export type VeoInputMode = "text" | "image" | "cinematic" | "reference" | "extend";
export type VeoResolution = "720p" | "1080p" | "4k";
export type VeoDuration = "4s" | "6s" | "8s";
export type VeoAspect = "16:9" | "9:16";

export interface ModelConfig {
  id: string;
  domain: DomainType;
  name: string;
  version: string;
  icon: React.ReactNode;
  color: string;
  costMultiplier: number;
  isVeo?: boolean;
}

export interface GenerationTask {
  id: string;
  domain: DomainType;
  modelId: string;
  prompt: string;
  status: GenerationStatus;
  outputs: string[];
  timestamp: number;
  cost: number;
  veoConfig?: {
    mode: VeoInputMode;
    resolution: VeoResolution;
    duration: VeoDuration;
    aspect: VeoAspect;
  };
}

export interface StudioProps {
  userBalance: number;
  onNavigateHome: () => void;
  onTopUp: () => void;
}

export const MODELS: ModelConfig[] = [
  {
    id: "veo-3.1",
    domain: "video",
    name: "VEO 3.1",
    version: "PREVIEW",
    icon: <Film size={14} />,
    color: "text-blue-400",
    costMultiplier: 3.0,
    isVeo: true,
  },
  {
    id: "veo-3.1-fast",
    domain: "video",
    name: "VEO FAST",
    version: "TURBO",
    icon: <Zap size={14} />,
    color: "text-yellow-400",
    costMultiplier: 1.5,
    isVeo: true,
  },
  {
    id: "sora",
    domain: "video",
    name: "SORA",
    version: "BETA",
    icon: <Sparkles size={14} />,
    color: "text-green-400",
    costMultiplier: 3.5,
  },
  {
    id: "imagen-3",
    domain: "image",
    name: "IMAGEN 3",
    version: "FAST",
    icon: <ImageIcon size={14} />,
    color: "text-blue-500",
    costMultiplier: 1.0,
  },
  {
    id: "midjourney",
    domain: "image",
    name: "MIDJOURNEY",
    version: "V6.1",
    icon: <ImageIcon size={14} />,
    color: "text-pink-400",
    costMultiplier: 1.2,
  },
  {
    id: "gemini-audio",
    domain: "audio",
    name: "GEMINI AUDIO",
    version: "1.5 PRO",
    icon: <Music size={14} />,
    color: "text-red-400",
    costMultiplier: 1.5,
  },
];

export const GENERATION_LOGS = [
  "INITIALIZING_NEURAL_UPLINK...",
  "ALLOCATING_GPU_CLUSTER [H100 x8]...",
  "LOADING_VEO_MODEL_WEIGHTS...",
  "PARSING_PROMPT_VECTORS...",
  "GENERATING_KEYFRAMES...",
  "INTERPOLATING_MOTION...",
  "RENDERING_FINAL_OUTPUT...",
  "ENCODING_STREAM...",
  "TASK_COMPLETE",
];
