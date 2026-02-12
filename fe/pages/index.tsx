import React, { useState, useEffect } from "react";
import Navbar from "../components/navbar";
import Sidebar from "../components/sidebar";
import BreakingNews from "../components/breakingNews";
import TitleCard from "@/components/titleCard";
import Card from "@/components/card"
import image from "@/public/Shrine+of+Imam+Hussain.-3109731395.jpg"
import { fetchHeadlineAndArticle,Article} from "../api/article_headline";

const styles = {
  container: {
    display: "flex",
    minHeight: "100vh",
    margin: 0,
    padding: 0,
  } as React.CSSProperties,
  mainContent: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
  } as React.CSSProperties,
  contentArea: {
    padding: 24,
  } as React.CSSProperties,
};

export default function Home() {
  const [articles, setArticles] = useState<Article[]>([]);

  const handleSearch = async (query: string) => {
    try {
      const data = await fetchHeadlineAndArticle(query);
      setArticles(data.results);
    } catch (error) {
      console.error(error);
    }
  };

const heroarticle=articles[0]
const largeArticles = articles.slice(1, 5);   // next 4
const mediumArticles = articles.slice(5, 8); 
const smallArticles=articles.slice(9,16)
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
      `}</style>
      <div style={styles.container}>
        <Sidebar 
          onItemClick={handleSidebarClick}
          onBiasToggle={handleBiasToggle}
        />

        <main style={styles.mainContent}>
          <Navbar onSearch={handleSearch} 
          />
          
          <BreakingNews 
            message="Ceasefire extended in Gaza — coverage diverge across outlets"
            actionText="Compare coverage →"
            onActionClick={handleBreakingNewsAction}
          />

          <div style={styles.contentArea}>
            {/* Main content will go here */}
<div style={{
  display: 'flex',
  gap: '20px',
  alignItems: 'flex-start',
}}>

  <div style={{ flex: 3 }}>
    {heroarticle && (
      <TitleCard
        bgSrc={heroarticle.image}
        title={heroarticle.headline}
        subtitle={heroarticle.article.slice(0, 200) + "..."}
        datetime="Febraury 12, 2026"
      />
    )}
  </div>

  <div style={{
    flex: 2,
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "20px",
  }}>
    {largeArticles.map((article) => (
      <Card
        key={article.doc_id}
        title={article.headline}
        imgSrc={article.image}
        size="large"
      />
    ))}
  </div>

  <div style={{
    flex: 1,
    display: "flex",
    flexDirection: "column",
    gap: "20px"
  }}>
    {mediumArticles.map((article) => (
      <Card
        key={article.doc_id}
        title={article.headline}
        imgSrc={article.image}
      />
    ))}
  </div>

</div>

            <div
              style={{
                display: "flex",
                flexDirection: "row",
                gap:"40px",
                marginTop: "40px",
                flex:1
            }}>
                {smallArticles.map((article) =>
                <Card
                  key={article.doc_id}
                  title={article.headline}
                  imgSrc={article.image}
                  size="small"
                />
                )}
            </div>
          </div>
        </main>
      </div>
    </>
  );
}