"""
ImageChatPage.tsx 主文件 token 批量迁移（按 token-migration-map.md frozen 合约）。

策略：纯文本 string-to-string 替换，按字符串字面量精确替换 className 中的 Tailwind utility。
每个 Tailwind class 总是用空格、引号、模板字符串边界分隔，所以字面替换是安全的。
"""

import re
import sys

PATH = r"D:\netcup\ProductFlow\web\src\pages\ImageChatPage.tsx"
EXTRA_PATHS = [
    r"D:\netcup\ProductFlow\web\src\pages\image-chat\ImageChatMainStage.tsx",
    r"D:\netcup\ProductFlow\web\src\pages\image-chat\GenerationCanvasPlaceholder.tsx",
    # G2 - ProductDetailPage (excluding WorkflowCanvas + WorkflowNodeCard per R6 / G2 grill)
    r"D:\netcup\ProductFlow\web\src\pages\ProductDetailPage.tsx",
    r"D:\netcup\ProductFlow\web\src\pages\product-detail\InspectorPanel.tsx",
    r"D:\netcup\ProductFlow\web\src\pages\product-detail\TemplateGroupsPanel.tsx",
    r"D:\netcup\ProductFlow\web\src\pages\product-detail\RunsPanel.tsx",
    r"D:\netcup\ProductFlow\web\src\pages\product-detail\ImageDownloadComponents.tsx",
    r"D:\netcup\ProductFlow\web\src\pages\product-detail\ImagesPanel.tsx",
    r"D:\netcup\ProductFlow\web\src\pages\product-detail\ImagePreviewModal.tsx",
    r"D:\netcup\ProductFlow\web\src\pages\product-detail\SidebarTabButton.tsx",
    r"D:\netcup\ProductFlow\web\src\pages\product-detail\TextArea.tsx",
    # atelier-ui-polish (2026-05-26) - SettingsPage token 迁移
    r"D:\netcup\ProductFlow\web\src\pages\SettingsPage.tsx",
]

# 替换映射（按 token-migration-map Section 1-6）
# 顺序很重要：长串先处理（如 bg-slate-50/70 必须在 bg-slate-50 之前）
RAW_MAP = [
    # ===== chrome - bg =====
    ("bg-slate-100", "bg-atelier-cream"),
    ("bg-slate-50/70", "bg-atelier-paper/70"),
    ("bg-slate-50", "bg-atelier-paper"),
    ("bg-slate-300", "bg-atelier-smoke/40"),
    ("bg-slate-200/70", "bg-atelier-smoke/30"),
    ("bg-slate-200", "bg-atelier-smoke/30"),
    ("bg-slate-950/45", "bg-atelier-ink/45"),
    ("bg-slate-950/42", "bg-atelier-ink/42"),
    ("bg-zinc-50", "bg-atelier-paper"),
    ("bg-zinc-100", "bg-atelier-cream"),
    ("bg-zinc-200/70", "bg-atelier-kraft/70"),
    ("bg-zinc-200", "bg-atelier-kraft"),
    ("bg-zinc-300", "bg-atelier-smoke/40"),
    ("bg-zinc-950", "bg-atelier-ink"),
    ("bg-zinc-900", "bg-atelier-ink"),
    ("bg-zinc-800", "bg-atelier-ink"),
    ("bg-gray-50", "bg-atelier-paper"),
    ("bg-white/95", "bg-atelier-paper/95"),
    ("bg-white/96", "bg-atelier-paper/96"),
    ("bg-white/90", "bg-atelier-paper/90"),
    ("bg-white/86", "bg-atelier-paper/86"),
    ("bg-white/80", "bg-atelier-paper/80"),
    ("bg-white/60", "bg-atelier-paper/60"),
    ("bg-white", "bg-atelier-paper"),
    ("disabled:bg-slate-900", "disabled:bg-atelier-cream/10"),
    ("disabled:bg-slate-50", "disabled:bg-atelier-paper"),
    ("hover:bg-zinc-50", "hover:bg-atelier-cream"),
    ("hover:bg-zinc-100", "hover:bg-atelier-cream"),
    ("hover:bg-zinc-200", "hover:bg-atelier-kraft"),
    ("hover:bg-zinc-300", "hover:bg-atelier-smoke/40"),
    ("hover:bg-zinc-800", "hover:bg-atelier-vermilion-dark"),
    ("hover:bg-zinc-50/80", "hover:bg-atelier-cream/80"),
    ("hover:bg-slate-50", "hover:bg-atelier-cream"),
    ("hover:bg-slate-100", "hover:bg-atelier-cream"),
    ("hover:bg-slate-200", "hover:bg-atelier-kraft"),
    ("hover:bg-slate-300", "hover:bg-atelier-smoke/40"),
    ("hover:bg-white", "hover:bg-atelier-paper"),

    # ===== chrome - text =====
    ("text-slate-950", "text-atelier-ink"),
    ("text-slate-900", "text-atelier-ink"),
    ("text-slate-800", "text-atelier-ink"),
    ("text-slate-700", "text-atelier-sepia"),
    ("text-slate-600", "text-atelier-sepia"),
    ("text-slate-500", "text-atelier-smoke"),
    ("text-slate-400", "text-atelier-smoke"),
    ("text-slate-300", "text-atelier-smoke"),
    ("text-slate-200", "text-atelier-cream"),
    ("text-slate-100", "text-atelier-cream"),
    ("text-zinc-950", "text-atelier-ink"),
    ("text-zinc-900", "text-atelier-ink"),
    ("text-zinc-800", "text-atelier-ink"),
    ("text-zinc-700", "text-atelier-sepia"),
    ("text-zinc-600", "text-atelier-sepia"),
    ("text-zinc-500", "text-atelier-smoke"),
    ("text-zinc-400", "text-atelier-smoke"),
    ("text-zinc-300", "text-atelier-smoke"),
    ("text-white", "text-atelier-cream"),
    ("hover:text-zinc-900", "hover:text-atelier-ink"),
    ("hover:text-zinc-950", "hover:text-atelier-ink"),
    ("hover:text-slate-900", "hover:text-atelier-ink"),
    ("hover:text-slate-950", "hover:text-atelier-ink"),
    ("hover:text-slate-700", "hover:text-atelier-sepia"),
    ("disabled:text-slate-500", "disabled:text-atelier-smoke"),
    ("disabled:text-zinc-500", "disabled:text-atelier-smoke"),

    # ===== chrome - border =====
    ("border-slate-100", "border-atelier-smoke/20"),
    ("border-slate-200", "border-atelier-smoke/30"),
    ("border-slate-300", "border-atelier-smoke/50"),
    ("border-slate-700/80", "border-atelier-cream/15"),
    ("border-slate-700", "border-atelier-cream/15"),
    ("border-slate-800", "border-atelier-cream/15"),
    ("border-slate-600/80", "border-atelier-cream/15"),
    ("border-slate-600", "border-atelier-cream/15"),
    ("border-zinc-100", "border-atelier-smoke/20"),
    ("border-zinc-200", "border-atelier-smoke/30"),
    ("border-zinc-300", "border-atelier-smoke/50"),
    ("border-zinc-700/80", "border-atelier-cream/15"),
    ("border-zinc-700", "border-atelier-cream/15"),
    ("hover:border-zinc-300", "hover:border-atelier-smoke/50"),
    ("hover:border-zinc-400", "hover:border-atelier-smoke/50"),
    ("hover:border-slate-300", "hover:border-atelier-smoke/50"),
    ("hover:border-slate-400", "hover:border-atelier-smoke/50"),

    # ===== chrome - divide / ring =====
    ("divide-slate-100", "divide-atelier-smoke/20"),
    ("divide-slate-200", "divide-atelier-smoke/30"),
    ("divide-slate-800", "divide-atelier-cream/15"),
    ("ring-slate-200/80", "ring-atelier-smoke/30"),
    ("ring-slate-200", "ring-atelier-smoke/30"),
    ("ring-slate-700", "ring-atelier-cream/15"),
    ("ring-slate-600/80", "ring-atelier-cream/15"),
    ("ring-slate-600", "ring-atelier-cream/15"),
    ("ring-zinc-200", "ring-atelier-smoke/30"),
    ("ring-zinc-700", "ring-atelier-cream/15"),
    ("dark:divide-slate-800", "dark:divide-atelier-cream/15"),

    # ===== dark hex 自定义冷蓝 → atelier 三档白名单 =====
    ("dark:bg-[#060a12]/78", "dark:bg-[#1A1410]/78"),
    ("dark:bg-[#060a12]", "dark:bg-[#1A1410]"),
    ("dark:bg-[#0a1020]", "dark:bg-[#1F1812]"),
    ("dark:bg-[#0b1220]/88", "dark:bg-[#1F1812]/88"),
    ("dark:bg-[#0b1220]", "dark:bg-[#1F1812]"),
    ("dark:bg-[#0f1726]", "dark:bg-[#1F1812]"),
    ("dark:bg-[#151f33]/80", "dark:bg-[#241B14]/80"),
    ("dark:bg-[#151f33]/70", "dark:bg-[#241B14]/70"),
    ("dark:bg-[#151f33]", "dark:bg-[#241B14]"),
    ("dark:bg-[#1a2740]/95", "dark:bg-[#241B14]/95"),
    ("dark:bg-[#1a2740]/92", "dark:bg-[#241B14]/92"),
    ("dark:bg-[#1a2740]", "dark:bg-[#241B14]"),
    ("dark:bg-[#121b2d]", "dark:bg-[#1A1410]"),
    ("dark:from-[#060a12]/78", "dark:from-[#1A1410]/78"),
    ("dark:from-[#060a12]", "dark:from-[#1A1410]"),
    ("dark:to-[#151f33]/70", "dark:to-[#241B14]/70"),
    ("dark:to-[#151f33]", "dark:to-[#241B14]"),
    ("dark:hover:bg-[#1a2740]", "dark:hover:bg-[#241B14]"),
    ("dark:hover:bg-[#151f33]", "dark:hover:bg-[#241B14]"),

    # ===== dark - bg =====
    ("dark:bg-slate-950/94", "dark:bg-[#1A1410]/94"),
    ("dark:bg-slate-950/90", "dark:bg-[#1A1410]/90"),
    ("dark:bg-slate-950/88", "dark:bg-[#1A1410]/88"),
    ("dark:bg-slate-950/80", "dark:bg-[#1A1410]/80"),
    ("dark:bg-slate-950/70", "dark:bg-[#1A1410]/70"),
    ("dark:bg-slate-950/60", "dark:bg-[#1A1410]/60"),
    ("dark:bg-slate-950/45", "dark:bg-[#1A1410]/45"),
    ("dark:bg-slate-950/42", "dark:bg-[#1A1410]/42"),
    ("dark:bg-slate-950/40", "dark:bg-[#1A1410]/40"),
    ("dark:bg-slate-950", "dark:bg-atelier-ink"),
    ("dark:bg-slate-900", "dark:bg-[#1F1812]"),
    ("dark:bg-slate-800/80", "dark:bg-[#241B14]/80"),
    ("dark:bg-slate-800/60", "dark:bg-[#241B14]/60"),
    ("dark:bg-slate-800", "dark:bg-[#241B14]"),
    ("dark:bg-slate-700/80", "dark:bg-atelier-cream/15"),
    ("dark:bg-slate-700", "dark:bg-atelier-cream/15"),
    ("dark:bg-slate-600/80", "dark:bg-atelier-cream/15"),
    ("dark:bg-slate-600", "dark:bg-atelier-cream/30"),
    ("dark:hover:bg-slate-800", "dark:hover:bg-[#241B14]"),
    ("dark:hover:bg-slate-700", "dark:hover:bg-atelier-cream/15"),

    # ===== dark - text =====
    ("dark:text-white", "dark:text-atelier-cream"),
    ("dark:text-slate-100", "dark:text-atelier-cream"),
    ("dark:text-slate-200", "dark:text-atelier-cream"),
    ("dark:text-slate-300", "dark:text-atelier-cream/60"),
    ("dark:text-slate-400", "dark:text-atelier-cream/40"),
    ("dark:text-slate-500", "dark:text-atelier-cream/40"),
    ("dark:text-slate-600", "dark:text-atelier-cream/40"),
    ("dark:text-slate-700", "dark:text-atelier-cream/60"),

    # ===== dark - border =====
    ("dark:border-slate-800/80", "dark:border-atelier-cream/15"),
    ("dark:border-slate-800", "dark:border-atelier-cream/15"),
    ("dark:border-slate-700/80", "dark:border-atelier-cream/15"),
    ("dark:border-slate-700/75", "dark:border-atelier-cream/15"),
    ("dark:border-slate-700", "dark:border-atelier-cream/15"),
    ("dark:border-slate-600/80", "dark:border-atelier-cream/15"),
    ("dark:border-slate-600", "dark:border-atelier-cream/15"),
    ("dark:divide-slate-800", "dark:divide-atelier-cream/15"),
    ("dark:ring-slate-700", "dark:ring-atelier-cream/15"),
    ("dark:ring-slate-600/80", "dark:ring-atelier-cream/15"),
    ("dark:ring-slate-600", "dark:ring-atelier-cream/15"),

    # ===== indigo (light accent) =====
    ("bg-indigo-950/15", "bg-atelier-vermilion/10"),
    ("from-indigo-950/5", "from-atelier-vermilion/5"),
    ("via-indigo-900/10", "via-atelier-vermilion/10"),
    ("to-purple-950/15", "to-atelier-vermilion/15"),
    ("bg-indigo-600", "bg-atelier-ink"),
    ("bg-indigo-500", "bg-atelier-vermilion"),
    ("bg-indigo-400/60", "bg-atelier-vermilion/40"),
    ("bg-indigo-300/50", "bg-atelier-vermilion/30"),
    ("bg-indigo-200/30", "bg-atelier-vermilion/20"),
    ("bg-indigo-50/70", "bg-atelier-vermilion/5"),
    ("bg-indigo-50/40", "bg-atelier-vermilion/5"),
    ("bg-indigo-50", "bg-atelier-vermilion/5"),
    ("hover:bg-indigo-700", "hover:bg-atelier-vermilion-dark"),
    ("hover:bg-indigo-500", "hover:bg-atelier-vermilion"),
    ("hover:bg-indigo-50/70", "hover:bg-atelier-vermilion/5"),
    ("hover:bg-indigo-50/40", "hover:bg-atelier-vermilion/5"),
    ("hover:bg-indigo-50", "hover:bg-atelier-vermilion/5"),
    ("text-indigo-950", "text-atelier-ink"),
    ("text-indigo-900", "text-atelier-vermilion-dark"),
    ("text-indigo-700", "text-atelier-vermilion"),
    ("text-indigo-600", "text-atelier-vermilion"),
    ("text-indigo-500", "text-atelier-vermilion"),
    ("text-indigo-200", "text-atelier-vermilion"),
    ("text-indigo-100", "text-atelier-cream"),
    ("hover:text-indigo-700", "hover:text-atelier-vermilion"),
    ("hover:text-indigo-600", "hover:text-atelier-vermilion"),
    ("border-indigo-500", "border-atelier-vermilion"),
    ("border-indigo-400", "border-atelier-vermilion"),
    ("border-indigo-300", "border-atelier-vermilion/30"),
    ("border-indigo-200", "border-atelier-vermilion/30"),
    ("border-indigo-100", "border-atelier-vermilion/30"),
    ("hover:border-indigo-200", "hover:border-atelier-vermilion/30"),
    ("ring-indigo-500", "ring-atelier-vermilion"),
    ("ring-indigo-200/80", "ring-atelier-vermilion/30"),
    ("ring-indigo-200", "ring-atelier-vermilion/30"),
    ("ring-indigo-100", "ring-atelier-vermilion/20"),
    ("focus:ring-indigo-500", "focus:ring-atelier-vermilion"),
    ("focus:ring-indigo-100", "focus:ring-atelier-vermilion/20"),
    ("focus-visible:ring-indigo-500", "focus-visible:ring-atelier-vermilion"),
    ("focus:border-indigo-500", "focus:border-atelier-vermilion"),
    ("shadow-indigo-600/20", "shadow-paper-md"),
    ("shadow-indigo-600/16", "shadow-paper-md"),
    ("shadow-indigo-500/20", "shadow-paper-md"),
    ("shadow-indigo-100", "shadow-paper-sm"),
    ("shadow-indigo-200/70", "shadow-paper-md"),

    # ===== dark - violet (accent) =====
    ("bg-violet-400/40", "bg-atelier-vermilion/30"),
    ("dark:bg-violet-600", "dark:bg-atelier-vermilion"),
    ("dark:bg-violet-500/85", "dark:bg-atelier-vermilion/85"),
    ("dark:bg-violet-500/30", "dark:bg-atelier-vermilion/15"),
    ("dark:bg-violet-500/20", "dark:bg-atelier-vermilion/15"),
    ("dark:bg-violet-500/18", "dark:bg-atelier-vermilion/15"),
    ("dark:bg-violet-500/15", "dark:bg-atelier-vermilion/10"),
    ("dark:bg-violet-500/14", "dark:bg-atelier-vermilion/10"),
    ("dark:bg-violet-500/12", "dark:bg-atelier-vermilion/10"),
    ("dark:bg-violet-500/10", "dark:bg-atelier-vermilion/10"),
    ("dark:bg-violet-500", "dark:bg-atelier-vermilion"),
    ("dark:hover:bg-violet-500/30", "dark:hover:bg-atelier-vermilion/15"),
    ("dark:hover:bg-violet-500/15", "dark:hover:bg-atelier-vermilion/10"),
    ("dark:hover:bg-violet-500/12", "dark:hover:bg-atelier-vermilion/10"),
    ("dark:hover:bg-violet-500/10", "dark:hover:bg-atelier-vermilion/10"),
    ("dark:hover:bg-violet-400", "dark:hover:bg-atelier-vermilion-dark"),
    ("dark:text-violet-400", "dark:text-atelier-vermilion"),
    ("dark:text-violet-300", "dark:text-atelier-vermilion"),
    ("dark:text-violet-200", "dark:text-atelier-vermilion"),
    ("dark:text-violet-100", "dark:text-atelier-cream"),
    ("dark:text-indigo-400", "dark:text-atelier-vermilion"),
    ("dark:text-indigo-300", "dark:text-atelier-vermilion"),
    ("dark:hover:text-violet-100", "dark:hover:text-atelier-cream"),
    ("dark:hover:text-violet-200", "dark:hover:text-atelier-vermilion"),
    ("dark:border-violet-500/80", "dark:border-atelier-vermilion/80"),
    ("dark:border-violet-500/45", "dark:border-atelier-vermilion/40"),
    ("dark:border-violet-400/60", "dark:border-atelier-vermilion/40"),
    ("dark:border-violet-400/55", "dark:border-atelier-vermilion/40"),
    ("dark:border-violet-400/50", "dark:border-atelier-vermilion/40"),
    ("dark:border-violet-400/45", "dark:border-atelier-vermilion/40"),
    ("dark:border-violet-400/40", "dark:border-atelier-vermilion/40"),
    ("dark:border-violet-400/35", "dark:border-atelier-vermilion/40"),
    ("dark:border-violet-400/30", "dark:border-atelier-vermilion/30"),
    ("dark:border-violet-400", "dark:border-atelier-vermilion"),
    ("dark:hover:border-violet-500/45", "dark:hover:border-atelier-vermilion/40"),
    ("dark:hover:border-violet-400/60", "dark:hover:border-atelier-vermilion/40"),
    ("dark:hover:border-violet-400/55", "dark:hover:border-atelier-vermilion/40"),
    ("dark:hover:border-violet-400/50", "dark:hover:border-atelier-vermilion/40"),
    ("dark:hover:border-violet-400/45", "dark:hover:border-atelier-vermilion/40"),
    ("dark:ring-violet-400/45", "dark:ring-atelier-vermilion/40"),
    ("dark:ring-violet-400/40", "dark:ring-atelier-vermilion/40"),
    ("dark:ring-violet-400/35", "dark:ring-atelier-vermilion/30"),
    ("dark:ring-violet-400/30", "dark:ring-atelier-vermilion/30"),
    ("dark:ring-violet-400/20", "dark:ring-atelier-vermilion/20"),
    ("dark:ring-violet-400", "dark:ring-atelier-vermilion"),
    ("dark:ring-violet-300/40", "dark:ring-atelier-vermilion/40"),
    ("dark:ring-violet-300/35", "dark:ring-atelier-vermilion/30"),
    ("dark:ring-violet-300/30", "dark:ring-atelier-vermilion/30"),
    ("dark:ring-violet-300", "dark:ring-atelier-vermilion"),
    ("dark:ring-violet-200/30", "dark:ring-atelier-vermilion/30"),
    ("dark:focus-visible:ring-violet-400", "dark:focus-visible:ring-atelier-vermilion"),
    ("dark:focus-visible:ring-violet-300", "dark:focus-visible:ring-atelier-vermilion"),
    ("dark:focus:border-violet-400", "dark:focus:border-atelier-vermilion"),
    ("dark:focus:border-violet-300", "dark:focus:border-atelier-vermilion"),
    ("dark:focus:ring-violet-400/20", "dark:focus:ring-atelier-vermilion/20"),
    ("dark:shadow-violet-950/40", "dark:shadow-paper-md"),
    ("dark:shadow-violet-950/35", "dark:shadow-paper-md"),
    ("dark:shadow-violet-950/30", "dark:shadow-paper-md"),
    ("dark:shadow-violet-900/45", "dark:shadow-paper-md"),
    ("dark:shadow-violet-900/35", "dark:shadow-paper-md"),

    # ===== gradient (violet-500 / fuchsia-500 / indigo-500) → solid =====
    ("dark:from-indigo-500 dark:to-violet-500", "dark:bg-atelier-vermilion"),
    ("dark:from-indigo-500 dark:via-violet-500 dark:to-fuchsia-500", "dark:bg-atelier-vermilion"),
    ("dark:bg-gradient-to-r dark:bg-atelier-vermilion", "dark:bg-atelier-vermilion"),
    ("dark:bg-gradient-to-br dark:bg-atelier-vermilion", "dark:bg-atelier-vermilion"),
    ("from-slate-950/80", "from-atelier-ink/80"),
    ("via-slate-950/24", "via-atelier-ink/24"),

    # ===== red - destructive (长串先匹配，防止子串误替换) =====
    ("dark:hover:bg-red-500/12", "dark:hover:bg-atelier-vermilion-dark/15"),
    ("dark:bg-red-500/15", "dark:bg-atelier-vermilion-dark/15"),
    ("dark:bg-red-500/10", "dark:bg-atelier-vermilion-dark/15"),
    ("dark:text-red-200", "dark:text-atelier-vermilion"),
    ("dark:text-red-300", "dark:text-atelier-vermilion"),
    ("dark:text-red-100", "dark:text-atelier-vermilion"),
    ("dark:border-red-400/40", "dark:border-atelier-vermilion/40"),
    ("dark:border-red-400/35", "dark:border-atelier-vermilion/40"),
    ("shadow-red-500/20", "shadow-paper-md"),
    ("hover:bg-red-500", "hover:bg-atelier-vermilion"),
    ("hover:bg-red-600", "hover:bg-atelier-vermilion-dark"),
    ("bg-red-600", "bg-atelier-vermilion-dark"),
    ("bg-red-500", "bg-atelier-vermilion-dark"),
    ("text-red-700", "text-atelier-vermilion-dark"),
    ("text-red-600", "text-atelier-vermilion-dark"),
    ("text-red-500/80", "text-atelier-vermilion-dark/80"),
    ("text-red-500", "text-atelier-vermilion-dark"),
    ("border-red-300", "border-atelier-vermilion-dark/50"),
    ("border-red-200", "border-atelier-vermilion-dark/30"),
    ("hover:text-red-600", "hover:text-atelier-vermilion-dark"),
    ("hover:text-red-300", "hover:text-atelier-vermilion"),
    ("bg-red-50", "bg-atelier-vermilion-dark/5"),

    # ===== emerald - success (no atelier-emerald per G7; soften to atelier 中性 + accent 提示) =====
    ("bg-emerald-50", "bg-atelier-cream"),
    ("text-emerald-700", "text-atelier-sepia"),
    ("border-emerald-200", "border-atelier-smoke/40"),
    ("dark:bg-emerald-500/10", "dark:bg-atelier-cream/5"),
    ("dark:text-emerald-200", "dark:text-atelier-cream/70"),
    ("dark:border-emerald-400/35", "dark:border-atelier-cream/15"),

    # ===== amber - warning (no atelier-amber; soften to kraft + sepia, 类似 G3 placeholderStatusClass queued) =====
    ("bg-amber-50", "bg-atelier-kraft"),
    ("text-amber-800", "text-atelier-sepia"),
    ("text-amber-700", "text-atelier-sepia"),
    ("border-amber-200", "border-atelier-smoke/40"),
    ("dark:bg-amber-500/10", "dark:bg-atelier-cream/10"),
    ("dark:text-amber-200", "dark:text-atelier-cream/70"),
    ("dark:border-amber-400/35", "dark:border-atelier-cream/15"),
    ("dark:border-amber-300/40", "dark:border-atelier-cream/15"),

    # ===== blue - 非 StatusPill 中 notice/banner 上下文（StatusPill 例外不动）→ atelier 弱化 =====
    ("bg-blue-50", "bg-atelier-vermilion/5"),
    ("text-blue-700", "text-atelier-vermilion"),
    ("text-blue-600", "text-atelier-vermilion"),
    ("border-blue-200", "border-atelier-vermilion/30"),
    ("border-blue-500", "border-atelier-vermilion"),
    ("dark:bg-blue-500/10", "dark:bg-atelier-vermilion/10"),
    ("dark:text-blue-200", "dark:text-atelier-vermilion"),
    ("dark:border-blue-400/35", "dark:border-atelier-vermilion/40"),

    # ===== shadow 残留 =====
    ("dark:shadow-black/20", "dark:shadow-paper-md"),
    ("dark:shadow-black/30", "dark:shadow-paper-md"),
    ("shadow-indigo-950/10", "shadow-paper-md"),

    # ===== to/from accent gradient 残留 =====
    ("to-indigo-50/40", "to-atelier-vermilion/5"),
    ("to-indigo-50", "to-atelier-vermilion/5"),
    ("from-indigo-50", "from-atelier-vermilion/5"),

    # ===== gray fallback =====
    ("text-gray-700", "text-atelier-sepia"),
    ("text-gray-500", "text-atelier-smoke"),
    ("text-gray-400", "text-atelier-smoke"),

    # ===== shadow 色去除 =====
    ("shadow-[12px_0_36px_rgba(0,0,0,0.24)]", "shadow-paper-md"),
    ("shadow-[-12px_0_36px_rgba(0,0,0,0.24)]", "shadow-paper-md"),
    ("shadow-[0_-8px_24px_rgba(15,23,42,0.04)]", "shadow-paper-sm"),
    ("shadow-[0_-8px_24px_rgba(15,23,42,0.10)]", "shadow-paper-sm"),
    ("shadow-[0_-6px_18px_rgba(15,23,42,0.12)]", "shadow-paper-sm"),
    ("shadow-[0_-12px_34px_rgba(15,23,42,0.16)]", "shadow-paper-md"),
    ("dark:shadow-[12px_0_36px_rgba(0,0,0,0.24)]", "dark:shadow-paper-md"),
    ("dark:shadow-[-12px_0_36px_rgba(0,0,0,0.24)]", "dark:shadow-paper-md"),
    ("dark:shadow-[0_-18px_40px_rgba(0,0,0,0.24)]", "dark:shadow-paper-md"),
    ("dark:shadow-[0_-18px_40px_rgba(0,0,0,0.32)]", "dark:shadow-paper-md"),
    ("dark:shadow-[0_-12px_28px_rgba(0,0,0,0.30)]", "dark:shadow-paper-md"),
    ("dark:shadow-[0_-18px_42px_rgba(0,0,0,0.34)]", "dark:shadow-paper-md"),
    ("dark:shadow-black/30", "dark:shadow-paper-md"),
]


def main() -> int:
    total_changed = 0
    total_mappings = 0
    for path in [PATH] + EXTRA_PATHS:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        original = content
        counts: list[tuple[str, str, int]] = []
        for old, new in RAW_MAP:
            n = content.count(old)
            if n:
                content = content.replace(old, new)
                counts.append((old, new, n))
        changed = sum(c for _, _, c in counts)
        if content == original:
            print(f"{path}: no changes")
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"{path}: replaced {changed} token instances across {len(counts)} mappings")
        total_changed += changed
        total_mappings += len(counts)
    print(f"total: {total_changed} replacements across {total_mappings} mapping hits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
