import { useEffect, useId, useMemo, useRef, useState } from "react";
import { Check, ChevronDown } from "lucide-react";

export interface SelectFieldOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectFieldGroup {
  label: string;
  options: SelectFieldOption[];
}

interface SelectFieldProps {
  id?: string;
  value: string;
  options?: readonly SelectFieldOption[];
  groups?: readonly SelectFieldGroup[];
  onChange: (value: string) => void;
  ariaLabel?: string;
  className?: string;
  disabled?: boolean;
  radius?: "lg" | "xl";
  visualSize?: "sm" | "md";
}

interface FlatOption extends SelectFieldOption {
  groupLabel?: string;
}

export function SelectField({
  id,
  value,
  options = [],
  groups = [],
  onChange,
  ariaLabel,
  className = "",
  disabled = false,
  visualSize = "md",
}: SelectFieldProps) {
  const generatedId = useId();
  const buttonId = id ?? generatedId;
  const listboxId = `${buttonId}-listbox`;
  const rootRef = useRef<HTMLDivElement | null>(null);
  const optionRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const [open, setOpen] = useState(false);
  const [activeValue, setActiveValue] = useState(value);

  const flatOptions = useMemo<FlatOption[]>(() => {
    const groupedOptions = groups.flatMap((group) =>
      group.options.map((option) => ({
        ...option,
        groupLabel: group.label,
      })),
    );
    return [...options, ...groupedOptions];
  }, [groups, options]);
  const enabledOptions = flatOptions.filter((option) => !option.disabled);
  const selectedOption = flatOptions.find((option) => option.value === value) ?? flatOptions[0] ?? null;
  const activeOption = flatOptions.find((option) => option.value === activeValue && !option.disabled) ?? selectedOption;

  useEffect(() => {
    if (!open) {
      setActiveValue(value);
      return undefined;
    }

    function handlePointerDown(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    window.addEventListener("pointerdown", handlePointerDown);
    return () => window.removeEventListener("pointerdown", handlePointerDown);
  }, [open, value]);

  useEffect(() => {
    if (open && activeOption) {
      optionRefs.current[activeOption.value]?.scrollIntoView({ block: "nearest" });
    }
  }, [activeOption, open]);

  // D 风默认直角；radius prop 保留为 API 兼容（不再生效）
  const sizeClassName = visualSize === "sm" ? "h-9 pl-2.5 pr-9 text-xs" : "h-10 pl-3 pr-10 text-sm";
  const menuClassName = visualSize === "sm" ? "max-h-56 text-xs" : "max-h-64 text-sm";
  const iconSize = visualSize === "sm" ? 14 : 16;
  const iconRightClassName = visualSize === "sm" ? "right-2.5" : "right-3";
  const dividerRightClassName = visualSize === "sm" ? "right-7" : "right-8";

  function moveActive(delta: number) {
    if (!enabledOptions.length) {
      return;
    }
    const currentIndex = Math.max(0, enabledOptions.findIndex((option) => option.value === activeValue));
    const nextIndex = (currentIndex + delta + enabledOptions.length) % enabledOptions.length;
    setActiveValue(enabledOptions[nextIndex].value);
  }

  function selectOption(option: SelectFieldOption) {
    if (option.disabled) {
      return;
    }
    onChange(option.value);
    setActiveValue(option.value);
    setOpen(false);
  }

  return (
    <div ref={rootRef} className={`relative w-full ${className}`}>
      <button
        id={buttonId}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listboxId}
        aria-label={ariaLabel}
        disabled={disabled}
        onClick={() => {
          if (!disabled) {
            setOpen((current) => !current);
          }
        }}
        onKeyDown={(event) => {
          if (disabled) {
            return;
          }
          if (event.key === "ArrowDown") {
            event.preventDefault();
            setOpen(true);
            moveActive(1);
            return;
          }
          if (event.key === "ArrowUp") {
            event.preventDefault();
            setOpen(true);
            moveActive(-1);
            return;
          }
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            if (open && activeOption) {
              selectOption(activeOption);
              return;
            }
            setOpen(true);
            return;
          }
          if (event.key === "Escape") {
            setOpen(false);
          }
        }}
        className={`relative w-full border border-atelier-smoke/50 bg-atelier-paper/90 text-left font-medium text-atelier-ink shadow-paper-sm outline-none transition-colors hover:border-atelier-smoke hover:bg-atelier-paper focus:border-atelier-vermilion focus:bg-atelier-paper focus:ring-2 focus:ring-atelier-vermilion/30 disabled:cursor-not-allowed disabled:border-atelier-smoke/30 disabled:bg-atelier-cream disabled:text-atelier-smoke disabled:shadow-none dark:border-atelier-cream/30 dark:bg-[#1F1812] dark:text-atelier-cream dark:shadow-black/25 dark:hover:border-atelier-cream/40 dark:hover:bg-atelier-cream/10 dark:focus:border-atelier-vermilion dark:focus:bg-[#1F1812] dark:focus:ring-atelier-vermilion/30 dark:disabled:border-atelier-cream/15 dark:disabled:bg-atelier-cream/5 dark:disabled:text-atelier-cream/40 ${sizeClassName}`}
      >
        <span className="block truncate">{selectedOption?.label ?? ""}</span>
        <span
          className={`pointer-events-none absolute top-1/2 h-5 -translate-y-1/2 border-l border-atelier-smoke/30 dark:border-atelier-cream/15 ${dividerRightClassName}`}
        />
        <ChevronDown
          size={iconSize}
          className={`pointer-events-none absolute top-1/2 -translate-y-1/2 text-atelier-smoke transition-transform dark:text-atelier-cream/60 ${open ? "rotate-180" : ""} ${iconRightClassName}`}
        />
      </button>

      {open && !disabled ? (
        <div
          id={listboxId}
          role="listbox"
          aria-labelledby={buttonId}
          className={`absolute z-[95] mt-1 w-full overflow-y-auto rounded-paper-lg border border-atelier-smoke/30 bg-atelier-paper p-1 shadow-paper-lg ring-1 ring-atelier-ink/5 dark:border-atelier-cream/15 dark:bg-[#1F1812] dark:shadow-black/45 dark:ring-atelier-cream/10 ${menuClassName}`}
        >
          {groups.length
            ? groups.map((group) => (
                <div key={group.label}>
                  <div className="px-2.5 py-1.5 font-mono text-[10px] uppercase tracking-wider text-atelier-smoke dark:text-atelier-cream/40">
                    {group.label}
                  </div>
                  {group.options.map((option) => (
                    <SelectOptionButton
                      key={`${group.label}-${option.value}`}
                      option={option}
                      selected={option.value === value}
                      active={option.value === activeOption?.value}
                      visualSize={visualSize}
                      onSelect={selectOption}
                      refCallback={(element) => {
                        optionRefs.current[option.value] = element;
                      }}
                    />
                  ))}
                </div>
              ))
            : options.map((option) => (
                <SelectOptionButton
                  key={option.value}
                  option={option}
                  selected={option.value === value}
                  active={option.value === activeOption?.value}
                  visualSize={visualSize}
                  onSelect={selectOption}
                  refCallback={(element) => {
                    optionRefs.current[option.value] = element;
                  }}
                />
              ))}
        </div>
      ) : null}
    </div>
  );
}

function SelectOptionButton({
  option,
  selected,
  active,
  visualSize,
  onSelect,
  refCallback,
}: {
  option: SelectFieldOption;
  selected: boolean;
  active: boolean;
  visualSize: "sm" | "md";
  onSelect: (option: SelectFieldOption) => void;
  refCallback: (element: HTMLButtonElement | null) => void;
}) {
  const sizeClassName = visualSize === "sm" ? "min-h-8 px-2 py-1.5 text-xs" : "min-h-9 px-2.5 py-2 text-sm";
  const stateClassName = selected
    ? "bg-atelier-vermilion/5 text-atelier-vermilion dark:bg-atelier-vermilion/12 dark:text-atelier-cream"
    : active
      ? "bg-atelier-cream text-atelier-ink dark:bg-atelier-cream/10 dark:text-atelier-cream"
      : "text-atelier-sepia hover:bg-atelier-cream hover:text-atelier-ink dark:text-atelier-cream/80 dark:hover:bg-atelier-cream/10 dark:hover:text-atelier-cream";

  return (
    <button
      ref={refCallback}
      type="button"
      role="option"
      aria-selected={selected}
      disabled={option.disabled}
      onClick={() => onSelect(option)}
      className={`flex w-full items-center gap-2 text-left font-medium outline-none transition-colors disabled:cursor-not-allowed disabled:text-atelier-smoke disabled:opacity-60 dark:disabled:text-atelier-cream/30 ${sizeClassName} ${stateClassName}`}
    >
      <span className="min-w-0 flex-1 truncate">{option.label}</span>
      {selected ? <Check size={14} className="shrink-0" /> : null}
    </button>
  );
}
