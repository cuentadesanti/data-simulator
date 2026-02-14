import { useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { TOUR_Z, type TooltipPosition, type TourMode } from './types';

interface TourTooltipProps {
  title: string;
  content: string;
  position: TooltipPosition;
  targetRect: DOMRect | null;
  floating: boolean;
  stepIndex: number;
  totalSteps: number;
  mode: TourMode;
  tourLabel?: string;
  onNext: () => void;
  onPrev: () => void;
  onSkip: () => void;
  onClose: () => void;
}

const TOOLTIP_GAP = 12;

function computeTooltipStyle(
  position: TooltipPosition,
  targetRect: DOMRect | null,
  floating: boolean,
  tooltipRect: DOMRect | null,
): React.CSSProperties {
  if (floating || !targetRect) {
    return {
      position: 'fixed',
      top: '50%',
      left: '50%',
      transform: 'translate(-50%, -50%)',
    };
  }

  const tw = tooltipRect?.width ?? 320;
  const th = tooltipRect?.height ?? 200;

  let top = 0;
  let left = 0;

  switch (position) {
    case 'bottom':
      top = targetRect.bottom + TOOLTIP_GAP;
      left = targetRect.left + targetRect.width / 2 - tw / 2;
      break;
    case 'top':
      top = targetRect.top - th - TOOLTIP_GAP;
      left = targetRect.left + targetRect.width / 2 - tw / 2;
      break;
    case 'right':
      top = targetRect.top + targetRect.height / 2 - th / 2;
      left = targetRect.right + TOOLTIP_GAP;
      break;
    case 'left':
      top = targetRect.top + targetRect.height / 2 - th / 2;
      left = targetRect.left - tw - TOOLTIP_GAP;
      break;
  }

  // Clamp within viewport
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  if (left < 8) left = 8;
  if (left + tw > vw - 8) left = vw - tw - 8;
  if (top < 8) top = 8;
  if (top + th > vh - 8) top = vh - th - 8;

  return { position: 'fixed', top, left };
}

export const TourTooltip = ({
  title,
  content,
  position,
  targetRect,
  floating,
  stepIndex,
  totalSteps,
  mode,
  tourLabel,
  onNext,
  onPrev,
  onSkip,
  onClose,
}: TourTooltipProps) => {
  const tooltipRef = useRef<HTMLDivElement>(null);
  const tooltipRect = tooltipRef.current?.getBoundingClientRect() ?? null;

  const style = computeTooltipStyle(position, targetRect, floating, tooltipRect);

  const isLastStep = stepIndex >= totalSteps - 1;
  const isFirstStep = stepIndex === 0;
  const isReference = mode === 'reference';

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      switch (e.key) {
        case 'Escape':
          e.preventDefault();
          onClose();
          break;
        case 'ArrowRight':
        case 'Enter':
          e.preventDefault();
          onNext();
          break;
        case 'ArrowLeft':
          e.preventDefault();
          if (!isFirstStep) onPrev();
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose, onNext, onPrev, isFirstStep]);

  const displayTitle = isReference && tourLabel ? `Guide: ${tourLabel}` : title;

  return (
    <div
      ref={tooltipRef}
      className="w-80 rounded-lg border border-gray-200 bg-white shadow-xl"
      style={{ ...style, zIndex: TOUR_Z.TOOLTIP }}
      role="dialog"
      aria-label={displayTitle}
    >
      {/* Header */}
      <div className="flex items-start justify-between px-4 pt-3">
        <h3 className="text-sm font-semibold text-gray-900">{displayTitle}</h3>
        <button
          type="button"
          onClick={onClose}
          className="ml-2 rounded p-0.5 text-gray-400 hover:text-gray-600"
          aria-label="Close tour"
        >
          <X size={14} />
        </button>
      </div>

      {/* Body */}
      <div className="px-4 py-2">
        <p className="text-sm text-gray-600">{content}</p>
      </div>

      {/* Progress dots */}
      <div className="flex items-center justify-center gap-1.5 px-4 py-1">
        {Array.from({ length: totalSteps }, (_, i) => (
          <span
            key={i}
            className={`inline-block h-1.5 w-1.5 rounded-full ${
              i === stepIndex
                ? 'bg-blue-600'
                : i < stepIndex
                  ? 'bg-blue-300'
                  : 'border border-gray-300 bg-white'
            }`}
          />
        ))}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between border-t border-gray-100 px-4 py-2.5">
        <div>
          {!isReference && (
            <button
              type="button"
              onClick={onSkip}
              className="text-xs text-gray-400 hover:text-gray-600"
            >
              Skip
            </button>
          )}
        </div>
        <div className="flex items-center gap-2">
          {!isFirstStep && (
            <button
              type="button"
              onClick={onPrev}
              className="rounded-md border border-gray-200 px-3 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50"
            >
              Back
            </button>
          )}
          <button
            type="button"
            onClick={onNext}
            className="rounded-md bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700"
          >
            {isLastStep ? (isReference ? 'Done' : 'Finish') : 'Next'}
          </button>
        </div>
      </div>

    </div>
  );
};
