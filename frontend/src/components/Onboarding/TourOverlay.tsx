import { TOUR_Z } from './types';

interface TourOverlayProps {
  targetRect: DOMRect | null;
  padding: number;
  visible: boolean;
  onBackdropClick: () => void;
}

export const TourOverlay = ({ targetRect, padding, visible, onBackdropClick }: TourOverlayProps) => {
  if (!visible) return null;

  const handleClick = (e: React.MouseEvent) => {
    // Only dismiss if clicking on the backdrop itself, not the cutout
    if (e.target === e.currentTarget) {
      onBackdropClick();
    }
  };

  return (
    <div
      className="fixed inset-0"
      style={{ zIndex: TOUR_Z.OVERLAY }}
      onClick={handleClick}
    >
      <svg className="absolute inset-0 h-full w-full">
        <defs>
          <mask id="tour-spotlight-mask">
            <rect x="0" y="0" width="100%" height="100%" fill="white" />
            {targetRect && (
              <rect
                x={targetRect.left - padding}
                y={targetRect.top - padding}
                width={targetRect.width + padding * 2}
                height={targetRect.height + padding * 2}
                rx="8"
                ry="8"
                fill="black"
              />
            )}
          </mask>
        </defs>
        <rect
          x="0"
          y="0"
          width="100%"
          height="100%"
          fill="rgba(0,0,0,0.5)"
          mask="url(#tour-spotlight-mask)"
        />
      </svg>
      {/* Transparent clickable cutout area so users can interact with target */}
      {targetRect && (
        <div
          className="absolute"
          style={{
            left: targetRect.left - padding,
            top: targetRect.top - padding,
            width: targetRect.width + padding * 2,
            height: targetRect.height + padding * 2,
            pointerEvents: 'none',
          }}
        />
      )}
    </div>
  );
};
