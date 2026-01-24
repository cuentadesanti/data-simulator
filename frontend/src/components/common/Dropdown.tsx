/**
 * Custom Dropdown component - a web-native replacement for native select elements.
 * Provides consistent styling and behavior across all browsers.
 */

import { useState, useRef, useEffect, ReactNode } from 'react';
import { ChevronDown, Check } from 'lucide-react';

export interface DropdownOption<T = string> {
    value: T;
    label: string;
    icon?: ReactNode;
    disabled?: boolean;
    description?: string;
}

interface DropdownProps<T = string> {
    options: DropdownOption<T>[];
    value: T;
    onChange: (value: T) => void;
    placeholder?: string;
    disabled?: boolean;
    error?: boolean;
    size?: 'sm' | 'md';
    className?: string;
    icon?: ReactNode;
    renderOption?: (option: DropdownOption<T>, isSelected: boolean) => ReactNode;
    renderValue?: (option: DropdownOption<T> | undefined) => ReactNode;
}

export function Dropdown<T = string>({
    options,
    value,
    onChange,
    placeholder = 'Select...',
    disabled = false,
    error = false,
    size = 'md',
    className = '',
    icon,
    renderOption,
    renderValue,
}: DropdownProps<T>) {
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);
    const listRef = useRef<HTMLDivElement>(null);

    const selectedOption = options.find((opt) => opt.value === value);

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };

        if (isOpen) {
            document.addEventListener('mousedown', handleClickOutside);
        }

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [isOpen]);

    // Scroll selected option into view when opening
    useEffect(() => {
        if (isOpen && listRef.current && selectedOption) {
            const selectedEl = listRef.current.querySelector('[data-selected="true"]');
            if (selectedEl) {
                selectedEl.scrollIntoView({ block: 'nearest' });
            }
        }
    }, [isOpen, selectedOption]);

    // Handle keyboard navigation
    useEffect(() => {
        if (!isOpen) return;

        const handleKeyDown = (event: KeyboardEvent) => {
            switch (event.key) {
                case 'Escape':
                    setIsOpen(false);
                    break;
                case 'ArrowDown': {
                    event.preventDefault();
                    const currentIndex = options.findIndex((opt) => opt.value === value);
                    const nextIndex = Math.min(currentIndex + 1, options.length - 1);
                    const nextOption = options[nextIndex];
                    if (nextOption && !nextOption.disabled) {
                        onChange(nextOption.value);
                    }
                    break;
                }
                case 'ArrowUp': {
                    event.preventDefault();
                    const currentIndex = options.findIndex((opt) => opt.value === value);
                    const prevIndex = Math.max(currentIndex - 1, 0);
                    const prevOption = options[prevIndex];
                    if (prevOption && !prevOption.disabled) {
                        onChange(prevOption.value);
                    }
                    break;
                }
                case 'Enter':
                    setIsOpen(false);
                    break;
            }
        };

        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [isOpen, options, value, onChange]);

    const handleSelect = (option: DropdownOption<T>) => {
        if (option.disabled) return;
        onChange(option.value);
        setIsOpen(false);
    };

    const sizeClasses = {
        sm: 'py-1.5 text-xs',
        md: 'py-2 text-sm',
    };

    const borderClasses = error
        ? 'border-red-300 focus:ring-red-500'
        : 'border-gray-300 focus:ring-purple-500';

    return (
        <div className={`relative ${className}`} ref={dropdownRef}>
            {/* Trigger button */}
            <button
                type="button"
                onClick={() => !disabled && setIsOpen(!isOpen)}
                disabled={disabled}
                className={`
                    w-full appearance-none bg-gray-50 border rounded-md
                    ${icon ? 'pl-9' : 'pl-3'} pr-8
                    ${sizeClasses[size]}
                    focus:outline-none focus:ring-2
                    ${borderClasses}
                    ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:bg-gray-100'}
                    text-left transition-colors
                `}
            >
                {renderValue ? (
                    renderValue(selectedOption)
                ) : selectedOption ? (
                    <span className="block truncate">{selectedOption.label}</span>
                ) : (
                    <span className="block truncate text-gray-400">{placeholder}</span>
                )}
            </button>

            {/* Left icon */}
            {icon && (
                <div className="absolute left-3 top-1/2 -translate-y-1/2 text-purple-600 pointer-events-none">
                    {icon}
                </div>
            )}

            {/* Chevron */}
            <ChevronDown
                size={size === 'sm' ? 12 : 14}
                className={`absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none transition-transform ${isOpen ? 'rotate-180' : ''}`}
            />

            {/* Dropdown menu */}
            {isOpen && (
                <div
                    ref={listRef}
                    className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-auto"
                >
                    {options.map((option, index) => {
                        const isSelected = option.value === value;

                        if (renderOption) {
                            return (
                                <div
                                    key={index}
                                    data-selected={isSelected}
                                    onClick={() => handleSelect(option)}
                                    className={`cursor-pointer ${option.disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                                >
                                    {renderOption(option, isSelected)}
                                </div>
                            );
                        }

                        return (
                            <div
                                key={index}
                                data-selected={isSelected}
                                onClick={() => handleSelect(option)}
                                className={`
                                    flex items-center gap-2 px-3 ${sizeClasses[size]}
                                    ${isSelected ? 'bg-purple-50 text-purple-700' : 'text-gray-700'}
                                    ${option.disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:bg-gray-50'}
                                    transition-colors
                                `}
                            >
                                {option.icon && (
                                    <span className="flex-shrink-0">{option.icon}</span>
                                )}
                                <span className="flex-1 truncate">{option.label}</span>
                                {isSelected && (
                                    <Check size={14} className="flex-shrink-0 text-purple-600" />
                                )}
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
