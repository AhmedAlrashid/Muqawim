export type Article = {
  doc_id: string;
  headline: string;
  article: string;
  url: string;
  image:string;
};

export type ArticleList = {
  query: string;
  query_info: string;
  total_documents: number;
  results_count: number;
  search_time_ms: number;
  results: Article[];
};

export async function fetchHeadlineAndArticle ( query: string) : Promise<ArticleList>{
    const response= await fetch (`http://127.0.0.1:8000/searchQuery?query=${encodeURIComponent(query)}`)
    if (!response.ok) {
        throw new Error("Search failed");
    }

    return response.json();
}