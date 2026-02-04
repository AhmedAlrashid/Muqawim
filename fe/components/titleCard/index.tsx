import React from "react";

type TitleCardProps = {
  bgSrc?: string; // leading slash or absolute URL recommended
  title: string;
  subtitle?: string;
  datetime?: string;
  onClick?: () => void;
};

function normalizeSrc(src?: string) {
  if (!src) return undefined;
  if (src.startsWith("/") || src.startsWith("http://") || src.startsWith("https://")) return src;
  return `/${src}`;
}

export default function TitleCard({
  bgSrc,
  title,
  subtitle,
  datetime,
  onClick,
}: TitleCardProps) {
  const bg = normalizeSrc(bgSrc) || undefined;

  const container: React.CSSProperties = {
    position: "relative",
    width: "50%",
    height: 620,
    borderRadius: 12,
    overflow: "hidden",
    backgroundImage: bg ? `url(${bg})` : undefined,
    backgroundSize: "cover",
    backgroundPosition: "center",
    display: "flex",
    alignItems: "flex-end",
    cursor: onClick ? "pointer" : "default",
  };

  const overlay: React.CSSProperties = {
    position: "absolute",
    inset: 0,
    background: "linear-gradient(180deg, rgba(0,0,0,0.12) 0%, rgba(0,0,0,0.45) 60%, rgba(0,0,0,0.65) 100%)",
    pointerEvents: "none",
  };

  const content: React.CSSProperties = {
    position: "relative",
    zIndex: 2,
    color: "#fff",
    padding: "28px 32px",
    width: "100%",
    boxSizing: "border-box",
  };

  const titleStyle: React.CSSProperties = {
    margin: 0,
    fontSize: "clamp(24px, 6vw, 56px)",
    lineHeight: 1.02,
    fontWeight: 800,
    letterSpacing: "-0.02em",
    textShadow: "0 6px 20px rgba(0,0,0,0.5)",
  };

  const subtitleStyle: React.CSSProperties = {
    margin: "8px 0 0",
    fontSize: 16,
    opacity: 0.95,
  };

  const metaStyle: React.CSSProperties = {
    position: "absolute",
    right: 16,
    top: 16,
    fontSize: 13,
    color: "rgba(255,255,255,0.9)",
    background: "rgba(0,0,0,0.25)",
    padding: "6px 10px",
    borderRadius: 999,
  };

  return (
    <section style={container} onClick={onClick} aria-label={title}>
      <div style={overlay} />
      {datetime && <div style={metaStyle}>{datetime}</div>}
      <div style={content}>
        <h1 style={titleStyle}>{title}</h1>
        {subtitle && <p style={subtitleStyle}>{subtitle}</p>}
      </div>
    </section>
  );
}
