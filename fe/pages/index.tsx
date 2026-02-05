import React from "react";
import Navbar from "../components/navbar";
import Sidebar from "../components/sidebar";
import BreakingNews from "../components/breakingNews";
import TitleCard from "@/components/titleCard";
import image from "@/public/Shrine+of+Imam+Hussain.-3109731395.jpg"

const styles = {
  container: {
    display: "flex",
    height: "100vh",
    margin: 0,
    padding: 0,
  } as React.CSSProperties,
  mainContent: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
  } as React.CSSProperties,
  contentArea: {
    flex: 1,
    padding: 24,
    overflow: "auto",
  } as React.CSSProperties,
};

export default function Home() {
  const handleSearch = (query: string) => {
    console.log('Search query:', query);
    // TODO: Implement search functionality
  };

  const handleSidebarClick = (itemId: string) => {
    console.log('Sidebar item clicked:', itemId);
    // TODO: Implement navigation
  };

  const handleBiasToggle = (enabled: boolean) => {
    console.log('Bias awareness toggled:', enabled);
    // TODO: Implement bias awareness toggle
  };

  const handleBreakingNewsAction = () => {
    console.log('Breaking news action clicked');
    // TODO: Navigate to comparison view
  };

  return (
    <>
      <style jsx global>{`
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }
        
        html, body {
          margin: 0;
          padding: 0;
          height: 100%;
          overflow-x: hidden;
        }
        
        #__next {
          margin: 0;
          padding: 0;
          height: 100vh;
        }
      `}</style>
      <div style={styles.container}>
        <Sidebar 
          onItemClick={handleSidebarClick}
          onBiasToggle={handleBiasToggle}
        />

        <main style={styles.mainContent}>
          <Navbar onSearch={handleSearch} />
          
          <BreakingNews 
            message="Ceasefire extended in Gaza — coverage diverge across outlets"
            actionText="Compare coverage →"
            onActionClick={handleBreakingNewsAction}
          />

          <div style={styles.contentArea}>
            {/* Main content will go here */}
            <div style={{ 
              display: 'flex', 
              alignItems: 'flex-start', 
              justifyContent: 'flex-start', 
              height: '100%',
              color: '#6b7280',
              fontSize: 18
            }}>
              <TitleCard
                bgSrc={image.src}
                title="Sample Title"
                subtitle="HSDJFJDSNFJKDSBFJDSBFJKDSBFJKDSFBDJSBFSDJFBD
                FDBSDJKFBSDJKF 
                SFDSJKFB JKF DS\
                 SFDS "
                datetime="April 27, 2024"
              ></TitleCard>
            </div>
          </div>
        </main>
      </div>
    </>
  );
}