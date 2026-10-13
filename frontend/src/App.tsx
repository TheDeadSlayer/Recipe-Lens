import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import RootLayout from './components/layout/RootLayout'
import AnalyzePage from './pages/AnalyzePage'
import RecipesPage from './pages/RecipesPage'
import RecipeDetailPage from './pages/RecipeDetailPage'

const router = createBrowserRouter([
  {
    element: <RootLayout />,
    children: [
      { index: true, element: <AnalyzePage /> },
      { path: 'recipes', element: <RecipesPage /> },
      { path: 'recipes/:id', element: <RecipeDetailPage /> },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
