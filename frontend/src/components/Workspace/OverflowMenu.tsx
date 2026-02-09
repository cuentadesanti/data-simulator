import { useEffect, useRef, useState } from 'react';
import { MoreVertical } from 'lucide-react';

interface OverflowMenuProps {
  items: Array<{
    label: string;
    onClick: () => void;
  }>;
}

export const OverflowMenu = ({ items }: OverflowMenuProps) => {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleOutside = (event: MouseEvent) => {
      const target = event.target as Node | null;
      if (menuRef.current && target && !menuRef.current.contains(target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutside);
    return () => document.removeEventListener('mousedown', handleOutside);
  }, [open]);

  return (
    <div className="relative" ref={menuRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="rounded-md border border-gray-200 bg-white p-2 text-gray-600 hover:bg-gray-50"
      >
        <MoreVertical size={14} />
      </button>
      {open && (
        <div className="absolute right-0 z-20 mt-2 min-w-44 rounded-md border border-gray-200 bg-white p-1 shadow-lg">
          {items.map((item) => (
            <button
              key={item.label}
              type="button"
              onClick={() => {
                item.onClick();
                setOpen(false);
              }}
              className="block w-full rounded px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-100"
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
