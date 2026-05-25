import { lazy, Suspense, useEffect, useMemo } from "react";
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { api } from "./lib/api";
import { LenisProvider } from "./lib/lenis-provider";
import { PreferencesProvider, useI18n } from "./lib/preferences";
import { DesktopOnlyPrompt } from "./components/DesktopOnlyPrompt";
import { useIsDesktop } from "./hooks/useIsDesktop";

const GalleryPage = lazy(() =>
  import("./pages/GalleryPage").then((module) => ({ default: module.GalleryPage })),
);
const HelpPage = lazy(() =>
  import("./pages/HelpPage").then((module) => ({ default: module.HelpPage })),
);
const LoginPage = lazy(() =>
  import("./pages/LoginPage").then((module) => ({ default: module.LoginPage })),
);
const loadImageChatPage = () =>
  import("./pages/ImageChatPage").then((module) => ({ default: module.ImageChatPage }));
const ImageChatPage = lazy(loadImageChatPage);
const ProductCreatePage = lazy(() =>
  import("./pages/ProductCreatePage").then((module) => ({ default: module.ProductCreatePage })),
);
const ProductDetailPage = lazy(() =>
  import("./pages/ProductDetailPage").then((module) => ({ default: module.ProductDetailPage })),
);
const loadProductListPage = () =>
  import("./pages/ProductListPage").then((module) => ({ default: module.ProductListPage }));
const ProductListPage = lazy(loadProductListPage);
const SettingsPage = lazy(() =>
  import("./pages/SettingsPage").then((module) => ({ default: module.SettingsPage })),
);
const NotFoundPage = lazy(() =>
  import("./pages/NotFoundPage").then((module) => ({ default: module.NotFoundPage })),
);

function LoadingScreen() {
  const { t } = useI18n();

  return (
    <div className="flex min-h-screen items-center justify-center bg-atelier-cream text-atelier-smoke dark:bg-[#1A1410] dark:text-atelier-cream/40">
      <Loader2 size={24} className="animate-spin" />
      <span className="sr-only">{t("app.loading")}</span>
    </div>
  );
}

function AppRoutes() {
  const sessionQuery = useQuery({
    queryKey: ["session"],
    queryFn: api.getSessionState,
    retry: false,
  });

  const authenticated = Boolean(sessionQuery.data?.authenticated);
  const isAdmin = sessionQuery.data?.principal_kind === "admin";
  const ssoStartUrl = sessionQuery.data?.sso_start_url ?? null;

  useEffect(() => {
    if (!authenticated) {
      return;
    }
    void loadProductListPage();
    void loadImageChatPage();
  }, [authenticated]);

  if (sessionQuery.isLoading) {
    return <LoadingScreen />;
  }

  const workspaceLoginTarget = "/login";

  return (
    <Suspense fallback={<LoadingScreen />}>
      <Routes>
        <Route path="/login" element={<LoginPage authenticated={authenticated} ssoStartUrl={ssoStartUrl} />} />
        <Route
          path="/products"
          element={authenticated ? <ProductListPage /> : <Navigate to={workspaceLoginTarget} replace />}
        />
        <Route
          path="/products/new"
          element={authenticated ? <ProductCreatePage /> : <Navigate to={workspaceLoginTarget} replace />}
        />
        <Route
          path="/image-chat"
          element={authenticated ? <ImageChatPage /> : <Navigate to={workspaceLoginTarget} replace />}
        />
        <Route
          path="/gallery"
          element={authenticated ? <GalleryPage /> : <Navigate to={workspaceLoginTarget} replace />}
        />
        <Route
          path="/help"
          element={authenticated ? <HelpPage /> : <Navigate to={workspaceLoginTarget} replace />}
        />
        <Route
          path="/settings"
          element={
            authenticated
              ? (isAdmin ? <SettingsPage /> : <Navigate to="/products" replace />)
              : <Navigate to={workspaceLoginTarget} replace />
          }
        />
        <Route
          path="/products/:productId/image-chat"
          element={authenticated ? <ImageChatPage /> : <Navigate to={workspaceLoginTarget} replace />}
        />
        <Route
          path="/products/:productId"
          element={authenticated ? <ProductDetailPage /> : <Navigate to={workspaceLoginTarget} replace />}
        />
        <Route path="*" element={<NotFoundPage authenticated={authenticated} />} />
      </Routes>
    </Suspense>
  );
}

export function App() {
  const isDesktop = useIsDesktop();
  const queryClient = useMemo(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            refetchOnWindowFocus: false,
          },
        },
      }),
    [],
  );

  if (!isDesktop) {
    return <DesktopOnlyPrompt />;
  }

  return (
    <QueryClientProvider client={queryClient}>
      <PreferencesProvider>
        <BrowserRouter>
          <LenisProvider>
            <div className="min-h-screen bg-atelier-cream font-body text-atelier-ink selection:bg-atelier-vermilion/20 dark:bg-[#1A1410] dark:text-atelier-cream dark:selection:bg-atelier-vermilion/30">
              <AppRoutes />
            </div>
          </LenisProvider>
        </BrowserRouter>
      </PreferencesProvider>
    </QueryClientProvider>
  );
}
