import { useState, useRef, useEffect } from 'react';
import { HelpCircle } from 'lucide-react';
import { useOnboardingStore } from '../../stores/onboardingStore';
import { tourDefinitions } from './tourDefinitions';
import { TOUR_Z, type TourId } from './types';
import { dispatchTelemetryEvent } from '../../services/telemetry';

const TOURS: { id: TourId; label: string }[] = [
  { id: 'main', label: 'Workspace Tour' },
  { id: 'source', label: 'Source Guide' },
  { id: 'transform', label: 'Transform Guide' },
  { id: 'model', label: 'Model Guide' },
  { id: 'publish', label: 'Publish Guide' },
];

export const HelpButton = () => {
  const [open, setOpen] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);
  const startTour = useOnboardingStore((s) => s.startTour);
  const activeTourId = useOnboardingStore((s) => s.activeTourId);
  const resetAll = useOnboardingStore((s) => s.resetAll);

  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  const handleLaunchTour = (tourId: TourId) => {
    if (activeTourId) return; // Don't interrupt active tour
    dispatchTelemetryEvent({
      event_type: 'tour_relaunch',
      action: tourId,
      metadata: { tour_id: tourId },
    });
    startTour(tourId, 'reference');
    setOpen(false);
  };

  const handleToggle = () => {
    if (!open) {
      dispatchTelemetryEvent({
        event_type: 'tour_help_open',
        metadata: {},
      });
    }
    setOpen(!open);
  };

  const handleResetAll = () => {
    resetAll();
    setOpen(false);
  };

  return (
    <div className="fixed bottom-16 right-4" style={{ zIndex: TOUR_Z.HELP_BUTTON }} ref={popoverRef}>
      {open && (
        <div className="absolute bottom-full right-0 mb-2 w-52 rounded-lg border border-gray-200 bg-white py-1 shadow-xl">
          {TOURS.map((tour) => (
            <button
              key={tour.id}
              type="button"
              onClick={() => handleLaunchTour(tour.id)}
              disabled={!!activeTourId}
              className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 disabled:text-gray-300"
            >
              {tour.label}
              <span className="ml-1 text-xs text-gray-400">
                ({tourDefinitions[tour.id].steps.length} steps)
              </span>
            </button>
          ))}
          <div className="my-1 border-t border-gray-100" />
          <button
            type="button"
            onClick={handleResetAll}
            className="w-full px-4 py-2 text-left text-xs text-gray-400 hover:text-gray-600"
          >
            Reset All Tours
          </button>
        </div>
      )}
      <button
        type="button"
        onClick={handleToggle}
        className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-600 text-white shadow-lg hover:bg-blue-700"
        aria-label="Help tours"
      >
        <HelpCircle size={20} />
      </button>
    </div>
  );
};
