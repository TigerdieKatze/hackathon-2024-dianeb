'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface Stats {
  total_games: number
  total_wins: number
  win_percentage: number
  avg_time_per_turn: number
  avg_errors: number
  total_new_words_added: number
  error_counts_per_word_length: Record<string, { errors: number; games: number }>
}

async function fetchStats(): Promise<Stats> {
  const response = await fetch('http://127.0.0.1:5000/api/stats')
  if (!response.ok) {
    throw new Error('Failed to fetch stats')
  }
  return response.json()
}

export default function Page() {
  const [stats, setStats] = useState<Stats | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await fetchStats()
        setStats(data)
      } catch (error) {
        console.error('Error fetching stats:', error)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 5000)

    return () => clearInterval(interval)
  }, [])

  if (!stats) {
    return <div className="flex justify-center items-center h-screen">Loading...</div>
  }

  const chartData = Object.entries(stats.error_counts_per_word_length).map(([length, data]) => ({
    length: parseInt(length),
    avgErrors: data.games > 0 ? data.errors / data.games : 0,
    gamesPlayed: data.games
  })).sort((a, b) => a.length - b.length)

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-6">Bot Statistics</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        <Card>
          <CardHeader>
            <CardTitle>Total Games</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-4xl font-bold">{stats.total_games}</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Win Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-4xl font-bold">{stats.win_percentage.toFixed(2)}%</p>
            <p className="text-sm text-muted-foreground">({stats.total_wins} wins)</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Avg Time per Turn</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-4xl font-bold">{stats.avg_time_per_turn.toFixed(2)}s</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Avg Errors</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-4xl font-bold">{stats.avg_errors.toFixed(2)}</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>New Words Added</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-4xl font-bold">{stats.total_new_words_added}</p>
          </CardContent>
        </Card>
      </div>
      
      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Error Counts per Word Length</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="length" />
                <YAxis yAxisId="left" orientation="left" stroke="#8884d8" />
                <YAxis yAxisId="right" orientation="right" stroke="#82ca9d" />
                <Tooltip />
                <Bar yAxisId="left" dataKey="avgErrors" fill="#8884d8" name="Avg Errors" />
                <Bar yAxisId="right" dataKey="gamesPlayed" fill="#82ca9d" name="Games Played" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader>
          <CardTitle>Error Counts per Word Length (Table)</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Word Length</TableHead>
                <TableHead>Average Errors</TableHead>
                <TableHead>Games Played</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {Object.entries(stats.error_counts_per_word_length).map(([length, data]) => (
                <TableRow key={length}>
                  <TableCell>{length}</TableCell>
                  <TableCell>{(data.errors / data.games).toFixed(2)}</TableCell>
                  <TableCell>{data.games}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}