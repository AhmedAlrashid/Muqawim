import React from "react";
import Image from "next/image";

type TitleCardProps = {
  bgSrc?: string;
  title: string;
  subtitle?: string;
  datetime?: string;
  onClick?: () => void;
};

export default function TitleCard({
  bgSrc,
  title,
  subtitle,
  datetime,
  onClick,
}: TitleCardProps) {
  const container: React.CSSProperties = {
    position: "relative",
    width: "100%",
    minHeight: "830px",
    borderRadius: 12,
    overflow: "hidden",
    display: "flex",
    alignItems: "flex-end",
    cursor: onClick ? "pointer" : "default",
  };

  const overlay: React.CSSProperties = {
    position: "absolute",
    inset: 0,
    background:
      "linear-gradient(180deg, rgba(0,0,0,0.12) 0%, rgba(0,0,0,0.45) 60%, rgba(0,0,0,0.65) 100%)",
    zIndex: 1,
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
    lineHeight: 1.05,
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
    zIndex: 2,
  };

  return (
    <section style={container} onClick={onClick} aria-label={title}>
      {bgSrc && (
        <Image
          src={bgSrc}
          alt={title}
          fill
          priority
          style={{
            objectFit: "cover", // 🔥 same as background-size: cover
          }}
        />
      )}

      <div style={overlay} />

      {datetime && <div style={metaStyle}>{datetime}</div>}

      <div style={content}>
        <h1 style={titleStyle}>{title}</h1>
        {subtitle && <p style={subtitleStyle}>{subtitle}</p>}
      </div>
    </section>
  );
}
