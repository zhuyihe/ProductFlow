import { useEffect, useState } from "react"

export const DESKTOP_BREAKPOINT = 1024

function getInitialIsDesktop(): boolean {
  if (typeof window === "undefined") return true
  return window.innerWidth >= DESKTOP_BREAKPOINT
}

export function useIsDesktop(): boolean {
  const [isDesktop, setIsDesktop] = useState(getInitialIsDesktop)

  useEffect(() => {
    function check() {
      setIsDesktop(window.innerWidth >= DESKTOP_BREAKPOINT)
    }
    window.addEventListener("resize", check)
    return () => {
      window.removeEventListener("resize", check)
    }
  }, [])

  return isDesktop
}
