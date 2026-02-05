import React from 'react';

type SidebarItem = {
  id: string;
  label: string;
  icon: string;
  active?: boolean;
};

type SidebarProps = {
  onItemClick?: (itemId: string) => void;
  biasAware?: boolean;
  onBiasToggle?: (enabled: boolean) => void;
};

const styles = {
  sidebar: {
    width: 240,
    background: "#1f2937",
    color: "white",
    padding: "24px 0",
    display: "flex",
    flexDirection: "column",
    margin: 0,
    minHeight: "100vh",
    position: "relative",
  } as React.CSSProperties,
  sidebarTitle: {
    fontSize: 24,
    fontWeight: "bold",
    padding: "0 24px",
    marginBottom: 32,
  } as React.CSSProperties,
  sidebarNav: {
    display: "flex",
    flexDirection: "column",
    gap: 4,
  } as React.CSSProperties,
  sidebarItem: {
    padding: "12px 24px",
    fontSize: 14,
    cursor: "pointer",
    transition: "background-color 0.2s",
    display: "flex",
    alignItems: "center",
    gap: 12,
  } as React.CSSProperties,
  activeSidebarItem: {
    background: "#374151",
  } as React.CSSProperties,
  biasToggle: {
    padding: "16px 24px",
    marginTop: "auto",
    borderTop: "1px solid #374151",
    fontSize: 14,
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
  } as React.CSSProperties,
  toggleSwitch: {
    width: 40,
    height: 20,
    borderRadius: 10,
    position: "relative",
    cursor: "pointer",
    transition: "background-color 0.2s",
  } as React.CSSProperties,
  toggleButton: {
    width: 16,
    height: 16,
    background: "white",
    borderRadius: "50%",
    position: "absolute",
    top: 2,
    transition: "right 0.2s",
  } as React.CSSProperties,
};

const defaultItems: SidebarItem[] = [
  { id: 'explore', label: 'Explore', icon: '', active: true },
  { id: 'compare', label: 'Compare', icon: '' },
  { id: 'play', label: 'Play', icon: '' },
  { id: 'bookmarks', label: 'Bookmarks', icon: '' },
  { id: 'settings', label: 'Settings', icon: '' },
];

export default function Sidebar({ 
  onItemClick, 
  biasAware = true, 
  onBiasToggle 
}: SidebarProps) {
  const handleItemClick = (itemId: string) => {
    onItemClick?.(itemId);
  };

  const handleBiasToggle = () => {
    onBiasToggle?.(!biasAware);
  };

  return (
    <aside style={styles.sidebar}>
      <div style={styles.sidebarTitle}>Muqawim</div>
      <nav style={styles.sidebarNav}>
        {defaultItems.map((item) => (
          <div
            key={item.id}
            style={{
              ...styles.sidebarItem,
              ...(item.active ? styles.activeSidebarItem : {}),
            }}
            onClick={() => handleItemClick(item.id)}
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </div>
        ))}
      </nav>
      <div style={styles.biasToggle}>
        <span>Bias-aware {biasAware ? 'ON' : 'OFF'}</span>
        <div 
          style={{
            ...styles.toggleSwitch,
            background: biasAware ? "#22c55e" : "#6b7280",
          }}
          onClick={handleBiasToggle}
        >
          <div style={{
            ...styles.toggleButton,
            right: biasAware ? 2 : 22,
          }} />
        </div>
      </div>
    </aside>
  );
}