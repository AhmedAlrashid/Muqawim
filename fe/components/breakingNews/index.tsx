import React from 'react';

type BreakingNewsProps = {
  message: string;
  actionText?: string;
  onActionClick?: () => void;
  visible?: boolean;
};

const styles = {
  breakingNews: {
    background: "#dc2626",
    color: "white",
    padding: "8px 24px",
    fontSize: 14,
    display: "flex",
    alignItems: "center",
    gap: 8,
    position: "relative",
    overflow: "hidden",
  } as React.CSSProperties,
  breakingLabel: {
    fontWeight: "bold",
    display: "flex",
    alignItems: "center",
    gap: 4,
    flexShrink: 0,
    zIndex: 2,
  } as React.CSSProperties,
  scrollingContainer: {
    flex: 1,
    overflow: "hidden",
    position: "relative",
  } as React.CSSProperties,
  scrollingText: {
    display: "inline-block",
    whiteSpace: "nowrap",
    animation: "scroll 20s linear infinite",
    paddingLeft: "100%",
  } as React.CSSProperties,
  action: {
    marginLeft: "auto",
    cursor: "pointer",
    fontWeight: 500,
    transition: "opacity 0.2s",
    flexShrink: 0,
    zIndex: 2,
  } as React.CSSProperties,
  hidden: {
    display: "none",
  } as React.CSSProperties,
};

export default function BreakingNews({ 
  message, 
  actionText, 
  onActionClick, 
  visible = true 
}: BreakingNewsProps) {
  if (!visible) {
    return null;
  }

  return (
    <>
      <style jsx>{`
        @keyframes scroll {
          0% {
            transform: translateX(0%);
          }
          100% {
            transform: translateX(-100%);
          }
        }
      `}</style>
      <div style={styles.breakingNews}>
        <span style={styles.breakingLabel}>
          🔴 BREAKING
        </span>
        <div style={styles.scrollingContainer}>
          <span style={styles.scrollingText}>{message}</span>
        </div>
        {actionText && (
          <span 
            style={styles.action}
            onClick={onActionClick}
          >
            {actionText}
          </span>
        )}
      </div>
    </>
  );
}