import { ReactLenis } from "lenis/react";

export default function LenisRoot({ children }) {
  return <ReactLenis root>{children}</ReactLenis>;
}
