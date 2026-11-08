export function LogoMark({ className = "size-6" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden fill="none">
      <circle cx="12" cy="12" r="10.5" stroke="currentColor" strokeOpacity="0.5" />
      <path d="M4 14.5 L20 8.5 L14.5 13 L15.5 18 L12.5 14.2 Z" fill="currentColor" />
    </svg>
  );
}
