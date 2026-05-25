import type { ReactNode } from "react";

interface SidebarTabButtonProps {
  active: boolean;
  label: string;
  title: string;
  icon: ReactNode;
  onClick: () => void;
}

export function SidebarTabButton({
  active,
  label,
  title,
  icon,
  onClick,
}: SidebarTabButtonProps) {
  return (
    <button
      type="button"
      aria-pressed={active}
      title={title}
      onClick={onClick}
      className={`flex w-full flex-col items-center rounded-xl px-1 py-2 text-[10px] font-medium transition-all transition-spring ${
        active
          ? "bg-atelier-paper text-atelier-vermilion shadow-[0_2px_8px_rgba(99,102,241,0.15)] ring-1 ring-atelier-vermilion/30 scale-[1.05] dark:bg-[#241B14] dark:text-atelier-cream dark:ring-1 dark:ring-atelier-vermilion/50 dark:shadow-[0_4px_12px_rgba(0,0,0,0.3)]"
          : "text-atelier-smoke hover:scale-[1.05] hover:bg-atelier-cream hover:text-atelier-ink dark:text-atelier-smoke dark:hover:bg-[#241B14]/60 dark:hover:text-atelier-cream"
      }`}
    >
      <span className={`transition-transform duration-300 ${active ? "scale-110" : ""}`}>{icon}</span>
      <span className="mt-1 leading-tight">{label}</span>
    </button>
  );
}
