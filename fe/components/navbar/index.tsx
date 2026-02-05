import React from 'react';

type NavbarProps = {
  onSearch?: (query: string) => void;
};

const styles = {
  header: {
    background: "white",
    borderBottom: "1px solid #e5e7eb",
    padding: "0 24px",
    height: 60,
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
  } as React.CSSProperties,
  headerNav: {
    display: "flex",
    gap: 32,
    alignItems: "center",
  } as React.CSSProperties,
  headerTitle: {
    fontSize: 24,
    fontWeight: "bold",
    color: "#1f2937",
  } as React.CSSProperties,
  headerLink: {
    fontSize: 14,
    color: "#6b7280",
    textDecoration: "none",
    cursor: "pointer",
    transition: "color 0.2s",
  } as React.CSSProperties,
  activeLink: {
    color: "#1f2937",
    fontWeight: 600,
  } as React.CSSProperties,
  searchBar: {
    padding: "8px 16px",
    border: "1px solid #d1d5db",
    borderRadius: 8,
    width: 300,
    fontSize: 14,
    outline: "none",
  } as React.CSSProperties,
};

export default function Navbar({ onSearch }: NavbarProps) {
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onSearch?.(e.target.value);
  };

  return (
    <header style={styles.header}>
      <nav style={styles.headerNav}>
        <span style={styles.headerTitle}>Muqawim</span>
        <a style={{ ...styles.headerLink, ...styles.activeLink }}>Explore</a>
        <a style={styles.headerLink}>Compare</a>
        <a style={styles.headerLink}>Play</a>
      </nav>
      <input 
        type="text" 
        placeholder="Search events, people, countries..."
        style={styles.searchBar}
        onChange={handleSearchChange}
      />
    </header>
  );
}