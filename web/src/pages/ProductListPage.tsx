import { useEffect, useState } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowRight,
  Image as ImageIcon,
  Plus,
  Trash2,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

import { ConfirmDialog } from "../components/ConfirmDialog";
import { StatusPill } from "../components/StatusPill";
import { TopNav } from "../components/TopNav";
import { StaggerGrid } from "../components/motion/StaggerGrid";
import { api, ApiError } from "../lib/api";
import { formatPrice, formatShortDate } from "../lib/format";
import { useI18n } from "../lib/preferences";
import type { ProductSummary } from "../lib/types";

const PAGE_SIZE = 12;
const PRODUCT_LIST_STALE_TIME_MS = 60_000;
const RUNTIME_CONFIG_STALE_TIME_MS = 5 * 60_000;

export function ProductListPage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [deleteError, setDeleteError] = useState("");
  const [pendingDeleteProduct, setPendingDeleteProduct] = useState<ProductSummary | null>(null);

  const productsQuery = useQuery({
    queryKey: ["products", page, PAGE_SIZE],
    queryFn: () => api.listProducts({ page, page_size: PAGE_SIZE }),
    placeholderData: keepPreviousData,
    staleTime: PRODUCT_LIST_STALE_TIME_MS,
  });
  const runtimeConfigQuery = useQuery({
    queryKey: ["runtime-config"],
    queryFn: api.getRuntimeConfig,
    staleTime: RUNTIME_CONFIG_STALE_TIME_MS,
  });
  const sessionQuery = useQuery({
    queryKey: ["session"],
    queryFn: api.getSessionState,
    staleTime: PRODUCT_LIST_STALE_TIME_MS,
  });

  const products = productsQuery.data?.items ?? [];
  const total = productsQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const deletionEnabled = runtimeConfigQuery.data?.deletion_enabled ?? false;
  const posterReadyCount = products.filter((p) => p.workflow_state === "poster_ready").length;
  const copyReadyCount = products.filter(
    (p) => p.workflow_state === "copy_ready" || p.workflow_state === "poster_ready",
  ).length;

  useEffect(() => {
    if (productsQuery.data && page > totalPages) {
      setPage(totalPages);
    }
  }, [page, productsQuery.data, totalPages]);

  const logoutMutation = useMutation({
    mutationFn: api.destroySession,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["session"] });
      navigate("/login", { replace: true });
    },
  });

  const deleteProductMutation = useMutation({
    mutationFn: (productId: string) => api.deleteProduct(productId),
    onSuccess: async () => {
      setDeleteError("");
      setPendingDeleteProduct(null);
      await queryClient.invalidateQueries({ queryKey: ["products"] });
      if (products.length === 1 && page > 1) {
        setPage((current) => Math.max(1, current - 1));
      }
    },
    onError: (mutationError) => {
      setPendingDeleteProduct(null);
      setDeleteError(
        mutationError instanceof ApiError ? mutationError.detail : t("products.deleteFailed"),
      );
    },
  });

  const handleDeleteProduct = (product: ProductSummary) => {
    if (!deletionEnabled) {
      setDeleteError(t("products.deleteDisabled"));
      return;
    }
    setPendingDeleteProduct(product);
  };

  return (
    <div className="flex min-h-screen flex-col bg-atelier-cream dark:bg-[#1A1410]">
      <TopNav
        onHome={() => navigate("/products")}
        onLogout={() => logoutMutation.mutate()}
        session={sessionQuery.data}
      />

      <main className="mx-auto flex w-full max-w-4xl flex-1 px-6 py-12 lg:py-16">
        <div className="w-full space-y-10">
          {/* Hero — D 风衬线标题 + ornament + 简化 metrics */}
          <section className="border-b border-atelier-smoke/30 pb-10 dark:border-atelier-cream/15">
            <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-atelier-smoke">
              {t("products.heroEyebrow")}
            </p>
            <h1 className="mt-3 font-display text-5xl italic text-atelier-ink dark:text-atelier-cream">
              {t("products.title")}
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-atelier-sepia dark:text-atelier-cream/60">
              {t("products.description")}
            </p>

            <div className="mt-6 flex items-center justify-between gap-6">
              <div className="grid grid-cols-3 gap-8 text-atelier-ink dark:text-atelier-cream">
                <MetricCard label={t("products.totalMetric")} value={total} />
                <MetricCard label={t("products.copyReadyMetric")} value={copyReadyCount} />
                <MetricCard label={t("products.posterReadyMetric")} value={posterReadyCount} />
              </div>

              <button
                type="button"
                onClick={() => navigate("/products/new")}
                className="group inline-flex items-center gap-2 border border-atelier-ink bg-atelier-ink px-5 py-2.5 font-display text-base italic text-atelier-cream transition-colors hover:border-atelier-vermilion hover:bg-atelier-vermilion dark:border-atelier-cream dark:bg-atelier-cream dark:text-atelier-ink dark:hover:border-atelier-vermilion dark:hover:bg-atelier-vermilion dark:hover:text-atelier-cream"
              >
                <Plus size={16} aria-hidden="true" />
                <span>{t("products.new")}</span>
              </button>
            </div>
          </section>

          {/* List */}
          <section>
            <div className="mb-4 flex items-end justify-between">
              <div>
                <h2 className="font-display text-2xl italic text-atelier-ink dark:text-atelier-cream">
                  {t("products.listTitle")}
                </h2>
                <p className="mt-1 font-mono text-xs text-atelier-smoke">
                  {t("products.paginationSummary", { page, totalPages, total })}
                </p>
              </div>
              {products.length ? (
                <Pagination
                  page={page}
                  totalPages={totalPages}
                  onPageChange={setPage}
                  disabled={productsQuery.isFetching}
                />
              ) : null}
            </div>

            {deleteError ? (
              <div className="mb-4 border border-atelier-vermilion/30 bg-atelier-vermilion/5 px-4 py-3 text-sm text-atelier-vermilion-dark dark:border-atelier-vermilion/40 dark:bg-atelier-vermilion/10 dark:text-atelier-vermilion">
                {deleteError}
              </div>
            ) : null}

            {productsQuery.isLoading ? (
              <LoadingList />
            ) : productsQuery.isError ? (
              <div className="border border-atelier-vermilion/30 bg-atelier-vermilion/5 px-4 py-3 text-sm text-atelier-vermilion-dark dark:border-atelier-vermilion/40 dark:bg-atelier-vermilion/10 dark:text-atelier-vermilion">
                {t("products.loadFailed")}
              </div>
            ) : products.length ? (
              <StaggerGrid className="divide-y divide-atelier-smoke/30 border-y border-atelier-smoke/30 dark:divide-atelier-cream/15 dark:border-atelier-cream/15">
                {products.map((product) => (
                  <ProductRow
                    key={product.id}
                    product={product}
                    deletionEnabled={deletionEnabled}
                    isDeleting={deleteProductMutation.isPending}
                    onOpen={() => navigate(`/products/${product.id}`)}
                    onDelete={() => handleDeleteProduct(product)}
                  />
                ))}
              </StaggerGrid>
            ) : (
              <EmptyState onNew={() => navigate("/products/new")} />
            )}

            {products.length ? (
              <div className="mt-8 flex justify-end">
                <Pagination
                  page={page}
                  totalPages={totalPages}
                  onPageChange={setPage}
                  disabled={productsQuery.isFetching}
                />
              </div>
            ) : null}
          </section>
        </div>
      </main>

      <ConfirmDialog
        open={Boolean(pendingDeleteProduct)}
        title={t("products.deleteConfirmTitle")}
        description={
          pendingDeleteProduct ? t("products.deleteConfirm", { name: pendingDeleteProduct.name }) : ""
        }
        confirmLabel={t("confirm.delete.confirm")}
        cancelLabel={t("common.cancel")}
        busy={deleteProductMutation.isPending}
        onClose={() => setPendingDeleteProduct(null)}
        onConfirm={() => {
          if (pendingDeleteProduct) {
            deleteProductMutation.mutate(pendingDeleteProduct.id);
          }
        }}
      />
    </div>
  );
}

// 杂志目录条目 (R2.3 wireframe).
// horizontal layout: thumbnail | title+description | timestamp | actions
function ProductRow({
  product,
  deletionEnabled,
  isDeleting,
  onOpen,
  onDelete,
}: {
  product: ProductSummary;
  deletionEnabled: boolean;
  isDeleting: boolean;
  onOpen: () => void;
  onDelete: () => void;
}) {
  const { t } = useI18n();
  const meta = [
    product.category,
    product.price ? formatPrice(product.price) : null,
    product.source_image_filename,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="group grid grid-cols-[80px_1fr_auto] items-center gap-6 py-6 transition-colors hover:bg-atelier-paper dark:hover:bg-atelier-ink/40">
      <ProductThumbnail product={product} />

      <button
        type="button"
        onClick={onOpen}
        className="min-w-0 text-left"
        title={product.name}
      >
        <h3 className="truncate font-display text-2xl italic text-atelier-ink transition-colors group-hover:text-atelier-vermilion dark:text-atelier-cream dark:group-hover:text-atelier-vermilion">
          {product.name}
        </h3>
        {meta ? (
          <p className="mt-1 truncate text-sm text-atelier-sepia dark:text-atelier-cream/60">
            {meta}
          </p>
        ) : null}
        <div className="mt-2 flex items-center gap-3">
          <StatusPill status={product.workflow_state} />
          <span className="font-mono text-[11px] uppercase tracking-wider text-atelier-smoke">
            edited {formatShortDate(product.updated_at)}
          </span>
        </div>
      </button>

      <div className="flex items-center gap-2 opacity-0 transition-opacity group-hover:opacity-100">
        <button
          type="button"
          onClick={onDelete}
          disabled={isDeleting || !deletionEnabled}
          title={deletionEnabled ? t("products.delete") : t("products.deleteDisabled")}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 font-mono text-[11px] uppercase tracking-wider text-atelier-vermilion-dark transition-colors hover:text-atelier-vermilion disabled:opacity-40 dark:text-atelier-vermilion dark:hover:text-atelier-cream"
        >
          <Trash2 size={13} />
          {t("products.delete")}
        </button>
        <button
          type="button"
          onClick={onOpen}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 font-mono text-[11px] uppercase tracking-wider text-atelier-ink transition-colors hover:text-atelier-vermilion dark:text-atelier-cream dark:hover:text-atelier-vermilion"
        >
          {t("products.open")}
          <ArrowRight size={13} className="transition-transform group-hover:translate-x-0.5" />
        </button>
      </div>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="font-display text-3xl italic tabular-nums">{value}</div>
      <div className="mt-1 font-mono text-[10px] uppercase tracking-widest text-atelier-smoke">
        {label}
      </div>
    </div>
  );
}

function ProductThumbnail({ product }: { product: ProductSummary }) {
  const [failed, setFailed] = useState(false);
  const thumbUrl = product.source_image_thumbnail_url ?? product.source_image_preview_url;
  const shouldShowImage = Boolean(thumbUrl) && !failed;

  return (
    <div className="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden border border-atelier-smoke/30 bg-atelier-paper dark:border-atelier-cream/15 dark:bg-[#221A14]">
      {shouldShowImage && thumbUrl ? (
        <img
          src={api.toApiUrl(thumbUrl)}
          alt={product.source_image_filename ?? product.name}
          className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
          decoding="async"
          loading="lazy"
          onError={() => setFailed(true)}
        />
      ) : (
        <ImageIcon size={20} strokeWidth={1.2} className="text-atelier-smoke" />
      )}
    </div>
  );
}

function LoadingList() {
  return (
    <div className="divide-y divide-atelier-smoke/30 border-y border-atelier-smoke/30 dark:divide-atelier-cream/15 dark:border-atelier-cream/15">
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="grid grid-cols-[80px_1fr_auto] items-center gap-6 py-6">
          <div className="h-20 w-20 animate-shimmer" />
          <div className="space-y-2.5">
            <div className="h-6 w-2/5 animate-shimmer" />
            <div className="h-3.5 w-1/2 animate-shimmer" />
            <div className="h-3 w-1/3 animate-shimmer" />
          </div>
          <div className="h-5 w-24 animate-shimmer" />
        </div>
      ))}
    </div>
  );
}

function EmptyState({ onNew }: { onNew: () => void }) {
  const { t } = useI18n();
  return (
    <div className="border border-dashed border-atelier-smoke/50 bg-atelier-paper px-8 py-20 text-center dark:border-atelier-cream/20 dark:bg-[#221A14]">
      {/* R4 #4 illustration — sketchbook empty */}
      <picture className="mx-auto mb-8 block w-44">
        <source
          type="image/avif"
          srcSet="/illustrations/productlist-empty.avif 1x, /illustrations/productlist-empty@2x.avif 2x"
        />
        <source
          type="image/webp"
          srcSet="/illustrations/productlist-empty.webp 1x, /illustrations/productlist-empty@2x.webp 2x"
        />
        <img
          src="/illustrations/productlist-empty.webp"
          alt=""
          aria-hidden="true"
          loading="lazy"
          decoding="async"
          width={800}
          height={800}
          className="block w-44 select-none"
        />
      </picture>
      <h3 className="font-display text-3xl italic text-atelier-ink dark:text-atelier-cream">
        {t("products.emptyTitle")}
      </h3>
      <p className="mx-auto mt-3 max-w-md text-sm leading-relaxed text-atelier-sepia dark:text-atelier-cream/60">
        {t("products.emptyDescription")}
      </p>
      <button
        type="button"
        onClick={onNew}
        className="mt-8 inline-flex items-center gap-2 border border-atelier-ink bg-atelier-ink px-5 py-2.5 font-display text-base italic text-atelier-cream transition-colors hover:border-atelier-vermilion hover:bg-atelier-vermilion dark:border-atelier-cream dark:bg-atelier-cream dark:text-atelier-ink dark:hover:border-atelier-vermilion dark:hover:bg-atelier-vermilion dark:hover:text-atelier-cream"
      >
        <Plus size={16} aria-hidden="true" />
        {t("products.new")}
      </button>
    </div>
  );
}

function Pagination({
  page,
  totalPages,
  onPageChange,
  disabled,
}: {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  disabled: boolean;
}) {
  const { t } = useI18n();
  return (
    <div className="inline-flex items-center gap-3 border border-atelier-smoke/30 px-2 py-1 dark:border-atelier-cream/15">
      <button
        type="button"
        onClick={() => onPageChange(Math.max(1, page - 1))}
        disabled={disabled || page <= 1}
        className="inline-flex items-center gap-1 px-2 py-1 font-mono text-[11px] uppercase tracking-wider text-atelier-ink transition-colors hover:text-atelier-vermilion disabled:opacity-40 dark:text-atelier-cream dark:hover:text-atelier-vermilion"
      >
        <ArrowLeft size={12} />
        {t("pagination.previous")}
      </button>
      <span className="font-mono text-xs tabular-nums text-atelier-sepia dark:text-atelier-cream/60">
        {page} / {totalPages}
      </span>
      <button
        type="button"
        onClick={() => onPageChange(Math.min(totalPages, page + 1))}
        disabled={disabled || page >= totalPages}
        className="inline-flex items-center gap-1 px-2 py-1 font-mono text-[11px] uppercase tracking-wider text-atelier-ink transition-colors hover:text-atelier-vermilion disabled:opacity-40 dark:text-atelier-cream dark:hover:text-atelier-vermilion"
      >
        {t("pagination.next")}
        <ArrowRight size={12} />
      </button>
    </div>
  );
}
