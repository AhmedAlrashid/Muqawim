import React from "react";
import Card from "@/components/card";
import TitleCard from "../components/titleCard";

export default function Home() {
  return (
    <>
      <main style={{ display: "flex", gap: 20, padding: 20, flexDirection: "column" }}>
        <TitleCard
          bgSrc="/Shrine+of+Imam+Hussain.-3109731395.jpg"
          title="After the extension of the ceasefire..."
          subtitle="Damascus government and SDF accused..."
          datetime="Day 22:51"
        />

        <div style={{ display: "flex", gap: 20, marginTop: 20 }}>
          <Card
            imgSrc="/Shrine+of+Imam+Hussain.-3109731395.jpg"
            imgAlt="Next logo"
            title="After the extension of the ceasefire..."
            excerpt="Damascus government and SDF accused..."
            datetime="Day 22:51"
            layout="top"
            size="small"
          />
          <Card
            imgSrc="/Shrine+of+Imam+Hussain.-3109731395.jpg"
            imgAlt="Next logo"
            title="Another headline"
            excerpt="Short excerpt for the second card"
            datetime="Day 22:30"
            layout="top"
            size="medium"
          />
          <Card
            imgSrc="/Shrine+of+Imam+Hussain.-3109731395.jpg"
            imgAlt="Next logo"
            title="Another headline"
            excerpt="Short excerpt for the second card"
            datetime="Day 22:30"
            layout="top"
            size="large"
          />
        </div>
      </main>
    </>
  );
}