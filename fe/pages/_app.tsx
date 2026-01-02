'use client'

import { useState } from 'react'

interface SearchResult {
  url: string
  title?: string
  snippet?: string
}

export default function Home() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [searchTime, setSearchTime] = useState<number | null>(null)
  const [totalResults, setTotalResults] = useState(0)
  const [queryInfo, setQueryInfo] = useState<string | null>(null)
  const [isOffline, setIsOffline] = useState(false)

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    setIsLoading(true)
    try {
      const response = await fetch(`/api/search?q=${encodeURIComponent(query.trim())}`, {
        method: 'GET'
      })
      
      const data = await response.json()
      setResults(data.results || [])
      setSearchTime(data.searchTime || null)
      setTotalResults(data.totalResults || data.results?.length || 0)
      setQueryInfo(data.queryInfo || null)
      setIsOffline(data.isOffline || false)
    } catch (error) {
      console.error('Search failed:', error)
      setResults([])
      setQueryInfo(null)
      setIsOffline(false)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <div className="bg-white border-b">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold text-blue-600 mb-6 text-center">
            UCI ICS Search
          </h1>
          
          {/* Search Form */}
          <form onSubmit={handleSearch} className="flex gap-3">
            <div className="flex-1 relative">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search ICS documents..."
                className="w-full px-4 py-3 text-black border-2 border-gray-300 rounded-full focus:outline-none focus:border-blue-500 hover:border-gray-400"
                disabled={isLoading}
              />
              {query && (
                <button
                  type="button"
                  onClick={() => setQuery('')}
                  className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              )}
            </div>
            <button
              type="submit"
              disabled={isLoading || !query.trim()}
              className="px-6 py-3 bg-blue-600 text-white rounded-full hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
            >
              {isLoading ? (
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  Searching...
                </div>
              ) : (
                'Search'
              )}
            </button>
          </form>
        </div>
      </div>

      {/* Results */}
      <div className="max-w-4xl mx-auto px-4 py-6">
        {/* Search Stats */}
        {searchTime !== null && (
          <div className="text-sm text-gray-600 mb-4 space-y-1">
            <div>
              About {totalResults.toLocaleString()} results 
              {searchTime && ` (${searchTime.toFixed(2)} ms)`}
              {isOffline && (
                <span className="ml-2 px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded">
                  Flask API Offline - Using Mock Data
                </span>
              )}
            </div>
            {queryInfo && (
              <div className="text-xs text-gray-500">
                {queryInfo}
              </div>
            )}
          </div>
        )}

        {/* Results List */}
        {results.length > 0 && (
          <div className="space-y-6">
            {results.map((result, index) => (
              <div key={index} className="group">
                <div className="mb-1">
                  <a
                    href={result.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline text-lg font-medium group-hover:text-blue-800"
                  >
                    {result.title || result.url}
                  </a>
                </div>
                <div className="text-green-700 text-sm mb-2 break-all">
                  {result.url}
                </div>
                {result.snippet && (
                  <div className="text-gray-700 text-sm leading-relaxed">
                    {result.snippet}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* No Results */}
        {!isLoading && results.length === 0 && query && (
          <div className="text-center py-12">
            <div className="text-gray-600 text-lg mb-2">
              No results found for <strong>"{query}"</strong>
            </div>
            <div className="text-gray-500 text-sm">
              Try different keywords or check your spelling
            </div>
          </div>
        )}

        {/* Initial State */}
        {!query && results.length === 0 && (
          <div className="text-center py-12">
            <div className="text-gray-500 text-lg">
              Search through 53,792 UCI ICS documents
            </div>
            <div className="text-gray-400 text-sm mt-2">
              Try: "machine learning", "cristina lopes", "ACM"
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="mt-16 border-t bg-gray-50 py-6">
        <div className="max-w-4xl mx-auto px-4 text-center text-gray-500 text-sm">
          <div>Powered by TF-IDF ranking with Porter stemming</div>
          <div className="mt-1">CS 121 Information Retrieval Project</div>
        </div>
      </div>
    </div>
  )
}
