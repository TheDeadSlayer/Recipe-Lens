import { apiFetch } from './client'
import type { Recipe } from '../types/api'

export function listRecipes(skip = 0, limit = 20): Promise<Recipe[]> {
  return apiFetch<Recipe[]>(`/api/v1/recipes?skip=${skip}&limit=${limit}`)
}

export function getRecipe(recipeId: string): Promise<Recipe> {
  return apiFetch<Recipe>(`/api/v1/recipes/${recipeId}`)
}
