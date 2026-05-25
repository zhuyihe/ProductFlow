import Lenis from "lenis"
import type { ReactNode } from "react"
import { useEffect, useRef } from "react"
import { useLocation } from "react-router-dom"

// Routes hosting @xyflow/react canvas — Lenis hijacks wheel events which
// breaks native pan/zoom on react-flow. Disable on these prefixes.
const LENIS_DISABLED_PREFIXES = [
  "/image-chat",
  "/products/new",
]

function isLenisDisabled(pathname: string): boolean {
  if (LENIS_DISABLED_PREFIXES.some((p) => pathname.startsWith(p))) {
    return true
  }
  // /products/:productId and /products/:productId/image-chat both host workflow canvas
  return /^\/products\/[^/]+/.test(pathname)
}

interface LenisProviderProps {
  children: ReactNode
}

export function LenisProvider({ children }: LenisProviderProps) {
  const { pathname } = useLocation()
  const lenisRef = useRef<Lenis | null>(null)

  useEffect(() => {
    if (isLenisDisabled(pathname)) {
      return
    }

    const lenis = new Lenis({ lerp: 0.1, smoothWheel: true })
    lenisRef.current = lenis

    let rafId = 0
    function raf(time: number) {
      lenis.raf(time)
      rafId = requestAnimationFrame(raf)
    }
    rafId = requestAnimationFrame(raf)

    return () => {
      cancelAnimationFrame(rafId)
      lenis.destroy()
      lenisRef.current = null
    }
  }, [pathname])

  return <>{children}</>
}
