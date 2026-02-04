import Image from "next/image";

type CardProps = {
  imgSrc?: string;
  imgAlt?: string;
  title?: string;
  excerpt?: string;
  datetime?: string; // short label like "Day 22:51"
  onClick?: () => void;
  layout?: "top" | "bottom" | "left" | "right";
  size?: "small" | "medium" | "large";
};

const inlineStyles: { [k: string]: React.CSSProperties } = {
  card: {
    display: "flex",
    flexDirection: "column",
    width: "100%",
    maxWidth: 360,
    borderRadius: 8,
    overflow: "hidden",
    background: "#fff",
    boxShadow: "0 6px 18px rgba(2,6,23,0.08)",
    cursor: "pointer",
  },
  media: {
    position: "relative",
    width: "100%",
    aspectRatio: "16/10",
    background: "#f3f4f6",
  },
  img: {
    objectFit: "cover",
    borderBottom: "1px solid rgba(0,0,0,0.04)",
  },
  placeholder: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "#6b7280",
    fontSize: 14,
    height: "100%",
  },
  content: {
    padding: "12px 14px",
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  title: {
    margin: 0,
    fontSize: 15,
    lineHeight: 1.2,
    color: "#111827",
    fontWeight: 600,
  },
  excerpt: {
    margin: 0,
    fontSize: 13,
    color: "#374151",
    display: "-webkit-box",
    WebkitLineClamp: 2,
    WebkitBoxOrient: "vertical" as any,
    overflow: "hidden",
  },
  meta: {
    marginTop: "auto",
    fontSize: 12,
    color: "#9ca3af",
    textAlign: "right" as any,
  },
};

export default function Card({
  imgSrc,
  imgAlt = "",
  title,
  excerpt,
  datetime,
  onClick,
  layout = "top",
  size = "medium",
}: CardProps) {
  const isHorizontal = layout === "left" || layout === "right";

  // size adjustments: small is quite small, medium is between small and title (large)
  const sizeSettings = {
    small: { maxWidth: 220, horizontalImage: 80, titleSize: 13, excerptSize: 12, cardHeightVertical: 110, cardMinHeightHorizontal: 80 },
    medium: { maxWidth: 360, horizontalImage: 140, titleSize: 15, excerptSize: 13, cardHeightVertical: 200, cardMinHeightHorizontal: 120 },
    large: { maxWidth: 520, horizontalImage: 180, titleSize: 18, excerptSize: 14, cardHeightVertical: 320, cardMinHeightHorizontal: 160 },
  } as const;

  const s = sizeSettings[size || "medium"];

  const cardStyle: React.CSSProperties = {
    ...inlineStyles.card,
    maxWidth: s.maxWidth,
    flexDirection: isHorizontal ? (layout === "right" ? "row-reverse" : "row") : "column",
    alignItems: isHorizontal ? "stretch" : undefined,
    // set an explicit height for horizontal layouts so children (media with `height: 100%`) have a real size
    minHeight: isHorizontal ? s.cardMinHeightHorizontal : undefined,
    height: isHorizontal ? s.cardMinHeightHorizontal : undefined,
    alignSelf: "flex-start",
  };

  const mediaStyle: React.CSSProperties = isHorizontal
    ? {
        position: "relative",
        width: s.horizontalImage,
        minWidth: Math.max(72, s.horizontalImage - 20),
        height: "100%",
        display: "block",
        flex: `0 0 ${s.horizontalImage}px`,
        background: inlineStyles.media.background,
      }
    : { ...inlineStyles.media };

  // for vertical layout override the media height to create clear size differences
  if (!isHorizontal) {
    mediaStyle.height = s.cardHeightVertical as unknown as number;
    // keep width:100% from inlineStyles.media
    mediaStyle.aspectRatio = undefined as any;
  }

  const contentStyle: React.CSSProperties = {
    ...inlineStyles.content,
    padding: isHorizontal ? 12 : inlineStyles.content.padding,
    flex: 1,
  };

  return (
    <article style={cardStyle} onClick={onClick}>
      <div style={mediaStyle}>
        {imgSrc ? (
          <Image
            src={imgSrc}
            alt={imgAlt}
            fill
            sizes={isHorizontal ? `${s.horizontalImage}px` : `(max-width: 600px) 100vw, ${s.maxWidth}px`}
            style={{ ...inlineStyles.img, height: "100%" }}
            priority={false}
          />
        ) : (
          <div style={inlineStyles.placeholder}>No Image</div>
        )}
      </div>

      <div style={contentStyle}>
        {title && <h3 style={{ ...inlineStyles.title, fontSize: s.titleSize }}>{title}</h3>}
        {excerpt && <p style={{ ...inlineStyles.excerpt, fontSize: s.excerptSize }}>{excerpt}</p>}
        <div style={inlineStyles.meta}>{datetime}</div>
      </div>
    </article>
  );
}
