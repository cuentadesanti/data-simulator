export type TourId = 'main' | 'source' | 'transform' | 'model' | 'publish';
export type TooltipPosition = 'top' | 'bottom' | 'left' | 'right';
export type TourMode = 'guided' | 'reference';

export interface TourStep {
  id: string;
  target: string | null;
  title: string;
  content: string;
  position: TooltipPosition;
  action?: { label: string; onClick: () => void };
  advanceOnAction?: boolean;
  spotlightPadding?: number;
  floating?: boolean;
  waitForTarget?: boolean;
}

export interface TourDefinition {
  id: TourId;
  version: number;
  steps: TourStep[];
  completionAction?: string;
}

export const TOUR_Z = {
  HELP_BUTTON: 50,
  OVERLAY: 60,
  TOOLTIP: 70,
} as const;
